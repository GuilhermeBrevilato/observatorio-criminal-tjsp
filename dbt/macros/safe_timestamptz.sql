{#
  Cria a função safe_timestamptz(text) no schema do projeto.
  Aceita os formatos que aparecem no DataJud:
    - ISO 8601: 2024-01-15T10:00:00.000Z / 2024-01-15T10:00:00 / 2024-01-15
    - compacto: 20240115100000 (AAAAMMDDhhmmss) / 20240115 (AAAAMMDD)
  Formatos compactos e ISO sem fuso são interpretados no horário de São Paulo.
  Qualquer valor inválido vira NULL em vez de derrubar a consulta inteira.
#}
{% macro create_safe_timestamptz() %}
CREATE SCHEMA IF NOT EXISTS {{ target.schema }};
CREATE OR REPLACE FUNCTION {{ target.schema }}.safe_timestamptz(valor text)
RETURNS timestamptz
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  v text := btrim(valor);
BEGIN
  IF v IS NULL OR v = '' THEN
    RETURN NULL;
  ELSIF v ~ '^\d{14}$' THEN
    RETURN to_timestamp(v, 'YYYYMMDDHH24MISS')::timestamp AT TIME ZONE 'America/Sao_Paulo';
  ELSIF v ~ '^\d{8}$' THEN
    RETURN to_timestamp(v, 'YYYYMMDD')::timestamp AT TIME ZONE 'America/Sao_Paulo';
  ELSIF v ~ '(Z|[+-]\d{2}:?\d{2})$' THEN
    RETURN v::timestamptz;
  ELSE
    RETURN v::timestamp AT TIME ZONE 'America/Sao_Paulo';
  END IF;
EXCEPTION WHEN others THEN
  RETURN NULL;
END;
$$;
{% endmacro %}
