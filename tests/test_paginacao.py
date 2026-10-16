import asyncio

import pytest

from ingestion.paginacao import PaginacaoTravada, paginar


def fake_es(docs):
    """Imita o Elasticsearch: devolve só os documentos com sort > search_after."""
    chamadas = []

    async def buscar(cursor, size):
        chamadas.append(cursor)
        resto = [d for d in docs if cursor is None or d["sort"] > cursor]
        return {"hits": {"hits": resto[:size]}}

    return buscar, chamadas


def coletar(buscar, page_size, max_records=10_000):
    async def _run():
        ids = []
        async for lote in paginar(buscar, page_size, max_records):
            ids.extend(h["_id"] for h in lote)
        return ids
    return asyncio.run(_run())


def docs_com_empates(n, grupo):
    """n documentos; cada `grupo` consecutivos compartilham o mesmo @timestamp."""
    return [{"_id": f"D{i:04d}", "sort": [1_700_000_000_000 + i // grupo]} for i in range(n)]


def test_sem_empates_traz_tudo():
    buscar, _ = fake_es(docs_com_empates(250, 1))
    ids = coletar(buscar, 100)
    assert len(ids) == 250 and len(set(ids)) == 250


def test_empates_na_virada_de_pagina_nao_perdem_documentos():
    # cenário que perdia 10 de 250 na versão anterior
    buscar, _ = fake_es(docs_com_empates(250, 10))
    ids = coletar(buscar, 95)
    assert len(ids) == 250 and len(set(ids)) == 250


def test_respeita_max_records():
    buscar, _ = fake_es(docs_com_empates(250, 10))
    assert len(coletar(buscar, 95, max_records=120)) == 120


def test_pagina_inteira_empatada_levanta_erro():
    buscar, _ = fake_es(docs_com_empates(300, 200))
    with pytest.raises(PaginacaoTravada):
        coletar(buscar, 100)


def test_pagina_maior_que_o_grupo_atravessa_o_empate():
    buscar, _ = fake_es(docs_com_empates(300, 200))
    ids = coletar(buscar, 250)
    assert len(set(ids)) == 300
