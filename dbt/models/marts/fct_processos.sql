-- Uma linha por documento DataJud (instância/capa), não por número CNJ.
-- Só documentos vigentes (vistos na última carga completa da classe).
SELECT
  document_id, numero_processo, tribunal, grau, data_ajuizamento,
  -- O mês é o do horário de São Paulo, qualquer que seja o fuso do servidor
  -- (o Postgres do Docker roda em UTC: sem isso, um flagrante às 22h de 31/01
  -- seria contado em fevereiro).
  date_trunc('month', data_ajuizamento AT TIME ZONE 'America/Sao_Paulo')::date AS mes_ajuizamento,
  classe_codigo, classe_nome,
  orgao_codigo, orgao_nome, municipio_ibge,
  ingested_at
FROM {{ ref('stg_processos') }}
WHERE data_ajuizamento IS NOT NULL AND classe_codigo IS NOT NULL AND vigente
