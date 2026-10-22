"""Insere registros INTEIRAMENTE FICTÍCIOS para validar banco + dbt + Power BI sem a API.

Nenhum dado real: todo `_id` começa com DEMO_ e todo órgão se chama "fictício".
Os flagrantes sintéticos (classe 280) reproduzem, em pequena escala, as situações
que a carga real revelou, para que o dbt e os testes tenham o que verificar:
  - data de entrada nos dois formatos (ISO e compacto AAAAMMDDhhmmss, em UTC);
  - as quatro situações do desfecho: decisão identificável, só "Outras Decisões",
    movimentos sem decisão sobre a prisão e nenhum movimento;
  - órgão não informado (código 0, sem nome) e dois órgãos com o mesmo nome.
Os 30 registros de classes 999001/999002 continuam como exemplo de outras classes.
"""
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

DEFAULT_DB = "postgresql://observatorio:observatorio@localhost:5433/observatorio"

# (código, nome) dos movimentos usados; os códigos estão em dbt/seeds/mapa_movimentos.csv
LIBERDADE = (818, "Liberdade provisória")
PREVENTIVA = (12140, "Prisão em Flagrante em Prisão Preventiva")
RELAXAMENTO = (12141, "Relaxamento do Flagrante")
OUTRAS = (12164, "Outras Decisões")
CUSTODIA = (12742, "Audiência de custódia")
DISTRIBUICAO = (26, "Distribuição")  # fora do mapa: movimento sem decisão sobre a prisão

ORGAOS = [
    {"codigo": 900001, "nome": "VARA FICTÍCIA DE PLANTÃO"},
    {"codigo": 900002, "nome": "VARA FICTÍCIA DAS GARANTIAS"},
    {"codigo": 900003, "nome": "VARA FICTÍCIA DAS GARANTIAS"},  # mesmo nome, outro órgão
    {"codigo": 0, "nome": None},                                  # órgão não informado
]


def _mov(codigo_nome, quando):
    codigo, nome = codigo_nome
    return {"codigo": codigo, "nome": nome, "dataHora": quando.strftime("%Y-%m-%dT%H:%M:%S.000Z")}


def demo_outras_classes():
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


def demo_flagrantes(n=300):
    """Flagrantes fictícios da classe 280, determinísticos (sem aleatoriedade)."""
    result = []
    inicio = datetime(2024, 1, 3, 9, 0, tzinfo=timezone.utc)
    decisoes = [LIBERDADE, LIBERDADE, LIBERDADE, PREVENTIVA, RELAXAMENTO]
    for i in range(n):
        entrada = inicio + timedelta(days=2 * i, hours=i % 11)  # 300 casos ~ 20 meses, nada no futuro
        # metade das datas no formato compacto (como o TJSP envia), sempre em UTC
        data_txt = entrada.strftime("%Y%m%d%H%M%S") if i % 2 else entrada.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        situacao = i % 10
        if situacao < 5:            # decisão identificável, 2 a 30 h depois da entrada
            movs = [_mov(CUSTODIA, entrada + timedelta(hours=1)),
                    _mov(decisoes[i % len(decisoes)], entrada + timedelta(hours=2 + (i * 7) % 29))]
        elif situacao < 8:          # só "Outras Decisões"
            movs = [_mov(OUTRAS, entrada + timedelta(hours=12))]
        elif situacao < 9:          # movimentos, mas nenhuma decisão sobre a prisão
            movs = [_mov(DISTRIBUICAO, entrada + timedelta(minutes=5))]
        else:                       # nenhum movimento
            movs = []
        orgao = ORGAOS[i % len(ORGAOS)]
        result.append({
            "_id": f"DEMO_FLAGRANTE_{i:05d}",
            "_source": {
                "tribunal": "TJSP", "grau": "G1",
                "dataAjuizamento": data_txt,
                "classe": {"codigo": 280, "nome": "Auto de Prisão em Flagrante"},
                "orgaoJulgador": {**orgao, "codigoMunicipioIBGE": 3550308},
                "assuntos": [{"codigo": 888001, "nome": "Assunto sintético"}],
                "movimentos": movs,
            },
        })
    return result


def demo_hits():
    return demo_outras_classes() + demo_flagrantes()


def main():
    import psycopg
    from ingestion.storage import init_db, store_hits
    load_dotenv()
    url = os.getenv("DATABASE_URL", DEFAULT_DB)
    with psycopg.connect(url) as conn:
        init_db(conn)
        print("Inseridos/atualizados:", store_hits(conn, demo_hits()))


if __name__ == "__main__":
    main()
