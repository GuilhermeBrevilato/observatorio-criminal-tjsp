import json
from datetime import datetime, timezone
import psycopg
from psycopg.types.json import Jsonb

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.datajud_document (
    document_id TEXT PRIMARY KEY,
    tribunal TEXT,
    source JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS raw.ingestion_run (
    run_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    details TEXT
);
"""


def init_db(conn):
    conn.execute(DDL)
    conn.commit()


def start_run(conn, details: str) -> int:
    """Abre um registro de execução e devolve o run_id."""
    run_id = conn.execute(
        "INSERT INTO raw.ingestion_run (details) VALUES (%s) RETURNING run_id", (details,)
    ).fetchone()[0]
    conn.commit()
    return run_id


def finish_run(conn, run_id: int, fetched_count: int, status: str, error: str | None = None) -> None:
    """Fecha o registro de execução com contagem, status e, se houver, a mensagem de erro."""
    conn.execute(
        """UPDATE raw.ingestion_run
              SET finished_at = now(), fetched_count = %s, status = %s,
                  details = CASE WHEN %s::text IS NULL THEN details
                                 ELSE details || ' | erro: ' || %s::text END
            WHERE run_id = %s""",
        (fetched_count, status, error, error, run_id),
    )
    conn.commit()


def store_hits(conn, hits: list[dict]) -> int:
    rows = []
    for hit in hits:
        source = hit.get("_source", {})
        document_id = hit.get("_id") or source.get("id")
        if not document_id:
            raise ValueError("Registro sem identificador")
        rows.append((str(document_id), source.get("tribunal", "TJSP"), Jsonb(source)))
    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO raw.datajud_document (document_id, tribunal, source)
            VALUES (%s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE
              SET source = EXCLUDED.source,
                  tribunal = EXCLUDED.tribunal,
                  ingested_at = now()
        """, rows)
    conn.commit()
    return len(rows)
