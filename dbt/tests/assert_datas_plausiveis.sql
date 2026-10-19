-- O próprio DataJud indexa '20250218171119' como 2611-09-15 (ver README).
-- Aqui a data vem do TEXTO original; este teste garante que nenhuma data
-- absurda chegou à camada analítica.
{{ config(severity='warn') }}
SELECT document_id, data_ajuizamento_original, data_ajuizamento
FROM {{ ref('stg_processos') }}
WHERE data_ajuizamento < DATE '1990-01-01'
   OR data_ajuizamento > now() + INTERVAL '1 day'
