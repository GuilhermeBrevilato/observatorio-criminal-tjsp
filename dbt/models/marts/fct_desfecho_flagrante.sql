-- Uma linha por auto de prisão em flagrante (classe 280) vigente.
-- Desfecho = a PRIMEIRA decisão sobre a prisão (o que aconteceu logo depois do
-- flagrante), pelos códigos de mapa_movimentos com grupo 'decisao_prisao'.
-- Limite (ver README): a decisão só é identificável em parte dos processos;
-- nos demais ela não está no DataJud ou está como "Outras Decisões" (genérico).
{{ config(materialized='table') }}
WITH flagrantes AS (
  SELECT document_id, numero_processo, data_ajuizamento, orgao_codigo, orgao_nome,
         date_trunc('month', data_ajuizamento AT TIME ZONE 'America/Sao_Paulo')::date AS mes_ajuizamento
  FROM {{ ref('stg_processos') }}
  WHERE classe_codigo = 280 AND vigente
),
decisoes AS (
  SELECT document_id, categoria, data_hora, ordem,
         row_number() OVER (PARTITION BY document_id ORDER BY data_hora, ordem) AS n,
         count(*) OVER (PARTITION BY document_id) AS qtd,
         -- outra categoria de decisão no MESMO instante da primeira = registro ambíguo
         (min(categoria) OVER (PARTITION BY document_id, data_hora)
          <> max(categoria) OVER (PARTITION BY document_id, data_hora)) AS ambigua_no_instante
  FROM {{ ref('fct_movimentos') }}
  WHERE grupo = 'decisao_prisao' AND data_valida
),
eventos AS (
  SELECT document_id,
         bool_or(categoria = 'anpp')            AS teve_anpp,
         bool_or(categoria = 'anpp_cumprido')   AS anpp_cumprido,
         bool_or(categoria = 'transacao_penal') AS teve_transacao_penal,
         bool_or(categoria = 'audiencia_custodia'
                 AND complementos @> '[{"nome": "realizada"}]') AS custodia_realizada,
         bool_or(categoria = 'outras_decisoes') AS teve_outras_decisoes,
         count(*) AS qtd_movimentos
  FROM {{ ref('fct_movimentos') }}
  GROUP BY 1
)
SELECT
  f.document_id,
  f.numero_processo,
  f.data_ajuizamento,
  f.mes_ajuizamento,
  f.orgao_codigo,
  f.orgao_nome,
  d.categoria AS primeira_decisao,
  d.data_hora AS data_primeira_decisao,
  round((extract(epoch FROM d.data_hora - f.data_ajuizamento) / 3600.0)::numeric, 1) AS horas_ate_decisao,
  -- Tempo pronto para médias no painel: vazio quando negativo (registro inconsistente).
  CASE WHEN d.data_hora >= f.data_ajuizamento
       THEN round((extract(epoch FROM d.data_hora - f.data_ajuizamento) / 3600.0)::numeric, 1) END AS horas_ate_decisao_valida,
  (d.data_hora < f.data_ajuizamento) AS decisao_antes_do_ajuizamento,
  COALESCE(d.qtd, 0) AS qtd_decisoes_prisao,
  COALESCE(d.ambigua_no_instante, false) AS decisao_ambigua,
  (d.categoria IS NOT NULL) AS desfecho_identificavel,
  COALESCE(e.qtd_movimentos, 0) AS qtd_movimentos,
  COALESCE(e.teve_anpp, false) AS teve_anpp,
  COALESCE(e.anpp_cumprido, false) AS anpp_cumprido,
  COALESCE(e.teve_transacao_penal, false) AS teve_transacao_penal,
  COALESCE(e.custodia_realizada, false) AS custodia_realizada,
  COALESCE(e.teve_outras_decisoes, false) AS teve_outras_decisoes
FROM flagrantes f
LEFT JOIN decisoes d ON d.document_id = f.document_id AND d.n = 1
LEFT JOIN eventos e ON e.document_id = f.document_id
