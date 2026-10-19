# Power BI: roteiro do painel

Painel de 5 páginas sobre os autos de prisão em flagrante (classe 280) do TJSP.
Cada página lê uma tabela já pronta no dbt: **nenhum cálculo de negócio no Power BI**,
só medidas de soma e divisão. Os números são testados no dbt antes de chegar aqui.

## 1. Conectar (Power BI no Parallels, banco no Docker do Mac)
1. No Mac: `docker compose up -d`, depois `dbt seed`, `dbt run` e `dbt test` **sem erro** (com erro, não atualize o painel).
2. No Windows, descubra o endereço do Mac: `ipconfig | findstr "Gateway"` (padrão do Parallels: `10.211.55.1`).
3. Power BI → **Obter dados → Banco de dados PostgreSQL**
   - Servidor: `10.211.55.1:5433` · Banco: `observatorio` · Modo: **Importar**
   - Credenciais (aba *Banco de dados*): `observatorio` / `observatorio`
4. Importe do esquema `analytics`:
   `rpt_desfecho_mensal`, `rpt_tempo_faixas`, `rpt_desfecho_orgao`, `fct_desfecho_flagrante`, `qa_cobertura`, `qa_desfecho`.
   Não importe `fct_movimentos` (~2,8 milhões de linhas; não é usada no painel).
5. **Exibição de modelo:** apague qualquer relacionamento que o Power BI tenha criado sozinho.
   As tabelas são independentes; um relacionamento automático pode filtrar números sem você perceber.

## 2. Medidas (crie numa tabela de medidas)
```dax
Flagrantes = SUM(rpt_desfecho_mensal[flagrantes])
Com desfecho = SUM(rpt_desfecho_mensal[com_desfecho])
% identificável = DIVIDE([Com desfecho], [Flagrantes])

% liberdade = DIVIDE(SUM(rpt_desfecho_mensal[liberdade]), [Com desfecho])
% preventiva = DIVIDE(SUM(rpt_desfecho_mensal[preventiva]), [Com desfecho])
% relaxamento = DIVIDE(SUM(rpt_desfecho_mensal[relaxamento_ou_nao_homologacao]), [Com desfecho])

Base do desfecho =
    FORMAT([Com desfecho], "#,0") & " de " & FORMAT([Flagrantes], "#,0")
    & " flagrantes têm a decisão sobre a prisão identificável"

Mediana horas = MEDIAN(fct_desfecho_flagrante[horas_ate_decisao_valida])
% decididos em até 24 h =
    DIVIDE(CALCULATE(SUM(rpt_tempo_faixas[flagrantes]), rpt_tempo_faixas[faixa_ordem] <= 3),
           SUM(rpt_tempo_faixas[flagrantes]))
```
**Por que medidas e não as colunas `pct_...`:** percentual não se soma nem se tira média entre meses.
A medida recalcula a divisão sobre os totais do período filtrado. As colunas `pct_...` das tabelas
servem só para conferência linha a linha.

## 3. Páginas

### Página 1 · Visão geral
- **Cartões:** `Flagrantes` · `Com desfecho` · `% identificável` · `Mediana horas`
- **Gráfico de linhas:** eixo `rpt_desfecho_mensal[mes_ajuizamento]`, valor `Flagrantes`, linha **não suavizada**
  - Título: "Processos hoje na classe 280, por mês de entrada no TJSP"
  - Linha X constante em **01/02/2025** (painel Análise), rótulo "mudança no envio dos dados"
  - Aviso logo abaixo, obrigatório: "Não mede o volume de prisões no tempo: processos saem da classe 280
    com o tempo, os meses recentes chegam incompletos e em fev/2025 mudou a forma de envio.
    Ver a página Qualidade e o README."
- **Filtros da página (os dois):** `rpt_desfecho_mensal[mes_ajuizamento]` **e**
  `fct_desfecho_flagrante[mes_ajuizamento]`, ambos a partir de **2024-01-01**.
  As tabelas não têm relacionamento: o filtro numa não chega à outra. Sem o segundo filtro,
  o cartão `Mediana horas` mostraria todos os anos ao lado de cartões só de 2024 em diante.
- **Caixa de texto:** "Autos de prisão em flagrante do TJSP na classe atual 280 (DataJud/CNJ).
  Processos que mudaram de classe não aparecem; anos anteriores tendem a ter menos registros."

### Página 2 · Desfecho do flagrante
- **Caixa de texto no topo, com a medida `Base do desfecho`** (obrigatória: os percentuais
  valem só para os flagrantes com a decisão identificável)
- **Barras 100% (ou rosca):** `% liberdade`, `% preventiva`, `% relaxamento`
- **Gráfico de linhas:** eixo `mes_ajuizamento`, valor `% preventiva`
- **Colunas:** eixo `mes_ajuizamento`, valor `com_anpp` (acordos de não persecução penal)
- **Filtro da página:** `mes_ajuizamento` a partir de 2024-01-01

### Página 3 · Tempo até a decisão
- **Colunas empilhadas:** eixo `rpt_tempo_faixas[faixa]`, **classificado por `faixa_ordem`**
  (Ferramentas de coluna → Classificar por coluna), valor `flagrantes`, legenda `primeira_decisao`
- **Cartões:** `Mediana horas` · `% decididos em até 24 h`
- **Rótulo obrigatório:** "Tempo entre a **entrada do flagrante no TJSP** e a primeira decisão
  sobre a prisão. Não é o tempo desde a prisão."

### Página 4 · Por órgão julgador
- **Tabela:** `orgao_nome`, `flagrantes`, `com_desfecho`, `pct_preventiva_sobre_identificaveis`,
  `mediana_horas_ate_decisao`
- **Filtro do visual:** `amostra_suficiente = Verdadeiro` (ao menos 30 decisões identificáveis;
  com menos, o percentual oscila demais)
- **Ordenação:** `flagrantes`, decrescente

### Página 5 · Qualidade dos dados
- **Tabela:** `qa_cobertura` (indicador, quantidade, pct_do_total)
- **Tabela:** `qa_desfecho` (indicador, quantidade, pct_dos_flagrantes)
- **Caixa de texto:** os três achados, em uma linha cada:
  1. o DataJud indexa a data compacta como ano 2611: a extração não filtra data na fonte;
  2. a data compacta está em UTC: lida no horário de SP, 5% dos tempos ficavam negativos;
  3. a decisão sobre a prisão só é identificável em 47% dos flagrantes;
  4. a série mensal mostra os processos que estão hoje na classe 280, não o volume de prisões no tempo
     (quebra em fev/2025, meses recentes inflados e o último mês incompleto).

## 4. Rodapé (todas as páginas)
`Fonte: CNJ / DataJud — TJSP, classe 280 (Auto de Prisão em Flagrante). Extração completa e
conferida com a API. Elaboração própria.`

## 5. Antes de publicar ou mostrar
- [ ] `dbt test` sem erro (avisos estão documentados na página 5)
- [ ] `Flagrantes` sem filtro = total de `qa_desfecho` (indicador `flagrantes`)
- [ ] Toda página de desfecho mostra `Base do desfecho`
- [ ] Nenhum relacionamento automático no modelo
