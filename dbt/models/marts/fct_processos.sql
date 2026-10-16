-- Uma linha por documento DataJud (instância/capa), não por número CNJ.
SELECT
  document_id, numero_processo, tribunal, grau, data_ajuizamento,
  date_trunc('month', data_ajuizamento)::date AS mes_ajuizamento,
  classe_codigo, classe_nome,
  orgao_codigo, orgao_nome, municipio_ibge,
  ingested_at
FROM {{ ref('stg_processos') }}
WHERE data_ajuizamento IS NOT NULL AND classe_codigo IS NOT NULL
