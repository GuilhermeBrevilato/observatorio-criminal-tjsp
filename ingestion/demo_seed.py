"""Insere registros inteiramente fictícios para validar banco + dbt + Power BI."""
import os
from dotenv import load_dotenv


def demo_hits():
    result = []
    for i in range(1, 31):
        code = 999001 if i % 2 else 999002
        result.append({
            "_id": f"DEMO_TJSP_{i:05d}",
            "_source": {
                "tribunal": "TJSP", "grau": "G1",
                "dataAjuizamento": f"2025-{(i % 12) + 1:02d}-{(i % 25) + 1:02d}T12:00:00Z",
                "classe": {"codigo": code, "nome": "Classe demonstrativa A" if code == 999001 else "Classe demonstrativa B"},
                "orgaoJulgador": {"codigo": i % 4 + 1, "nome": f"Órgão fictício {i % 4 + 1}", "codigoMunicipioIBGE": 3550308},
                "assuntos": [{"codigo": 888001, "nome": "Assunto sintético"}],
                "movimentos": [],
            },
        })
    return result


def main():
    import psycopg
    from ingestion.storage import init_db, store_hits
    load_dotenv()
    url = os.getenv("DATABASE_URL", "postgresql://observatorio:observatorio@localhost:5432/observatorio")
    with psycopg.connect(url) as conn:
        init_db(conn)
        print("Inseridos/atualizados:", store_hits(conn, demo_hits()))

if __name__ == "__main__":
    main()
