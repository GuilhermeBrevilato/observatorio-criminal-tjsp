"""Extração ELT do DataJud: classe(s) inteira(s), retomável; execute com --help.

Fluxo:
  1. filtra na fonte SÓ pela classe (TPU/CNJ, confiável) — sem filtro de data;
  2. pagina por @timestamp e grava o JSON bruto em raw.datajud_document;
  3. depois de cada lote, salva o cursor em raw.ingestion_checkpoint: se a API
     cair, rodar o MESMO comando retoma de onde parou;
  4. no fim, confere: total da classe informado pela API x documentos gravados
     por esta carga. Só marca 'done' se bater.
O recorte de período é feito no dbt, a partir do texto original da data.
"""
import argparse
import asyncio
import json
import logging
import os

import psycopg
from dotenv import load_dotenv

from ingestion.client import DataJudClient, build_count_query, build_query
from ingestion.paginacao import paginar
from ingestion.storage import (close_checkpoint, count_loaded_since, finish_run, get_checkpoint,
                               init_db, open_checkpoint, save_cursor, start_run, store_hits)

logger = logging.getLogger(__name__)
DEFAULT_DB = "postgresql://observatorio:observatorio@localhost:5433/observatorio"
MODO = "elt-classe-completa-v1"


def job_key(class_codes: list[int]) -> str:
    return json.dumps({"class_codes": sorted(class_codes), "modo": MODO})


async def contar_na_api(client, class_codes) -> int:
    resposta = await client.search(build_count_query(class_codes))
    return resposta["hits"]["total"]["value"]


async def ingest(args):
    load_dotenv()
    class_codes = [int(x) for x in args.class_codes.split(",") if x.strip()] if args.class_codes else None
    if not class_codes:
        raise SystemExit("Informe --class-codes com códigos TPU (ex.: 280)")

    client = DataJudClient(os.getenv("DATAJUD_API_KEY", ""), timeout=args.timeout)
    job = job_key(class_codes)

    async def buscar(cursor, size):
        resposta = await client.search(build_query(size, class_codes, cursor))
        await asyncio.sleep(args.pause)
        return resposta

    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB)) as conn:
        init_db(conn)
        atual = get_checkpoint(conn, job)
        if atual and atual[2] == "done" and not args.restart:
            logger.info("Carga já concluída e conferida em execução anterior. Use --restart para refazer.")
            return 0
        open_checkpoint(conn, job, restart=args.restart)
        started_at, cursor, _ = get_checkpoint(conn, job)
        if cursor:
            logger.info("Retomando carga iniciada em %s, a partir do cursor %s", started_at, cursor)
        else:
            logger.info("Iniciando carga completa das classes %s", class_codes)

        run_id = start_run(conn, job)
        nesta_execucao = 0
        try:
            async for lote in paginar(buscar, args.page_size, args.limit, cursor_inicial=cursor):
                nesta_execucao += store_hits(conn, lote)
                save_cursor(conn, job, lote[-1]["sort"])
                if nesta_execucao % 1000 < len(lote):
                    logger.info("  %s documentos gravados nesta execução", nesta_execucao)
        except BaseException as exc:
            conn.rollback()
            finish_run(conn, run_id, nesta_execucao, "failed", f"{type(exc).__name__}: {exc}")
            raise

        if args.limit < 10**9 and nesta_execucao >= args.limit:
            finish_run(conn, run_id, nesta_execucao, "partial")
            logger.info("Parado em --limit=%s. Rode de novo (sem --limit) para continuar.", args.limit)
            return nesta_execucao

        # Conferência independente: não usa o critério da extração, só a classe.
        esperado = await contar_na_api(client, class_codes)
        gravados = count_loaded_since(conn, class_codes, started_at)
        status = "done" if gravados == esperado else "mismatch"
        close_checkpoint(conn, job, status, esperado, gravados)
        finish_run(conn, run_id, nesta_execucao, "success" if status == "done" else "mismatch",
                   None if status == "done" else f"gravados {gravados}, API informou {esperado}", esperado)
        if status == "done":
            logger.info("Concluído e conferido: %s documentos (API: %s).", gravados, esperado)
        else:
            logger.warning("DIVERGÊNCIA: gravados %s, API informa %s. Veja a seção 'Conferência' do README.",
                           gravados, esperado)
    return nesta_execucao


def main():
    parser = argparse.ArgumentParser(description="Extração ELT do DataJud (TJSP), retomável.")
    parser.add_argument("--class-codes", help="Códigos TPU separados por vírgula (ex.: 280 ou 280,283)")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--pause", type=float, default=3.0, help="Segundos entre páginas")
    parser.add_argument("--timeout", type=float, default=120.0, help="Segundos de espera por resposta da API")
    parser.add_argument("--limit", type=int, default=10**9, help="Para após N documentos (útil para testes)")
    parser.add_argument("--restart", action="store_true", help="Descarta o checkpoint e recomeça do zero")
    args = parser.parse_args()
    if not 1 <= args.page_size <= 1000 or args.limit < 1 or args.pause < 0:
        parser.error("Parâmetros fora dos limites estabelecidos")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(ingest(args))


if __name__ == "__main__":
    main()
