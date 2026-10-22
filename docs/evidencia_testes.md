# Evidência dos testes

Dois ambientes, dois níveis de prova:

| Onde | Dados | O que roda | Quem executa |
|---|---|---|---|
| GitHub Actions (`.github/workflows/ci.yml`) | sintéticos (`ingestion/demo_seed.py`) | pytest + `dbt seed/run/test` | automático, a cada push |
| Máquina do autor | carga real (48.681 flagrantes) | `dbt test` | manual, registrado abaixo |

Os dados reais não são versionados, então os números da carga real **não** podem ser
reproduzidos pelo CI. O CI prova que o código e os testes funcionam; o registro abaixo
mostra o resultado na carga real.

## Carga real — 22/10/2026
Extração de 19/10/2026: API informou 48.681 documentos da classe 280; gravados 48.681.

```
$ dbt test   (trecho da saída)
Warning in test assert_datas_antigas            Got 92 results, configured to warn if != 0
Warning in test assert_decisao_antes_do_ajuizamento  Got 15 results, configured to warn if != 0
Done. PASS=21 WARN=2 ERROR=0 SKIP=0 TOTAL=23
```
Os dois avisos são esperados e estão documentados no README (datas anteriores a 1990
e decisões registradas antes da entrada).

## Dados sintéticos — 22/10/2026 (mesmos comandos do CI)
```
python -m pytest -q                      16 passed
python -m ingestion.demo_seed            Inseridos/atualizados: 330
dbt seed / dbt run / dbt test            Done. PASS=23 WARN=0 ERROR=0 SKIP=0 TOTAL=23
```
Nos sintéticos não há datas antigas nem decisões antes da entrada, por isso os dois
testes de aviso passam. Os 300 flagrantes fictícios cobrem as 4 situações do desfecho
(150 · 90 · 30 · 30), os dois formatos de data e os casos de órgão (código 0 e nome repetido).

**Uma trava que funcionou durante a preparação do CI:** a primeira versão dos dados
sintéticos gerava datas até 2028. O teste bloqueante `assert_datas_nao_futuras` falhou
com 95 registros, e as datas foram corrigidas antes do commit.
