-- BLOQUEIA: os quatro grupos da barra "O que se sabe sobre a decisão" (página Qualidade)
-- não se sobrepõem e somam o total de flagrantes. Se falhar, a barra do painel não fecha 100%.
WITH q AS (SELECT indicador, quantidade FROM {{ ref('qa_desfecho') }})
SELECT *
FROM (
  SELECT
    (SELECT quantidade FROM q WHERE indicador = 'flagrantes') AS total,
    (SELECT sum(quantidade) FROM q WHERE indicador IN (
        'desfecho_identificavel', 'sem_desfecho_com_outras_decisoes',
        'com_movimentos_sem_decisao_prisao', 'sem_nenhum_movimento')) AS soma_grupos
) t
WHERE total IS DISTINCT FROM soma_grupos
