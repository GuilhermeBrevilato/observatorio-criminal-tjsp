-- Página "Tempo": distribuição do tempo da entrada no TJSP até a primeira decisão.
-- Atenção ao rótulo: é a entrada do flagrante no tribunal, não a hora da prisão.
WITH base AS (
  SELECT primeira_decisao, horas_ate_decisao_valida AS h
  FROM {{ ref('fct_desfecho_flagrante') }}
  WHERE horas_ate_decisao_valida IS NOT NULL
)
SELECT
  primeira_decisao,
  CASE WHEN h < 6 THEN 1 WHEN h < 12 THEN 2 WHEN h < 24 THEN 3 WHEN h < 48 THEN 4 ELSE 5 END AS faixa_ordem,
  CASE WHEN h < 6 THEN 'até 6 h' WHEN h < 12 THEN '6 a 12 h' WHEN h < 24 THEN '12 a 24 h'
       WHEN h < 48 THEN '24 a 48 h' ELSE 'mais de 48 h' END AS faixa,
  count(*) AS flagrantes
FROM base
GROUP BY 1, 2, 3
