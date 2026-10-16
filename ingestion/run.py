"""Carga incremental por quantidade limitada; execute com --help."""
import argparse
import asyncio
import json
import logging
import os

import psycopg
from dotenv import load_dotenv

from ingestion.client import DataJudClient, build_query
from ingestion.paginacao import paginar
from ingestion.storage import finish_run, init_db, start_run, store_hits

logger = logging.getLogger(__name__)
DEFAULT_DB = "postgresql://observatorio:observatorio@localhost:5432/observatorio"


async def ingest(args):
    load_dotenv()
    class_codes = [int(x) for x in args.class_codes.split(",") if x.strip()] if args.class_codes else None
    if not class_codes:
        raise SystemExit("Informe --class-codes com códigos TPU validados; sem isso use explore_datajud")
    if not args.start_date or not args.end_date:
        raise SystemExit("É obrigatório informar --start-date e --end-date")

    client = DataJudClient(os.getenv("DATAJUD_API_KEY", ""))

    async def buscar(cursor, size):
        payload = build_query(size, class_codes, args.start_date, args.end_date, cursor)
        resposta = await client.search(payload)
        await asyncio.sleep(args.pause)
        return resposta

    params = json.dumps({"class_codes": class_codes, "start_date": args.start_date,
                         "end_date": args.end_date, "max_records": args.max_records,
                         "page_size": args.page_size})
    total = 0
    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB)) as conn:
        init_db(conn)
        run_id = start_run(conn, params)
        try:
            async for lote in paginar(buscar, args.page_size, args.max_records):
                total += store_hits(conn, lote)
                logger.info("Lote: %s; extraídos nesta execução: %s", len(lote), total)
        except BaseException as exc:
            conn.rollback()                      # sai de uma transação abortada, se houver
            finish_run(conn, run_id, total, "failed", f"{type(exc).__name__}: {exc}")
            raise
        finish_run(conn, run_id, total, "success")
    logger.info("Concluído: %s documentos extraídos (run_id=%s)", total, run_id)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--class-codes", help="Códigos TPU criminais validados, separados por vírgula (ex.: 280,283)")
    parser.add_argument("--start-date", help="Inclusivo, exemplo 2025-01-01")
    parser.add_argument("--end-date", help="Exclusivo, exemplo 2026-01-01")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-records", type=int, default=1000)
    parser.add_argument("--pause", type=float, default=0.5)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000 or not 1 <= args.max_records <= 50000 or args.pause < 0:
        parser.error("Parâmetros fora dos limites estabelecidos")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    asyncio.run(ingest(args))


if __name__ == "__main__":
    main()
