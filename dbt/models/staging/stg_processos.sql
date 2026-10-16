-- Uma linha por documento bruto. Nenhum filtro aqui: o que for descartado
-- adiante fica visível em quality/qa_cobertura.
SELECT
  document_id,
  tribunal,
  NULLIF(source->>'numeroProcesso', '') AS numero_processo,
  source->>'dataAjuizamento' AS data_ajuizamento_original,
  {{ target.schema }}.safe_timestamptz(source->>'dataAjuizamento') AS data_ajuizamento,
  source->>'grau' AS grau,
  NULLIF(source #>> '{classe,codigo}', '')::integer AS classe_codigo,
  source #>> '{classe,nome}' AS classe_nome,
  NULLIF(source #>> '{orgaoJulgador,codigo}', '')::integer AS orgao_codigo,
  source #>> '{orgaoJulgador,nome}' AS orgao_nome,
  NULLIF(source #>> '{orgaoJulgador,codigoMunicipioIBGE}', '')::integer AS municipio_ibge,
  source->'assuntos' AS assuntos,
  ingested_at
FROM raw.datajud_document
WHERE tribunal = 'TJSP'
