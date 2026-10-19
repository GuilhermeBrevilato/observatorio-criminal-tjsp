-- Uma linha por movimento de cada processo vigente (~2,8 milhões na classe 280).
-- Tabela (não view): o JSON é desmontado uma vez, e o Power BI lê rápido.
{{ config(materialized='table') }}
SELECT
  p.document_id,
  p.classe_codigo,
  m.ordem,
  NULLIF(m.mov->>'codigo', '')::integer AS movimento_codigo,
  m.mov->>'nome' AS movimento_nome,
  mp.categoria,
  mp.grupo,
  m.mov->>'dataHora' AS data_hora_original,
  {{ target.schema }}.safe_timestamptz(m.mov->>'dataHora') AS data_hora,
  -- Data utilizável em cálculo de tempo: existe, não é o "dia zero" de sistemas
  -- antigos (1899-12-30, 17 casos na carga real) e não está no futuro.
  COALESCE({{ target.schema }}.safe_timestamptz(m.mov->>'dataHora') >= TIMESTAMPTZ '1900-01-01'
           AND {{ target.schema }}.safe_timestamptz(m.mov->>'dataHora') <= now() + INTERVAL '1 day',
           false) AS data_valida,
  COALESCE(m.mov->'complementosTabelados', '[]'::jsonb) AS complementos
FROM {{ ref('stg_processos') }} p
CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(p.movimentos) = 'array' THEN p.movimentos ELSE '[]'::jsonb END
) WITH ORDINALITY AS m(mov, ordem)
LEFT JOIN {{ ref('mapa_movimentos') }} mp
  ON mp.codigo = NULLIF(m.mov->>'codigo', '')::integer
WHERE p.vigente
