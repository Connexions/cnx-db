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
  SELECT c1.nodeid, c1.title, c1.parent_id, t.path || ARRAY[c1.nodeid], c1.documentid /* Recursion */
  FROM trees c1
  JOIN t ON (c1.nodeid = t.parent)
  WHERE not nodeid = any (t.path)
)
SELECT m.name, m.uuid
FROM t
JOIN modules m on t.value = m.module_ident
WHERE t.parent IS NULL;
