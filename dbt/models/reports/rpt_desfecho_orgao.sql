-- Página "Por órgão julgador". Órgãos com poucos casos distorcem percentuais:
-- `amostra_suficiente` marca os que têm ao menos 30 decisões identificáveis.
SELECT
  orgao_codigo,
  orgao_nome,
  count(*)                                       AS flagrantes,
  count(*) FILTER (WHERE desfecho_identificavel) AS com_desfecho,
  round(100.0 * count(*) FILTER (WHERE desfecho_identificavel) / NULLIF(count(*), 0), 1) AS pct_identificavel,
  round(100.0 * count(*) FILTER (WHERE primeira_decisao = 'preventiva')
        / NULLIF(count(*) FILTER (WHERE desfecho_identificavel), 0), 1) AS pct_preventiva_sobre_identificaveis,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY horas_ate_decisao_valida) AS mediana_horas_ate_decisao,
  (count(*) FILTER (WHERE desfecho_identificavel) >= 30) AS amostra_suficiente
FROM {{ ref('fct_desfecho_flagrante') }}
GROUP BY 1, 2
