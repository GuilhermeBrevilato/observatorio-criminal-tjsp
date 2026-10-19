-- Quanto da origem chega ao modelo analítico, e por que o resto fica de fora.
-- Alimenta a página "Qualidade" do Power BI.
WITH base AS (
  SELECT
    count(*)                                                        AS total_documentos,
    count(*) FILTER (WHERE data_ajuizamento_original IS NULL
                        OR data_ajuizamento_original = '')          AS sem_data,
    count(*) FILTER (WHERE data_ajuizamento_original <> ''
                       AND data_ajuizamento IS NULL)                AS data_invalida,
    count(*) FILTER (WHERE data_ajuizamento < DATE '1990-01-01'
                        OR data_ajuizamento > now() + INTERVAL '1 day') AS data_implausivel,
    count(*) FILTER (WHERE data_ajuizamento_original ~ '^\d{14}$')  AS data_formato_compacto,
    count(*) FILTER (WHERE classe_codigo IS NULL)                   AS sem_classe,
    count(*) FILTER (WHERE municipio_ibge IS NULL)                  AS sem_municipio_ibge,
    count(*) FILTER (WHERE orgao_codigo IS NULL)                    AS sem_orgao,
    count(*) FILTER (WHERE NOT vigente)                             AS fora_da_ultima_carga,
    count(*) FILTER (WHERE data_ajuizamento IS NOT NULL
                       AND classe_codigo IS NOT NULL AND vigente)   AS incluidos_fct
  FROM {{ ref('stg_processos') }}
)
SELECT indicador, quantidade,
       round(100.0 * quantidade / NULLIF(total_documentos, 0), 1) AS pct_do_total
FROM base
CROSS JOIN LATERAL (VALUES
  ('total_documentos',   total_documentos),
  ('incluidos_fct',      incluidos_fct),
  ('sem_data',           sem_data),
  ('data_invalida',      data_invalida),
  ('data_implausivel',   data_implausivel),
  ('data_formato_compacto', data_formato_compacto),
  ('fora_da_ultima_carga', fora_da_ultima_carga),
  ('sem_classe',         sem_classe),
  ('sem_orgao',          sem_orgao),
  ('sem_municipio_ibge', sem_municipio_ibge)
) AS t(indicador, quantidade)
