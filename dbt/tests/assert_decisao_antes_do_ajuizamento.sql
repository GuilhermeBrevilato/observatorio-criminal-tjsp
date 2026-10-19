-- AVISA: decisão sobre a prisão registrada antes da entrada do flagrante.
-- Pode ser fuso/horário de registro ou erro na origem; o tempo negativo fica
-- marcado (decisao_antes_do_ajuizamento) e deve ser excluído das médias.
{{ config(severity='warn') }}
SELECT document_id, data_ajuizamento, data_primeira_decisao
FROM {{ ref('fct_desfecho_flagrante') }}
WHERE decisao_antes_do_ajuizamento
