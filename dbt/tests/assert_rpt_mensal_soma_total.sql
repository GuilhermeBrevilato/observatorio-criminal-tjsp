-- BLOQUEIA: a soma dos meses tem que bater com o total de flagrantes com data
-- (a mesma trava que teria pego o defeito das datas do DataJud).
{{ config(severity='error') }}
SELECT r.total_meses, f.total_fct
FROM (SELECT sum(flagrantes) AS total_meses FROM {{ ref('rpt_desfecho_mensal') }} WHERE mes_ajuizamento IS NOT NULL) r,
     (SELECT count(*) AS total_fct FROM {{ ref('fct_desfecho_flagrante') }} WHERE mes_ajuizamento IS NOT NULL) f
WHERE r.total_meses <> f.total_fct
