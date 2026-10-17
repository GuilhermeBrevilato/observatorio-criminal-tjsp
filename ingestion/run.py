"""Carga do DataJud em janelas mensais, retomável; execute com --help.

Por que mês a mês:
  - cada consulta fica menor e mais leve para a API (menos 504);
  - se a API cair, só o mês em andamento é perdido;
  - meses já carregados com sucesso são pulados na execução seguinte
    (use --force para recarregar).
"""
import argparse
import asyncio
import json
import logging
import os
from datetime import date

import psycopg
from dotenv import load_dotenv

from ingestion.client import DataJudClient, build_query
from ingestion.paginacao import paginar
from ingestion.storage import finish_run, init_db, start_run, store_hits

logger = logging.getLogger(__name__)
DEFAULT_DB = "postgresql://observatorio:observatorio@localhost:5432/observatorio"


def janelas_mensais(inicio: str, fim: str) -> list[tuple[str, str]]:
    """Divide [inicio, fim) em meses: [('2024-01-01','2024-02-01'), ...]."""
    a, b = date.fromisoformat(inicio), date.fromisoformat(fim)
    if a >= b:
        raise ValueError("--start-date deve ser anterior a --end-date")
    janelas, atual = [], a
    while atual < b:
        prox = date(atual.year + (atual.month == 12), atual.month % 12 + 1, 1)
        janelas.append((atual.isoformat(), min(prox, b).isoformat()))
        atual = prox
    return janelas


def params_janela(class_codes, inicio, fim, max_records) -> str:
    return json.dumps({"class_codes": class_codes, "start_date": inicio,
                       "end_date": fim, "max_records": max_records})


def ja_carregada(conn, params: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM raw.ingestion_run WHERE status = 'success' AND details = %s LIMIT 1",
        (params,),
    ).fetchone()
    return row is not None


async def carregar_janela(conn, client, class_codes, inicio, fim, args) -> int:
    async def buscar(cursor, size):
        payload = build_query(size, class_codes, inicio, fim, cursor)
        resposta = await client.search(payload)
        await asyncio.sleep(args.pause)
        return resposta

    params = params_janela(class_codes, inicio, fim, args.max_records)
    run_id = start_run(conn, params)
    total = 0
    try:
        async for lote in paginar(buscar, args.page_size, args.max_records):
            total += store_hits(conn, lote)
            logger.info("  %s: lote de %s; acumulado no mês: %s", inicio[:7], len(lote), total)
    except BaseException as exc:
        conn.rollback()                      # sai de uma transação abortada, se houver
        finish_run(conn, run_id, total, "failed", f"{type(exc).__name__}: {exc}")
        raise
    finish_run(conn, run_id, total, "success")
    if total >= args.max_records:
        logger.warning("  %s atingiu --max-records (%s): o mês pode estar incompleto", inicio[:7], total)
    return total


async def ingest(args):
    load_dotenv()
    class_codes = [int(x) for x in args.class_codes.split(",") if x.strip()] if args.class_codes else None
    if not class_codes:
        raise SystemExit("Informe --class-codes com códigos TPU validados; sem isso use explore_datajud")
    if not args.start_date or not args.end_date:
        raise SystemExit("É obrigatório informar --start-date e --end-date")

    client = DataJudClient(os.getenv("DATAJUD_API_KEY", ""), timeout=args.timeout)
    janelas = janelas_mensais(args.start_date, args.end_date)
    total_geral, puladas = 0, 0

    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB)) as conn:
        init_db(conn)
        for i, (inicio, fim) in enumerate(janelas, 1):
            params = params_janela(class_codes, inicio, fim, args.max_records)
            if not args.force and ja_carregada(conn, params):
                puladas += 1
                logger.info("[%s/%s] %s já carregado; pulando", i, len(janelas), inicio[:7])
                continue
            logger.info("[%s/%s] carregando %s", i, len(janelas), inicio[:7])
            total_geral += await carregar_janela(conn, client, class_codes, inicio, fim, args)

    logger.info("Concluído: %s documentos nesta execução; %s meses pulados por já estarem carregados",
                total_geral, puladas)
    return total_geral


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--class-codes", help="Códigos TPU criminais validados, separados por vírgula (ex.: 280,283)")
    parser.add_argument("--start-date", help="Inclusivo, exemplo 2025-01-01")
    parser.add_argument("--end-date", help="Exclusivo, exemplo 2026-01-01")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-records", type=int, default=50000, help="Limite POR MÊS")
    parser.add_argument("--pause", type=float, default=3.0, help="Segundos entre páginas")
    parser.add_argument("--timeout", type=float, default=120.0, help="Segundos de espera por resposta da API")
    parser.add_argument("--force", action="store_true", help="Recarrega meses já carregados com sucesso")
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000 or not 1 <= args.max_records <= 50000 or args.pause < 0:
        parser.error("Parâmetros fora dos limites estabelecidos")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)   # sem uma linha por requisição
    asyncio.run(ingest(args))


if __name__ == "__main__":
    main()
