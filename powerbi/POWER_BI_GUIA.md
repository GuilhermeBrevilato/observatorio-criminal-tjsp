# Power BI — configuração local

## Conectar
1. Execute `docker compose up -d`, o seed ou a carga real, e `dbt run`.
2. No Power BI Desktop: **Obter dados > Banco de dados PostgreSQL**.
3. Servidor: `localhost:5432`; banco: `observatorio`; autenticação: banco de dados (`observatorio` / `observatorio`).
4. Importe `analytics.fct_processos`, `analytics.agg_ajuizamentos_mensais`, `analytics.fct_desfecho_flagrante`, `analytics.qa_cobertura`, `analytics.qa_desfecho` e, opcionalmente, `analytics.fct_assuntos`. Evite importar `fct_movimentos` inteira (~2,8 milhões de linhas) se não for usá-la.
5. Consulte a configuração do driver Npgsql caso solicitado pelo Power BI.

## Medidas DAX
```dax
Documentos extraídos = DISTINCTCOUNT(fct_processos[document_id])

Órgãos distintos = DISTINCTCOUNT(fct_processos[orgao_codigo])

Classes distintas = DISTINCTCOUNT(fct_processos[classe_codigo])
```

## Medidas de desfecho (DAX)
```dax
Flagrantes com desfecho = CALCULATE(COUNTROWS(fct_desfecho_flagrante), fct_desfecho_flagrante[desfecho_identificavel] = TRUE())

% preventiva (sobre identificáveis) = DIVIDE(CALCULATE(COUNTROWS(fct_desfecho_flagrante), fct_desfecho_flagrante[primeira_decisao] = "preventiva"), [Flagrantes com desfecho])

Mediana horas até decisão = MEDIAN(fct_desfecho_flagrante[horas_ate_decisao_valida])
```
Toda página de desfecho deve exibir a base: "N de M flagrantes têm a decisão identificável".

## Páginas sugeridas
- **Visão Geral:** cartões das três medidas; gráfico de colunas por mês de ajuizamento.
- **Perfil Processual:** contagem por classe e grau; filtros por classe e período.
- **Distribuição institucional:** barras por órgão julgador; tabela por município IBGE.
- **Qualidade:** tabela de `qa_cobertura` (total, incluídos, sem data, data inválida, sem classe, sem órgão, sem município) e período efetivo da amostra.

**Obrigatório:** incluir rodapé `Fonte: CNJ / DataJud — TJSP. Dados da amostra extraída, sem inferência de volume total ou produtividade.`

### Limitações
- A consulta é limitada por `--max-records` e ordenada por timestamp de atualização: **não é amostragem aleatória**.
- `fct_assuntos` possui múltiplas linhas por documento; não some linhas da tabela para contar processos.
- Um número CNJ pode aparecer em múltiplos documentos/graus; evite equipará-lo a 1 processo único sem regras adicionais.
- Município do órgão julgador não equivale ao local do delito.
- O arquivo `.pbix` **não** está incluído, pois exige criação no Power BI Desktop e acesso a um banco populado.
