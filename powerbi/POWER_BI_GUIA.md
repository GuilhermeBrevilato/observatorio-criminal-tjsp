# Power BI: roteiro do painel

Painel de **4 páginas** sobre os autos de prisão em flagrante (classe 280) do TJSP.
Cada página lê uma tabela já pronta no dbt: **nenhum cálculo de negócio no Power BI**,
só medidas de soma e divisão. Os números são testados no dbt antes de chegar aqui.

Ordem da história: **primeiro o que os dados mostram com segurança, depois onde eles falham.**

## 1. Conectar (Power BI no Parallels, banco no Docker do Mac)
1. No Mac: `docker compose up -d`, depois `dbt seed`, `dbt run` e `dbt test` **sem erro** (com erro, não atualize o painel).
2. No Windows, confirme que o Mac responde: `Test-NetConnection 10.211.55.2 -Port 5433`
   (`10.211.55.2` é o Mac visto de dentro do Parallels; `10.211.55.1` é o gateway e não funciona).
3. Power BI → **Obter dados → Banco de dados PostgreSQL**
   - Servidor: `10.211.55.2:5433` · Banco: `observatorio` · Modo: **Importar**
   - Credenciais (aba *Banco de dados*): `observatorio` / `observatorio`
4. Importe do esquema `analytics`:
   `rpt_desfecho_mensal`, `rpt_tempo_faixas`, `rpt_desfecho_orgao`, `fct_desfecho_flagrante`, `qa_cobertura`, `qa_desfecho`.
   Não importe `fct_movimentos` (~2,8 milhões de linhas; não é usada no painel).
5. Renomeie as tabelas tirando o prefixo `analytics ` (as medidas usam os nomes sem prefixo).
6. **Exibição de modelo:** apague qualquer relacionamento que o Power BI tenha criado sozinho.
   As tabelas são independentes; um relacionamento automático pode filtrar números sem você perceber.
7. **Exibir → Temas → Procurar temas** → `powerbi/tema_observatorio.json` (cores, fontes, fundo e bordas).
8. O `.pbix` guarda os dados importados: fica fora do Git (`*.pbix` no `.gitignore`).

## 2. Medidas (numa tabela `Medidas`)
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
**Medidas de exibição (só para cartões).** O cartão novo do Power BI abrevia números ("48,68 Mil");
texto não é abreviado. As medidas originais continuam sendo usadas nos gráficos.
```dax
Flagrantes (cartão) = FORMAT([Flagrantes], "#,0")
Com desfecho (cartão) = FORMAT([Com desfecho], "#,0")
% identificável (cartão) = FORMAT([% identificável], "0.0%")
Mediana horas (cartão) = FORMAT([Mediana horas], "0.0") & " h"
% em até 24 h (cartão) = FORMAT([% decididos em até 24 h], "0.0%")
```
**Por que medidas e não as colunas `pct_...`:** percentual não se soma nem se tira média entre meses.
A medida recalcula a divisão sobre os totais. As colunas `pct_...` servem para conferência linha a linha.

## 3. Padrão visual (todas as páginas)
- **Cabeçalho:** faixa verde com título e subtítulo; à direita, "Projeto de portfólio". Sem logo de nenhuma instituição.
- **Navegação:** faixa verde-escura com **Inserir → Botões → Navegador → Navegador de páginas**.
- **Cartões:** título, número e texto de apoio alinhados à esquerda; o texto de apoio diz o período ("todos os anos").
- **Gráficos:** sem rótulo em todos os pontos; eixo com grade clara; avisos no **subtítulo do próprio visual**
  (um print do gráfico leva o aviso junto).
- **Rodapé:** `Fonte: CNJ / DataJud — TJSP, classe 280 (Auto de Prisão em Flagrante). Extração completa e conferida com a API. Elaboração própria.`
- **Sem filtro de página.** Todo filtro fica no próprio visual e é dito no título ou subtítulo.

## 4. Páginas

### Página 1 · Visão geral — "o que os dados mostram"
- **4 cartões** (todos os anos): `Flagrantes (cartão)` · `Com desfecho (cartão)` · `% identificável (cartão)` · `Mediana horas (cartão)`
- **Faixa de aviso** (cartão largo, sem título, fonte 14–16): medida `Base do desfecho`
- **Barras horizontais:** valores `% liberdade`, `% preventiva`, `% relaxamento`, com rótulo de dados
  - Título: "Primeira decisão sobre a prisão"
  - Subtítulo: "Percentual sobre os flagrantes com decisão identificável · todos os anos.
    Relaxamento inclui não homologação. Prisão domiciliar: 5 casos."
- **Conferência:** 48.681 · 22.899 · 47,0% · 13,9 h · liberdade 73,7% · preventiva 23,2% · relaxamento 3,1%

### Página 2 · Tempo até a decisão
- **2 cartões:** `Mediana horas (cartão)` · `% em até 24 h (cartão)`
- **Colunas empilhadas:** eixo `rpt_tempo_faixas[faixa]`, **classificado por `faixa_ordem`**
  (selecione a coluna `faixa` → Ferramentas de coluna → Classificar por coluna → `faixa_ordem`),
  valor `flagrantes`, legenda `primeira_decisao`
  - Título: "Flagrantes por tempo até a primeira decisão"
  - Subtítulo obrigatório: "Tempo entre a entrada do flagrante no TJSP e a primeira decisão sobre a prisão.
    Não é o tempo desde a prisão. Todos os anos; exclui registros com decisão antes da entrada."
- **Conferência:** a mediana bate com a página 1; o total das colunas = número de flagrantes com tempo válido
  (`SELECT count(horas_ate_decisao_valida) FROM analytics.fct_desfecho_flagrante;`)

### Página 3 · Por órgão julgador
- **Tabela** (`rpt_desfecho_orgao`): **`orgao_rotulo`** (nunca `orgao_nome`), `flagrantes`, `com_desfecho`,
  `pct_preventiva_sobre_identificaveis`, `mediana_horas_ate_decisao`
  - Cabeçalhos renomeados no visual: Órgão julgador · Flagrantes · Decisões identificáveis · % preventiva* · Mediana (h)
  - Em `pct_...` e `mediana_...`: **Não resumir** (somar percentuais dá número inexistente)
  - Por que `orgao_rotulo`: "VARA REGIONAL DAS GARANTIAS" é o nome de 4 órgãos diferentes; agrupado
    pelo nome, o Power BI juntaria os 4 e somaria os percentuais
- **Cartões:** órgãos com flagrantes · órgãos na tabela (30+) · flagrantes nesses órgãos · % do total
- **Filtro do visual:** `amostra_suficiente = Verdadeiro`
- **Ordenação:** `flagrantes`, decrescente
- **Subtítulo:** "* Sobre os flagrantes com decisão identificável. Só órgãos com ao menos 30 decisões
  identificáveis: com menos, o percentual oscila demais. Todos os anos."
- **Como interpretar:** "As diferenças entre órgãos podem refletir o tipo de órgão (plantão, central de
  custódia, vara comum) e o perfil dos casos que cada um recebe, não a conduta de cada juiz."
- O "Órgão não informado" (código 0 no DataJud) fica fora da tabela e é contado na página Qualidade
- **Conferência:** `SELECT count(*) FROM analytics.rpt_desfecho_orgao WHERE amostra_suficiente;` = número de linhas da tabela

### Página 4 · Qualidade dos dados — "onde os dados falham"
- **Gráfico de linhas** (o achado principal): eixo `rpt_desfecho_mensal[mes_ajuizamento]`, valor `Flagrantes`, não suavizado
  - Filtro **do visual**: `mes_ajuizamento` a partir de 01/01/2024
  - Título: "Processos hoje na classe 280, por mês de entrada no TJSP"
  - Subtítulo: "Não mede o volume de prisões no tempo: processos saem da classe 280 com o tempo,
    os meses recentes chegam incompletos e em fev/2025 mudou a forma de envio."
  - Análise → Linha X constante, cinza tracejada: **01/02/2025** "mudança no envio dos dados";
    **01/09/2026** "mês incompleto" (sem a data no rótulo)
- **Tabela** `qa_cobertura` (indicador, quantidade, pct_do_total)
- **Tabela** `qa_desfecho` (indicador, quantidade, pct_dos_flagrantes)
- **Caixa de texto:** os quatro achados, uma linha cada:
  1. o DataJud indexa a data compacta como ano 2611: a extração não filtra data na fonte;
  2. a data compacta está em UTC: lida no horário de SP, 5% dos tempos ficavam negativos;
  3. a decisão sobre a prisão só é identificável em 47% dos flagrantes;
  4. a série mensal mostra os processos que estão hoje na classe 280, não o volume de prisões no tempo
     (quebra em fev/2025, meses recentes inflados e o último mês incompleto).

## 5. Antes de publicar ou mostrar
- [ ] `dbt test` sem erro (avisos estão documentados na página 4)
- [ ] Cartão `Flagrantes` = total de `qa_desfecho` (indicador `flagrantes`) = 48.681
- [ ] A página 1 mostra `Base do desfecho` junto dos percentuais
- [ ] Nenhum relacionamento automático no modelo; nenhum filtro de página
- [ ] Todo gráfico com recorte de período diz o recorte no título ou subtítulo
- [ ] `.pbix` fora do Git
