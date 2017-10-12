-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: uuid:string, version:string, search_term:string, page_uuid: string
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder]
FROM 
  trees tr, 
  modules m
WHERE 
  m.uuid::text = %(uuid)s AND
  module_version(m.major_version, m.minor_version) = %(version)s AND
  tr.documentid = m.module_ident AND
  tr.parent_id IS NULL AND
  is_collated = True
UNION ALL
SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder]
FROM trees c1 JOIN t ON (c1.parent_id = t.node)
WHERE NOT nodeid = any (t.path)
)
SELECT
m.uuid,
m.major_version as version,
ts_headline(COALESCE(t.title, m.name),
plainto_or_tsquery(%(search_term)s),
E'StartSel="<span class=""q-match"">", StopSel="</span>", MaxFragments=0, HighlightAll=TRUE'
),
ts_headline(
convert_from(f.file, 'utf8'),
plainto_or_tsquery(%(search_term)s),
E'StartSel="<mtext class=""q-match"">", StopSel="</mtext>", MaxFragments=0, HighlightAll=TRUE'
),
ts_rank_cd(cft.module_idx, plainto_or_tsquery(%(search_term)s)) AS rank
FROM
 t left join modules m on t.value = m.module_ident
        join collated_fti cft on cft.item = m.module_ident
        join collated_file_associations cfa on cfa.item = m.module_ident
        join files f on cfa.fileid = f.fileid,
 modules AS book
WHERE
 cft.module_idx @@ plainto_or_tsquery(%(search_term)s) AND 
 m.uuid = (%(page_uuid)s) AND
 cft.context = book.module_ident AND
 cfa.context = book.module_ident AND
 book.uuid = (%(uuid)s) AND
 module_version(book.major_version, book.minor_version) = %(version)s
ORDER BY
 rank,
 path
