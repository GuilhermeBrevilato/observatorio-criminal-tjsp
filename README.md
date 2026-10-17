# Observatório de Inteligência Processual Criminal — TJSP

Projeto educacional de Engenharia de Dados: **API DataJud → HTTPX → PostgreSQL → dbt → Power BI**.

## Entregas
- Cliente assíncrono `httpx`, retries e timeout
- Consulta exploratória de 10 documentos
- Extração com filtro por códigos TPU, intervalo e paginação `search_after`
- Upsert idempotente dos documentos por `_id` do DataJud
- Tabelas JSONB de origem no PostgreSQL
- Transformações, agregados e testes de qualidade via dbt
- Gerador de dados **inteiramente sintéticos** para demonstração
- Guia de conexão, medidas e páginas no Power BI
- Testes unitários com pytest

## Execução rápida (Mac/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Preencha DATAJUD_API_KEY usando a documentação oficial do CNJ.
python -m pytest -q
python -m ingestion.explore_datajud
```

## Banco de dados e demo sem API
```bash
docker compose up -d
python -m ingestion.demo_seed
cp dbt/profiles.yml.example dbt/profiles.yml
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
```
Consulte `powerbi/POWER_BI_GUIA.md` para configurar o Power BI.

## Ingestão real
Classes validadas em amostra real do TJSP (TPU/CNJ):

| Código | Classe | Documentos desde 2024-01-01 (consulta de out/2026) |
|---|---|---|
| 280 | Auto de Prisão em Flagrante | 33.603 |
| 283 | Ação Penal - Procedimento Ordinário | 867.669 |

```bash
python -m ingestion.run --class-codes 280 --start-date 2024-01-01 --end-date 2026-01-01
```
A carga é feita **mês a mês**. Se a API falhar, rode o mesmo comando de novo: meses já carregados com sucesso são pulados (`--force` recarrega). O limite `--max-records` vale por mês.

Em seguida, execute `dbt run` e `dbt test` novamente.

Cada mês carregado fica registrado em `raw.ingestion_run` (parâmetros em JSON, quantidade, `success`/`failed` e, se houver, a mensagem na coluna `error`).

## Decisões técnicas
- **Paginação segura contra empates** (`ingestion/paginacao.py`): o `search_after` por `@timestamp` pula documentos quando vários têm o mesmo timestamp e a página termina no meio do grupo. A próxima página recomeça 1 ms antes do último timestamp e descarta `_id` já vistos. Se uma página inteira estiver empatada, a carga para com erro pedindo `--page-size` maior, em vez de perder dados em silêncio. Coberto por `tests/test_paginacao.py`.
- **Resiliência a uma API instável**: o DataJud alterna 504 (servidor sobrecarregado) e 429 (limite de taxa). Tentar de novo em 1–2 s piorava o quadro e provocava o 429. O cliente espera 10, 20, 40, 80 e 120 s em erros 5xx, respeita o `Retry-After` no 429 e usa timeout de 120 s. Coberto por `tests/test_run.py`.
- **Carga mensal retomável** (`ingestion/run.py`): consultas menores falham menos, e uma falha só obriga a refazer o mês em andamento.
- **Datas tolerantes a formato** (`dbt/macros/safe_timestamptz.sql`): aceita ISO 8601 e o formato compacto `AAAAMMDDhhmmss`; valor inválido vira NULL em vez de derrubar todos os modelos. A data original é preservada em `data_ajuizamento_original`.
- **Nada some sem registro**: `qa_cobertura` mostra o total da origem, quantos chegam ao `fct_processos` e quantos ficam de fora por data ausente/inválida, classe, órgão ou município ausentes.

## Escopo / ciência de dados
- Os agregados representam **somente os documentos efetivamente extraídos**, não o universo de processos criminais do TJSP.
- A ordenação por `@timestamp` facilita a paginação, mas não cria amostra aleatória nem garante retratos históricos invariáveis do índice em atualização.
- `numeroProcesso` não é uma chave única universal de documento no DataJud. A chave de carga é `_id` e a camada analítica conta documentos.
- Para indicadores de abrangência geral é preciso estratégia de extração e reconciliação completa, avaliação de cobertura e deduplicação juridicamente validada.
- `dataAjuizamento` é data declarada no registro e não data de ocorrência do crime.
- Dados sintéticos usam códigos `999001/999002`; **não são códigos TPU criminais reais**.
- Nenhum dado real é distribuído neste repositório; não publique arquivos extraídos antes de revisar permissões legais e riscos de reidentificação.

## Fontes oficiais
- https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
- https://datajud-wiki.cnj.jus.br/api-publica/glossario/
- https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo3/
- https://atos.cnj.jus.br/atos/detalhar/3453

**Atribuição obrigatória:** Conselho Nacional de Justiça (CNJ), Base Nacional de Dados do Poder Judiciário (DataJud).
