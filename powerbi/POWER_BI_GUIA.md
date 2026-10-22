# Power BI: como o painel foi montado

Painel de **4 páginas** sobre os autos de prisão em flagrante (classe 280) do TJSP:
**Visão geral · Tempo · Órgãos julgadores · Qualidade dos dados**. Imagens em `docs/img/`.

Regra geral: **nenhum cálculo de negócio no Power BI**. Cada visual lê uma tabela pronta e
testada no dbt; o Power BI só soma, divide e formata. O `.pbix` não é versionado (guarda os
dados importados): este guia é o que permite remontá-lo.

## 1. Conectar
1. Rode o pipeline com `dbt test` **sem erro** (com erro, não atualize o painel).
   Sem acesso à API, use os dados sintéticos: `python -m ingestion.demo_seed` (ver README).
2. Power BI → **Obter dados → Banco de dados PostgreSQL**, modo **Importar**.
   - Servidor: `localhost:5433` (Power BI no mesmo computador do Docker) ou, com o Power BI no
     Parallels e o Docker no Mac, `10.211.55.2:5433` (confira com `Test-NetConnection 10.211.55.2 -Port 5433`).
   - Banco `observatorio` · usuário e senha `observatorio`.
3. Importe do esquema `analytics`: `rpt_desfecho_mensal`, `rpt_tempo_faixas`, `rpt_desfecho_orgao`,
   `fct_desfecho_flagrante`, `qa_cobertura`, `qa_desfecho`. Não importe `fct_movimentos` (~2,8 milhões de linhas).
4. Renomeie as tabelas sem o prefixo `analytics ` (as medidas usam os nomes curtos).
5. **Exibição de modelo:** apague qualquer relacionamento criado sozinho. As tabelas são
   independentes; um relacionamento automático filtraria números sem aviso.
6. **Exibir → Temas → Procurar temas** → `powerbi/tema_observatorio.json`.
7. Tela de **todas** as páginas: 16:9, **1920 × 1080**.

## 2. Tabelas digitadas no Power BI (Inserir dados)
**`Decisoes`**: eixo dos gráficos de decisão. Sem relacionamento (tabela desconectada).

| ordem | decisao | decisao_curta (coluna calculada) |
|---|---|---|
| 1 | Liberdade provisória | Liberdade |
| 2 | Prisão preventiva | Preventiva |
| 3 | Relaxamento* | Relaxamento* |

```dax
decisao_curta = SWITCH(Decisoes[ordem], 1, "Liberdade", 2, "Preventiva", 3, "Relaxamento*")
```
`decisao` e `decisao_curta`: **Classificar por coluna → `ordem`**.

**`Achados`**: texto da tabela "Seis achados na fonte" (colunas `n`, `achado`, `evidencia`,
`o_que_foi_feito`), copiado do README. É texto, não dado do banco.

**Colunas calculadas em `qa_desfecho`** (nome legível e ordem da barra da página 4):
```dax
grupo = SWITCH(qa_desfecho[indicador],
    "desfecho_identificavel", "Decisão identificável",
    "sem_desfecho_com_outras_decisoes", "Só ""Outras Decisões""",
    "com_movimentos_sem_decisao_prisao", "Movimentos, sem decisão sobre a prisão",
    "sem_nenhum_movimento", "Nenhum movimento", BLANK())
grupo_ordem = SWITCH(qa_desfecho[indicador],
    "desfecho_identificavel", 1, "sem_desfecho_com_outras_decisoes", 2,
    "com_movimentos_sem_decisao_prisao", 3, "sem_nenhum_movimento", 4, BLANK())
```
`grupo`: **Classificar por coluna → `grupo_ordem`**. `rpt_tempo_faixas[faixa]`: **Classificar por coluna → `faixa_ordem`**.

## 3. Medidas (tabela `Medidas`)
```dax
Flagrantes = SUM(rpt_desfecho_mensal[flagrantes])
Com desfecho = SUM(rpt_desfecho_mensal[com_desfecho])
% identificável = DIVIDE([Com desfecho], [Flagrantes])
% liberdade = DIVIDE(SUM(rpt_desfecho_mensal[liberdade]), [Com desfecho])
% preventiva = DIVIDE(SUM(rpt_desfecho_mensal[preventiva]), [Com desfecho])
% relaxamento = DIVIDE(SUM(rpt_desfecho_mensal[relaxamento_ou_nao_homologacao]), [Com desfecho])
Mediana horas = MEDIAN(fct_desfecho_flagrante[horas_ate_decisao_valida])
% decididos em até 24 h =
    DIVIDE(CALCULATE(SUM(rpt_tempo_faixas[flagrantes]), rpt_tempo_faixas[faixa_ordem] <= 3),
           SUM(rpt_tempo_faixas[flagrantes]))

-- uma medida para o eixo "decisao", em vez de três medidas soltas
% decisão = SWITCH(SELECTEDVALUE(Decisoes[decisao]),
    "Liberdade provisória", [% liberdade], "Prisão preventiva", [% preventiva], "Relaxamento*", [% relaxamento])
Mediana por decisão = SWITCH(SELECTEDVALUE(Decisoes[decisao]),
    "Liberdade provisória", CALCULATE([Mediana horas], fct_desfecho_flagrante[primeira_decisao] = "liberdade_provisoria"),
    "Prisão preventiva",    CALCULATE([Mediana horas], fct_desfecho_flagrante[primeira_decisao] = "preventiva"),
    "Relaxamento*",         CALCULATE([Mediana horas], fct_desfecho_flagrante[primeira_decisao] IN {"relaxamento", "nao_homologacao"}))
Subtítulo desfecho = "Sobre os " & FORMAT([Com desfecho], "#,0") & " flagrantes com decisão identificável · todos os anos"
```
**Medidas de cartão.** O cartão do Power BI abrevia números ("48,68 Mil"); texto não é abreviado.
```dax
Flagrantes (cartão) = FORMAT([Flagrantes], "#,0")
Com desfecho (cartão) = FORMAT([Com desfecho], "#,0")
% identificável (cartão) = FORMAT([% identificável], "0.0%")
Mediana horas (cartão) = FORMAT([Mediana horas], "0.0") & " h"
% em até 24 h (cartão) = FORMAT([% decididos em até 24 h], "0.0%")
Com tempo válido (cartão) = FORMAT(SUM(rpt_tempo_faixas[flagrantes]), "#,0")
Inconsistentes (cartão) = FORMAT(CALCULATE(COUNTROWS(fct_desfecho_flagrante), fct_desfecho_flagrante[decisao_antes_do_ajuizamento] = TRUE()), "#,0")
Órgãos total (cartão) = FORMAT(CALCULATE(COUNTROWS(rpt_desfecho_orgao), rpt_desfecho_orgao[orgao_informado] = TRUE()), "#,0")
Órgãos 30+ (cartão) = FORMAT(CALCULATE(COUNTROWS(rpt_desfecho_orgao), rpt_desfecho_orgao[amostra_suficiente] = TRUE()), "#,0")
Flagrantes 30+ (cartão) = FORMAT(CALCULATE(SUM(rpt_desfecho_orgao[flagrantes]), rpt_desfecho_orgao[amostra_suficiente] = TRUE()), "#,0")
% flagrantes 30+ (cartão) = FORMAT(DIVIDE(CALCULATE(SUM(rpt_desfecho_orgao[flagrantes]), rpt_desfecho_orgao[amostra_suficiente] = TRUE()), SUM(rpt_desfecho_orgao[flagrantes])), "0.0%")
Órgão não informado (cartão) = FORMAT(CALCULATE(SUM(rpt_desfecho_orgao[flagrantes]), rpt_desfecho_orgao[orgao_informado] = FALSE()), "#,0")
Testes (cartão) = "21 passam"   -- texto fixo: o Power BI não lê o resultado do dbt; o cartão traz a data da execução
```
**Por que medidas e não as colunas `pct_...`:** percentual não se soma nem se tira média; a medida
refaz a divisão sobre os totais.

## 4. Padrão de todas as páginas
- Cabeçalho verde-escuro com o nome do painel e "Projeto independente · Portfólio de dados". Sem logo de instituição.
- **Navegador de páginas** (Inserir → Botões → Navegador) logo abaixo; mesma largura nas 4 páginas.
- Título e subtítulo da página; etiquetas "Classe TPU 280" e "Extração: dd/mm/aaaa".
- 4 cartões, um painel de contexto à direita e um rodapé com a fonte.
- **Sem filtro de página.** Filtro, quando há, fica no próprio visual e é dito no título ou subtítulo.
- Gráficos sem rótulo em todo ponto; avisos no subtítulo do próprio visual (o print leva o aviso junto).

## 5. Páginas
### 1 · Visão geral — "Panorama dos flagrantes"
- **Cartões** (todos os anos): processos na classe 280 · com decisão identificável · % com decisão identificável · tempo mediano.
- **Linha** "Processos por mês de entrada no TJSP": eixo `rpt_desfecho_mensal[mes_ajuizamento]`, valor `Flagrantes`,
  **filtro do visual** a partir de 01/01/2024, linha não suavizada; Análise → linha X constante em **01/02/2025**
  ("Mudança no envio · fev/25"); rótulos só em 791, 282, 1.940 e 335.
- **Contexto analítico** (à direita): a série mostra os processos que **hoje** estão na classe 280, não o número de
  prisões; fev/2025 = mudança no envio; ago/2026 (1.940) e set/2026 (335) = meses recentes inflados e mês incompleto.
- **Barras** "Primeira decisão sobre a prisão": eixo Y `Decisoes[decisao]`, eixo X `% decisão`; subtítulo pela medida `Subtítulo desfecho`.
- **Nota metodológica**: os percentuais valem só para os 47% com decisão identificável.
- Rodapé: `* Relaxamento inclui não homologação. Prisão domiciliar (5 casos) não aparece nas barras.`

### 2 · Tempo até a decisão
- **Cartões**: tempo mediano · decisão em menos de 24 h · flagrantes com tempo válido · registros inconsistentes (15, fora da conta).
- **Colunas**: eixo `rpt_tempo_faixas[faixa]` (classificado por `faixa_ordem`), valor `flagrantes`, rótulo com quantidade e %;
  faixas acima de 24 h em verde claro; linha divisória "95,1% antes de 24 h · 4,9% a partir de 24 h".
- **Como ler**: o relógio começa na **entrada no TJSP**, não na prisão; por isso a página **não mede** o prazo de 24 h da audiência de custódia.
- **Mediana por tipo de decisão**: eixo Y `Decisoes[decisao_curta]`, eixo X `Mediana por decisão`.

### 3 · Órgãos julgadores
- **Cartões**: órgãos com flagrantes (órgão informado) · órgãos na tabela (30+ decisões identificáveis) · flagrantes nesses órgãos · % do total.
- **Tabela** (`rpt_desfecho_orgao`): **`orgao_rotulo`** (nunca `orgao_nome`), `flagrantes`, `com_desfecho`,
  `pct_preventiva_sobre_identificaveis`, `mediana_horas_ate_decisao`.
  - Filtro do visual `amostra_suficiente = Verdadeiro`; ordenação por `flagrantes`, decrescente; Totais desligado.
  - Percentual e mediana com **Não resumir**; barra de dados clara (`#C9D3E3`, mínimo 0, máximo 100) na % preventiva.
  - Por que o rótulo: "VARA REGIONAL DAS GARANTIAS" é o nome de 4 órgãos; agrupado pelo nome, o Power BI somaria os percentuais.
- **Como interpretar**: só órgãos com 30+ decisões · **tipo de órgão, não juiz** · 3.154 flagrantes sem órgão ficam fora.

### 4 · Qualidade dos dados
- **Cartões**: carga conferida com a API · decisão identificável · órgão não informado · testes automáticos (texto fixo com a data do `dbt test`).
- **Barra 100% empilhada** "O que se sabe sobre a decisão em cada flagrante": eixo X `qa_desfecho[quantidade]`,
  legenda `qa_desfecho[grupo]`, filtro do visual sem "(Em branco)"; rótulos com quantidade e %, em duas linhas.
  Os 4 grupos somam o total (teste `assert_qa_desfecho_particao`).
- **Tabela** "Seis achados na fonte": tabela `Achados`, quebra de texto ligada.
- **Travas automáticas**: os testes do dbt que bloqueiam e os que avisam.

## 6. Antes de publicar ou mostrar
- [ ] `dbt test` sem erro (os 2 avisos estão documentados na página 4)
- [ ] Cartão de flagrantes = indicador `flagrantes` da `qa_desfecho`
- [ ] Nenhum relacionamento no modelo; nenhum filtro de página
- [ ] Todo recorte de período dito no título ou subtítulo
- [ ] Exportar para PDF **sem** avisos do Power BI na tela (eles saem impressos)
- [ ] `.pbix` fora do Git
