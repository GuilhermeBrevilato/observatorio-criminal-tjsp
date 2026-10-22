-- O que o painel de desfechos pode afirmar, e sobre qual parte dos flagrantes.
WITH f AS (SELECT * FROM {{ ref('fct_desfecho_flagrante') }}),
total AS (SELECT count(*) AS n FROM f)
SELECT indicador, quantidade,
       CASE WHEN base = 'flagrantes' THEN round(100.0 * quantidade / NULLIF((SELECT n FROM total), 0), 1) END AS pct_dos_flagrantes
FROM (
  SELECT 'flagrantes' AS indicador, count(*) AS quantidade, 'flagrantes' AS base FROM f
  UNION ALL SELECT 'desfecho_identificavel', count(*) FILTER (WHERE desfecho_identificavel), 'flagrantes' FROM f
  UNION ALL SELECT 'sem_desfecho_com_outras_decisoes', count(*) FILTER (WHERE NOT desfecho_identificavel AND teve_outras_decisoes), 'flagrantes' FROM f
  UNION ALL SELECT 'com_movimentos_sem_decisao_prisao', count(*) FILTER (WHERE NOT desfecho_identificavel
                       AND NOT teve_outras_decisoes AND qtd_movimentos > 0), 'flagrantes' FROM f
  UNION ALL SELECT 'sem_nenhum_movimento', count(*) FILTER (WHERE qtd_movimentos = 0), 'flagrantes' FROM f
  UNION ALL SELECT 'decisao_antes_do_ajuizamento', count(*) FILTER (WHERE decisao_antes_do_ajuizamento), 'flagrantes' FROM f
  UNION ALL SELECT 'decisao_ambigua', count(*) FILTER (WHERE decisao_ambigua), 'flagrantes' FROM f
  -- base diferente (movimentos, não flagrantes): sem percentual
  UNION ALL SELECT 'movimentos_com_data_invalida', count(*) FILTER (WHERE NOT data_valida), 'movimentos'
            FROM {{ ref('fct_movimentos') }}
) t
