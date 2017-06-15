-- arguments text_terms:string "%(text_terms)s"
SELECT row_to_json(combined_rows) as results
FROM (
WITH weighted_query_results AS (
  SELECT
    module_ident,
    cast(sum(weight) as bigint) as weight,
    semilist(keys) as keys
  FROM
    ({queries}) as matched
  -- table join...
  GROUP BY module_ident

  ),
derived_weighted_query_results AS (
  SELECT
    wqr.module_ident,
    CASE WHEN lm.parent IS NULL THEN weight + 1
         ELSE weight
    END AS weight,
    keys
  FROM weighted_query_results AS wqr
       LEFT JOIN latest_modules AS lm ON (wqr.module_ident = lm.module_ident)
  )
SELECT
  {columns}
FROM
  latest_modules AS lm
  NATURAL LEFT JOIN abstracts AS ab
  NATURAL LEFT JOIN modulefti AS mfti
  {limits}
  LEFT OUTER JOIN recent_hit_ranks ON (lm.uuid = document),
  derived_weighted_query_results AS wqr
WHERE
  wqr.module_ident = lm.module_ident
  AND lm.portal_type not in  ('CompositeModule','SubCollection')
  {filters}
  {groupby}
ORDER BY {sorts}

) as combined_rows

{size}
;
