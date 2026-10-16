-- Contagem de documentos da amostra extraída, NÃO total do TJSP.
SELECT
  mes_ajuizamento, classe_codigo, classe_nome, grau,
  count(DISTINCT document_id) AS documentos_amostra
FROM {{ ref('fct_processos') }}
GROUP BY 1,2,3,4
