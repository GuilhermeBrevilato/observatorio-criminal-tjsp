# Observatório de Inteligência Processual Criminal — TJSP

Projeto educacional de Engenharia de Dados: **API DataJud → HTTPX → PostgreSQL → dbt → Power BI**.

## Entregas
- Cliente assíncrono `httpx`, retries e timeout
- Consulta exploratória de 10 documentos
- Extração ELT por classe TPU, retomável por checkpoint, com paginação `search_after` e conferência contra a API
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

## Ingestão real (ELT)
A extração filtra na fonte **apenas pela classe** (TPU/CNJ) e traz todos os anos. O recorte de período é feito no dbt.

| Código | Classe | Documentos no índice (out/2026) |
|---|---|---|
| 280 | Auto de Prisão em Flagrante | 48.681 |
| 283 | Ação Penal - Procedimento Ordinário | não medido de forma confiável (não extraída) |

```bash
python -m ingestion.run --class-codes 280
```
- **Retomável:** depois de cada lote, o cursor é salvo em `raw.ingestion_checkpoint`. Se a API cair, rode **o mesmo comando**: a carga continua de onde parou. `--restart` recomeça do zero.
- **API instável:** para deixar rodando sozinho até o fim (macOS):
  ```bash
  caffeinate -i zsh -c 'until python -m ingestion.run --class-codes 280; do sleep 300; done'
  ```
- Em seguida, `dbt run` e `dbt test`.

### Conferência
No fim, a carga compara o **total da classe informado pela API** (`size: 0`, `track_total_hits`) com os **documentos gravados por esta carga**. A conferência não usa nenhum critério além da classe, para não herdar um eventual erro da extração. Só com os números iguais o checkpoint vira `done`. Se divergir (`mismatch`), rodar de novo retoma do fim e confere outra vez. Divergências pequenas e persistentes costumam vir de processos que mudaram de classe durante a carga.

Se a divergência persistir em execuções seguidas, use `--restart`: em geral são processos que saíram da classe durante a carga.

### Cópias velhas e fuso horário
- **Cópias velhas:** um processo que sai da classe (ou do índice) não volta mais na extração, mas a cópia antiga continua no banco. O `stg_processos` marca como `vigente` só o que foi visto na **última carga completa e conferida** da classe; o `fct_processos` usa só os vigentes, e a `qa_cobertura` conta os demais em `fora_da_ultima_carga`.
- **Fuso:** o mês de ajuizamento é calculado no horário de São Paulo, qualquer que seja o fuso do servidor (o Postgres do Docker roda em UTC).
- **Dados de demonstração** (`demo_seed`) servem só para um banco vazio: misturados a uma carga real, entram nas contagens.

Cada execução fica em `raw.ingestion_run` (`success`, `partial`, `failed` ou `mismatch`, com a mensagem na coluna `error`).

## Achado: as datas do DataJud
A carga real revelou um defeito na fonte oficial. `dataAjuizamento` chega em **dois formatos**, que convivem nos mesmos meses: ISO (`2024-12-10T10:00:00.000Z`) e compacto (`20250218171119`). O índice do DataJud **não entende o formato compacto** e lê o número como milissegundos desde 1970:

| Texto enviado pelo TJSP | Data gravada no índice |
|---|---|
| `20250218171119` (18/02/2025 17:11) | `2611-09-15T12:36:11.119Z` |

Consequências observadas antes da correção:
- um filtro de período por mês **retornava 0 documentos** de fev a dez/2025, sem erro nenhum;
- um limite com 14 dígitos virava o ano 2611, e a janela de dezembro trazia 38.441 documentos em vez de 355;
- a conferência por mês "batia", porque contava com o mesmo filtro defeituoso que extraía. **Uma conferência que usa o critério da extração não detecta erro no critério.**

Números contaminados pelo defeito (não usar): uma contagem "desde 2024-01-01" com `range` simples dava 33.603 para a classe 280, porque todo documento em formato compacto, de qualquer ano, "está" em 26xx e passa no filtro. O total real de 2024–2025 é 10.661, e cerca de 72% vieram no formato compacto.

Decisão: **nenhum filtro de data na fonte.** A extração usa só a classe, e o dbt interpreta a data a partir do texto original (`safe_timestamptz`). O teste `assert_datas_nao_futuras` **falha** (bloqueia) com qualquer data no futuro; `assert_datas_antigas` só avisa sobre datas anteriores a 1990 (a carga real trouxe 92 flagrantes de 1899 a 1989, lidos de forma consistente nos dois formatos), e a `qa_cobertura` mostra quantos registros vieram em formato compacto.

## Desfecho do flagrante
`fct_desfecho_flagrante`: uma linha por auto de prisão em flagrante, com a **primeira decisão sobre a prisão** (o que aconteceu logo depois do flagrante) e o tempo até ela.

- **Códigos, não palavras:** cada movimento é classificado pelo código oficial (TPU/CNJ) em `dbt/seeds/mapa_movimentos.csv`, revisável num lugar só.
- **Decisões consideradas:** liberdade provisória (818 e 12146), preventiva (12140), relaxamento (12141), não homologação (146) e domiciliar (12148). Também são marcados o acordo de não persecução penal (12733), seu cumprimento (12735), a transação penal (12738) e a audiência de custódia realizada (12742).
- **Tempo:** `horas_ate_decisao` = da entrada do flagrante à primeira decisão. `horas_ate_decisao_valida` fica vazio quando a decisão aparece **antes** da entrada (registro inconsistente); use esta para médias.
- **Ambiguidade:** duas decisões diferentes no mesmo instante são marcadas em `decisao_ambigua`.
- **Datas inválidas** (`1899-12-30`, o "dia zero" de sistemas antigos; 17 movimentos na carga real) ficam fora dos cálculos.

### Limite: o que o painel pode afirmar
Na carga real (48.681 flagrantes), a decisão sobre a prisão é **identificável em 47%** (22.894). Nos demais, ela não está no DataJud ou está registrada como **"Outras Decisões" (12164)**, um código genérico, sem complemento, que não diz qual foi a decisão. Os complementos de "Liberdade provisória" também não distinguem os códigos 818 e 12146. Por isso, os números de desfecho valem **para os flagrantes com decisão identificável**, e o painel deve mostrar essa base (`qa_desfecho`).

Achados de qualidade nos complementos: o mesmo campo aparece como `situacao_da_audiencia` e `situacao_de_audiencia`, e há valores no campo errado (ex.: o tipo "inicial" registrado como situação).

## Decisões técnicas
- **ELT em vez de filtro na fonte** (ver "Achado" acima). Coberto por `tests/test_client.py::test_nenhum_filtro_de_data_na_fonte`.
- **Paginação segura contra empates** (`ingestion/paginacao.py`): o `search_after` por `@timestamp` pula documentos quando vários têm o mesmo timestamp e a página termina no meio do grupo. A próxima página recomeça 1 ms antes do último timestamp e descarta `_id` já vistos. A retomada pelo checkpoint usa a mesma regra. Se uma página inteira estiver empatada, a carga para com erro pedindo `--page-size` maior, em vez de perder dados em silêncio. Coberto por `tests/test_paginacao.py`.
- **Resiliência a uma API instável**: o DataJud alterna 504 (servidor sobrecarregado), 429 (limite de taxa) e respostas 200 parciais (falha de shard). Tentar de novo em 1–2 s piorava o quadro e provocava o 429. O cliente espera 10, 20, 40, 80 e 120 s, respeita o `Retry-After` no 429, nunca aceita página parcial e usa timeout de 120 s. Coberto por `tests/test_run.py`.
- **Datas tolerantes a formato** (`dbt/macros/safe_timestamptz.sql`): aceita ISO 8601 e o formato compacto `AAAAMMDDhhmmss`; valor inválido vira NULL em vez de derrubar todos os modelos. A data original é preservada em `data_ajuizamento_original`. O formato compacto é lido em **UTC**: lido no horário de São Paulo, 5% dos flagrantes nesse formato tinham a decisão "antes" da entrada, concentrados entre 0 e −3 h (contra 0,1% no formato ISO), a assinatura de um deslocamento de 3 horas.
- **Nada some sem registro**: `qa_cobertura` mostra o total da origem, quantos chegam ao `fct_processos` e quantos ficam de fora, por motivo.

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
