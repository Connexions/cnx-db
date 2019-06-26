-- ###
-- Copyright (c) 2019, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- Given an ident-hash for a book, return the core information about
-- the collection (aka book) and book's modules core information.
-- arguments: ident_hash:string; is_collated:boolean;
WITH RECURSIVE t(node, title, path, value, is_collated) AS (
    SELECT
      nodeid,
      title,
      ARRAY [nodeid],
      documentid,
      is_collated
    FROM trees AS tr, modules AS m
    WHERE ident_hash(m.uuid, m.major_version, m.minor_version) = %(ident_hash)s
     AND tr.documentid = m.module_ident
     AND tr.is_collated = %(is_collated)s

  UNION ALL

    /* Recursion */
    SELECT
      c1.nodeid,
      c1.title,
      t.path || ARRAY [c1.nodeid],
      c1.documentid,
      c1.is_collated
    FROM trees AS c1
    JOIN t ON (c1.parent_id = t.node)
    WHERE NOT nodeid = ANY (t.path) AND t.is_collated = c1.is_collated
)
SELECT DISTINCT
  m.module_ident AS module_ident,
  m.portal_type AS type,
  coalesce(t.title, m.name) AS title,
  m.uuid AS uuid,
  module_version(m.major_version, m.minor_version) AS version,
  ident_hash(m.uuid, m.major_version, m.minor_version) as ident_hash
FROM t JOIN modules m ON t.value = m.module_ident;
