-- ###
-- Copyright (c) 2018, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string; p_id:string
WITH RECURSIVE t(node, parent, path, value) AS (
  SELECT nodeid, parent_id, ARRAY[nodeid], documentid
  FROM trees tr, modules m
  WHERE m.uuid = %(p_id)s::uuid
  AND tr.documentid = m.module_ident
  AND tr.parent_id IS NOT NULL
UNION ALL
  SELECT c1.nodeid, c1.parent_id,
         t.path || ARRAY[c1.nodeid], c1.documentid
  FROM trees c1
  JOIN t ON (c1.nodeid = t.parent)
  WHERE not nodeid = any (t.path)
)

SELECT module_version(major_version, minor_version) AS version
FROM t JOIN modules ON t.value = module_ident
WHERE t.parent IS NULL AND uuid = %(id)s::uuid 
ORDER BY uuid, major_version DESC, minor_version DESC LIMIT 1;

