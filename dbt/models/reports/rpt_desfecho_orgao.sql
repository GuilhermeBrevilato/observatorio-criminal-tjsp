-- Página "Órgão julgador". Órgãos com poucos casos distorcem percentuais:
-- `amostra_suficiente` marca os que têm ao menos 30 decisões identificáveis.
-- Uma linha por CÓDIGO de órgão. `orgao_rotulo` (nome + código) é único: nomes se repetem
-- entre órgãos diferentes (ex.: "VARA REGIONAL DAS GARANTIAS" em 4 códigos) e o Power BI
-- agruparia pelo nome, somando percentuais.
-- Código 0 ou nulo = órgão não informado no DataJud: uma linha só, fora do ranking.
-- O mesmo código aparece com grafias diferentes (ex.: "MOGI MIRIM" e "MOJI MIRIM",
-- "01 CUMULATIVA" e "VARA UNICA"): o nome exibido é o mais frequente do código.
WITH base AS (
  SELECT f.*, coalesce(orgao_codigo, 0) AS cod
  FROM {{ ref('fct_desfecho_flagrante') }} f
)
SELECT
  cod                                            AS orgao_codigo,
  mode() WITHIN GROUP (ORDER BY orgao_nome) AS orgao_nome,
  CASE
    WHEN cod = 0 THEN 'Órgão não informado'
    ELSE coalesce(nullif(trim(mode() WITHIN GROUP (ORDER BY orgao_nome)), ''), 'Nome não informado') || ' · cód. ' || cod
  END                                            AS orgao_rotulo,
  (cod <> 0)                                     AS orgao_informado,
  count(*)                                       AS flagrantes,
  count(*) FILTER (WHERE desfecho_identificavel) AS com_desfecho,
  round(100.0 * count(*) FILTER (WHERE desfecho_identificavel) / NULLIF(count(*), 0), 1) AS pct_identificavel,
  round(100.0 * count(*) FILTER (WHERE primeira_decisao = 'preventiva')
        / NULLIF(count(*) FILTER (WHERE desfecho_identificavel), 0), 1) AS pct_preventiva_sobre_identificaveis,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY horas_ate_decisao_valida) AS mediana_horas_ate_decisao,
  (cod <> 0 AND count(*) FILTER (WHERE desfecho_identificavel) >= 30) AS amostra_suficiente
FROM base
GROUP BY cod
