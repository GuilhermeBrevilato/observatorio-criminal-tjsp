import asyncio
import logging
import os
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)
DEFAULT_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"


class DataJudClient:
    def __init__(self, api_key: str, url: str | None = None, timeout: float = 120.0):
        if not api_key:
            raise ValueError("DATAJUD_API_KEY ausente")
        self.url = url or os.getenv("DATAJUD_URL", DEFAULT_URL)
        self.headers = {"Authorization": f"APIKey {api_key}", "Content-Type": "application/json"}
        self.timeout = timeout

    async def search(self, payload: dict[str, Any], retries: int = 6) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(retries + 1):
                try:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                        if response.status_code == 429:
                            # limite de taxa: respeita o tempo pedido pelo servidor
                            delay = float(response.headers.get("Retry-After", 30 * (attempt + 1)))
                        else:
                            # servidor sobrecarregado: insistir rápido só piora (e gera 429).
                            # Espera crescente: 10, 20, 40, 80, 120, 120 s
                            delay = min(120.0, 10 * (2 ** attempt)) + random.uniform(0, 2)
                        logger.warning("HTTP %s; nova tentativa em %.1fs", response.status_code, delay)
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()
                    result = response.json()
                    if result.get("timed_out") or result.get("_shards", {}).get("failed", 0):
                        # HTTP 200, mas o Elasticsearch não consultou todas as partes do índice:
                        # a página viria INCOMPLETA. Nunca aceitar; tentar de novo como num 5xx.
                        if attempt >= retries:
                            raise RuntimeError("Consulta incompleta: timeout ou falha de shard")
                        delay = min(120.0, 10 * (2 ** attempt)) + random.uniform(0, 2)
                        logger.warning("Resposta parcial (shard/timeout); nova tentativa em %.1fs", delay)
                        await asyncio.sleep(delay)
                        continue
                    if not isinstance(result.get("hits", {}).get("hits"), list):
                        raise ValueError("Formato de resposta inesperado")
                    return result
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    if attempt >= retries:
                        raise
                    delay = min(120.0, 10 * (2 ** attempt)) + random.uniform(0, 2)
                    logger.warning("Falha de rede %s; nova tentativa em %.1fs", type(exc).__name__, delay)
                    await asyncio.sleep(delay)
        raise RuntimeError("Consulta não concluída")


# Por que NÃO há filtro de data aqui (ver README, "Achado: datas do DataJud"):
# o DataJud indexa `dataAjuizamento` de forma inconsistente. Quando o tribunal
# envia o formato compacto ('20250218171119'), o índice lê o número como
# milissegundos desde 1970 e grava a data 2611-09-15. Qualquer filtro de período
# na fonte depende desse defeito. A extração filtra só pela classe (padrão
# nacional da TPU/CNJ) e o período é recortado no dbt, a partir do texto original.


def _filtros(class_codes) -> list:
    return [{"terms": {"classe.codigo": class_codes}}] if class_codes else []


def build_query(size: int = 10, class_codes: list[int] | None = None,
                after: list | None = None) -> dict:
    if not 1 <= size <= 1000:
        raise ValueError("Tamanho permitido neste projeto: 1 a 1000")
    filters = _filtros(class_codes)
    payload = {
        "size": size,
        "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
        "sort": [{"@timestamp": {"order": "asc"}}],
    }
    if after is not None:
        payload["search_after"] = after
    return payload


def build_count_query(class_codes: list[int]) -> dict:
    """Só a contagem exata, sem documentos: usada na conferência da carga."""
    return {"size": 0, "track_total_hits": True,
            "query": {"bool": {"filter": _filtros(class_codes)}}}
