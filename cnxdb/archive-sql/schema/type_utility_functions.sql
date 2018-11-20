CREATE OR REPLACE FUNCTION public.book_pages(uuid uuid, version text, as_collated boolean DEFAULT true)
 RETURNS SETOF modules
 LANGUAGE sql
AS $function$
WITH RECURSIVE t(node, title, path,value, depth, corder, is_collated) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder],
           is_collated
    FROM trees tr, modules m
    WHERE m.uuid = $1 AND
          module_version( m.major_version, m.minor_version) = $2 AND
      tr.documentid = m.module_ident AND
      tr.is_collated = $3 AND
      tr.parent_id is NULL
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder], c1.is_collated /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path) AND t.is_collated = c1.is_collated
)
SELECT
m.*
FROM t left join  modules m on t.value = m.module_ident WHERE m.portal_type in ('Module','CompositeModule')

$function$;

CREATE OR REPLACE FUNCTION public.set_canonical(bookid uuid, canonical uuid)
 RETURNS void
 LANGUAGE sql
AS $function$
UPDATE modules set canonical = $2 where uuid in 
    (SELECT bp.uuid from latest_modules lm join
        lateral book_pages(uuid, module_version(major_version, minor_version), False) bp on True
     WHERE lm.uuid = $1
    UNION
     SELECT bp.uuid from latest_modules lm join
        lateral book_pages(uuid, module_version(major_version, minor_version), True) bp on True
     WHERE lm.uuid = $1
)  

$function$;
