import asyncio
import logging
import os
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)
DEFAULT_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"


class DataJudClient:
    def __init__(self, api_key: str, url: str | None = None, timeout: float = 40.0):
        if not api_key:
            raise ValueError("DATAJUD_API_KEY ausente")
        self.url = url or os.getenv("DATAJUD_URL", DEFAULT_URL)
        self.headers = {"Authorization": f"APIKey {api_key}", "Content-Type": "application/json"}
        self.timeout = timeout

    async def search(self, payload: dict[str, Any], retries: int = 3) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(retries + 1):
                try:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                        delay = min(8.0, 0.8 * (2 ** attempt)) + random.uniform(0, 0.2)
                        logger.warning("HTTP %s; nova tentativa em %.1fs", response.status_code, delay)
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()
                    result = response.json()
                    if result.get("timed_out") or result.get("_shards", {}).get("failed", 0):
                        raise RuntimeError("Consulta incompleta: timeout ou falha de shard")
                    if not isinstance(result.get("hits", {}).get("hits"), list):
                        raise ValueError("Formato de resposta inesperado")
                    return result
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    if attempt >= retries:
                        raise
                    delay = min(8.0, 0.8 * (2 ** attempt)) + random.uniform(0, 0.2)
                    logger.warning("Falha de rede %s; nova tentativa em %.1fs", type(exc).__name__, delay)
                    await asyncio.sleep(delay)
        raise RuntimeError("Consulta não concluída")


def build_query(size: int = 10, class_codes: list[int] | None = None,
                start_date: str | None = None, end_date: str | None = None,
                after: list | None = None) -> dict:
    if not 1 <= size <= 1000:
        raise ValueError("Tamanho permitido neste projeto: 1 a 1000")
    filters = []
    if class_codes:
        filters.append({"terms": {"classe.codigo": class_codes}})
    if start_date or end_date:
        conditions = {}
        if start_date:
            conditions["gte"] = start_date
        if end_date:
            conditions["lt"] = end_date
        filters.append({"range": {"dataAjuizamento": conditions}})
    payload = {
        "size": size,
        "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
        "sort": [{"@timestamp": {"order": "asc"}}],
    }
    if after is not None:
        payload["search_after"] = after
    return payload
