-- AVISA: a carga real da classe 280 trouxe 92 flagrantes de 1899 a 1989, nos
-- dois formatos e quase todos às 08:00 (provável cadastro posterior de
-- processos antigos). Não é erro de leitura; fica visível, sem bloquear.
{{ config(severity='warn') }}
SELECT document_id, data_ajuizamento_original, data_ajuizamento
FROM {{ ref('stg_processos') }}
WHERE data_ajuizamento < DATE '1990-01-01'
