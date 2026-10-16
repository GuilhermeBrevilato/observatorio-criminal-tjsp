SELECT
  p.document_id,
  NULLIF(item->>'codigo', '')::integer AS assunto_codigo,
  item->>'nome' AS assunto_nome
FROM {{ ref('stg_processos') }} p
CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(p.assuntos) = 'array' THEN p.assuntos ELSE '[]'::jsonb END
) item
WHERE item ? 'codigo'
