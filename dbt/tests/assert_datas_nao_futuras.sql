-- BLOQUEIA: data de ajuizamento no futuro é impossível. É o sintoma do defeito
-- do DataJud (texto '20250218171119' indexado como 2611-09-15) caso a leitura
-- da data algum dia falhe. Com falha aqui, o painel não deve ser atualizado.
{{ config(severity='error') }}
SELECT document_id, data_ajuizamento_original, data_ajuizamento
FROM {{ ref('stg_processos') }}
WHERE data_ajuizamento > now() + INTERVAL '1 day'
