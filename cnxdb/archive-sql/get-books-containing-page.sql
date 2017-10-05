-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: document_uuid:string; document_version:string
WITH RECURSIVE t(node, title, parent, path, value) AS (
  SELECT nodeid, title, parent_id, ARRAY[nodeid], documentid
  FROM trees tr, modules m
  WHERE m.uuid = %(document_uuid)s::uuid
  AND module_version(m.major_version, m.minor_version) = %(document_version)s
  AND tr.documentid = m.module_ident
  AND tr.parent_id IS NOT NULL
UNION ALL
  SELECT c1.nodeid, c1.title, c1.parent_id,
         t.path || ARRAY[c1.nodeid], c1.documentid
  FROM trees c1
  JOIN t ON (c1.nodeid = t.parent)
  WHERE not nodeid = any (t.path)
),

books(uuid, major_version, minor_version, title) AS (
  SELECT m.uuid, m.major_version, m.minor_version, COALESCE(t.title, m.name),
         m.authors
  FROM t
  JOIN modules m ON t.value = m.module_ident
  WHERE t.parent IS NULL
  ORDER BY uuid, major_version desc, minor_version desc
),

page(authors) as (
  SELECT authors FROM modules m
  WHERE m.uuid = %(document_uuid)s::uuid
  AND module_version(m.major_version, m.minor_version) = %(document_version)s
),

top_books(title, ident_hash, authors) AS (
SELECT first(title),
       ident_hash(uuid, first(major_version), first(minor_version)),
       first(authors)
  FROM books GROUP BY uuid
)

SELECT tb.title, tb.ident_hash, tb.authors
  FROM top_books tb, page p ORDER BY tb.authors = p.authors DESC

