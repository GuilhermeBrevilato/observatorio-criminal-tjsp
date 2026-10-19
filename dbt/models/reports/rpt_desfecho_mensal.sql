-- Página "Visão geral" e "Desfecho": uma linha por mês de ajuizamento.
-- Percentuais de desfecho SEMPRE sobre os flagrantes com decisão identificável.
SELECT
  mes_ajuizamento,
  count(*)                                                           AS flagrantes,
  count(*) FILTER (WHERE desfecho_identificavel)                     AS com_desfecho,
  count(*) FILTER (WHERE primeira_decisao = 'liberdade_provisoria')  AS liberdade,
  count(*) FILTER (WHERE primeira_decisao = 'preventiva')            AS preventiva,
  count(*) FILTER (WHERE primeira_decisao IN ('relaxamento', 'nao_homologacao')) AS relaxamento_ou_nao_homologacao,
  count(*) FILTER (WHERE primeira_decisao = 'domiciliar')            AS domiciliar,
  count(*) FILTER (WHERE teve_anpp)                                  AS com_anpp,
  round(100.0 * count(*) FILTER (WHERE desfecho_identificavel) / NULLIF(count(*), 0), 1) AS pct_identificavel,
  round(100.0 * count(*) FILTER (WHERE primeira_decisao = 'preventiva')
        / NULLIF(count(*) FILTER (WHERE desfecho_identificavel), 0), 1) AS pct_preventiva_sobre_identificaveis,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY horas_ate_decisao_valida) AS mediana_horas_ate_decisao
FROM {{ ref('fct_desfecho_flagrante') }}
GROUP BY 1
