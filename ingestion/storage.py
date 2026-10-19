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
ALTER TABLE raw.ingestion_run ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE raw.ingestion_run ADD COLUMN IF NOT EXISTS expected_count INTEGER;
-- Uma linha por carga completa ("job"). Guarda onde parou, para retomar.
CREATE TABLE IF NOT EXISTS raw.ingestion_checkpoint (
    job TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cursor JSONB,
    expected_count INTEGER,
    loaded_count INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    finished_at TIMESTAMPTZ
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


def finish_run(conn, run_id: int, fetched_count: int, status: str, error: str | None = None,
               expected_count: int | None = None) -> None:
    """Fecha o registro de execução com contagem, status e, se houver, a mensagem de erro.
    `details` guarda só os parâmetros (JSON); o erro vai na coluna própria."""
    conn.execute(
        """UPDATE raw.ingestion_run
              SET finished_at = now(), fetched_count = %s, status = %s, error = %s,
                  expected_count = %s
            WHERE run_id = %s""",
        (fetched_count, status, error, expected_count, run_id),
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


def get_checkpoint(conn, job: str):
    """Devolve (started_at, cursor, status) do job, ou None se ele não existe."""
    return conn.execute(
        "SELECT started_at, cursor, status FROM raw.ingestion_checkpoint WHERE job = %s", (job,)
    ).fetchone()


def open_checkpoint(conn, job: str, restart: bool = False) -> None:
    if restart:
        conn.execute("DELETE FROM raw.ingestion_checkpoint WHERE job = %s", (job,))
    conn.execute("INSERT INTO raw.ingestion_checkpoint (job) VALUES (%s) ON CONFLICT (job) DO NOTHING", (job,))
    conn.commit()


def save_cursor(conn, job: str, cursor: list) -> None:
    """Grava o sort do último documento salvo. Chamado DEPOIS de gravar o lote:
    se cair no meio, a retomada repete no máximo um lote (upsert, sem duplicar)."""
    conn.execute("UPDATE raw.ingestion_checkpoint SET cursor = %s WHERE job = %s",
                 (Jsonb(cursor), job))
    conn.commit()


def close_checkpoint(conn, job: str, status: str, expected: int, loaded: int) -> None:
    conn.execute(
        """UPDATE raw.ingestion_checkpoint
              SET status = %s, expected_count = %s, loaded_count = %s, finished_at = now()
            WHERE job = %s""",
        (status, expected, loaded, job),
    )
    conn.commit()


def count_loaded_since(conn, class_codes: list[int], since) -> int:
    """Documentos das classes pedidas gravados/atualizados desde o início do job."""
    return conn.execute(
        """SELECT count(*) FROM raw.datajud_document
            WHERE ingested_at >= %s
              AND NULLIF(source #>> '{classe,codigo}', '')::int = ANY(%s)""",
        (since, class_codes),
    ).fetchone()[0]
