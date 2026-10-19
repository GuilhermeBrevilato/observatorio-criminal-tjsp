"""Paginação segura contra empates de @timestamp.

Problema: com sort apenas por @timestamp, o search_after devolve somente o que
vem DEPOIS do último valor. Se vários documentos têm o mesmo @timestamp e a
página termina no meio desse grupo, o resto do grupo é pulado sem aviso.

Solução: a próxima página começa em (último @timestamp - 1 ms), ou seja,
inclui de novo o grupo empatado, e os documentos já vistos são descartados
pelo _id. Custa algumas linhas repetidas por página, mas não perde nada.

Limite: se uma página inteira tiver o MESMO @timestamp, não há como avançar
com segurança. Nesse caso levantamos erro pedindo um page_size maior.
"""
from collections.abc import AsyncIterator, Callable
from typing import Any


class PaginacaoTravada(RuntimeError):
    pass


def _cursor_inclusivo(sort_value: list) -> list:
    """Recua 1 ms o @timestamp para a próxima página reincluir o grupo empatado."""
    ts = sort_value[0]
    if not isinstance(ts, (int, float)):
        raise TypeError(f"Valor de sort inesperado (esperado epoch ms): {sort_value!r}")
    return [ts - 1]


async def paginar(buscar: Callable[[list | None, int], Any],
                  page_size: int, max_records: int,
                  cursor_inicial: list | None = None) -> AsyncIterator[list[dict]]:
    """Gera lotes de hits INÉDITOS (por _id) até esgotar ou atingir max_records.

    `buscar(cursor, size)` deve executar a consulta e devolver a resposta do
    Elasticsearch. O cursor é None na primeira página.

    `cursor_inicial` (o `sort` do último documento gravado numa execução
    anterior) retoma a carga: a primeira página recomeça 1 ms antes dele, para
    reincluir um eventual grupo empatado; repetidos são regravados sem duplicar.
    """
    vistos: set[str] = set()
    cursor: list | None = _cursor_inclusivo(cursor_inicial) if cursor_inicial else None
    entregues = 0

    while entregues < max_records:
        resposta = await buscar(cursor, page_size)
        hits = resposta["hits"]["hits"]
        if not hits:
            return

        novos = [h for h in hits if h.get("_id") not in vistos]
        restante = max_records - entregues
        novos = novos[:restante]
        for h in novos:
            vistos.add(h["_id"])
        if novos:
            entregues += len(novos)
            yield novos

        if len(hits) < page_size:          # última página
            return

        primeiro, ultimo = hits[0].get("sort"), hits[-1].get("sort")
        if not ultimo:
            raise PaginacaoTravada("Resposta sem campo 'sort'; impossível paginar")
        if primeiro == ultimo:
            raise PaginacaoTravada(
                f"Página inteira com o mesmo @timestamp ({ultimo}). "
                f"Aumente --page-size (atual: {page_size}) para atravessar o grupo empatado."
            )
        cursor = _cursor_inclusivo(ultimo)
