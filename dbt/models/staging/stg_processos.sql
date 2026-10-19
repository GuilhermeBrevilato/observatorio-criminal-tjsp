-- Uma linha por documento bruto. Nada é descartado aqui: o que fica de fora
-- adiante aparece, com o motivo, em quality/qa_cobertura.
WITH ultima_carga AS (
  -- Início da última carga COMPLETA e conferida de cada classe.
  SELECT c::int AS classe_codigo, max(started_at) AS inicio
  FROM raw.ingestion_checkpoint,
       jsonb_array_elements_text((job::jsonb) -> 'class_codes') AS c
  WHERE status = 'done'
  GROUP BY 1
),
base AS (
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
)
SELECT
  b.*,
  -- Documento visto na última carga completa da sua classe? Se não foi, ele
  -- saiu da classe (ou do índice) desde então e é uma cópia velha: não entra
  -- nas contagens. Sem carga completa ainda (ex.: só dados de demonstração),
  -- tudo é considerado vigente.
  (u.inicio IS NULL OR b.ingested_at >= u.inicio) AS vigente
FROM base b
LEFT JOIN ultima_carga u USING (classe_codigo)
