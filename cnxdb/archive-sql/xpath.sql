-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: document_uuid:string document_version:string xpath_string:string

SELECT name, uuid, version, array_agg(xpath_result) FROM (
  WITH RECURSIVE t(node, title, path, value) AS (
    SELECT
      nodeid,
      title,
      ARRAY [nodeid],
      documentid
    FROM trees tr, modules m
    WHERE m.uuid = %(document_uuid)s::UUID
    AND module_version(m.major_version, m.minor_version) = %(document_version)s
    AND tr.documentid = m.module_ident
    AND tr.parent_id IS NULL
    UNION ALL
      SELECT c1.nodeid, c1.title, t.path || ARRAY [c1.nodeid], c1.documentid /* Recursion */
      FROM trees c1
      JOIN t ON (c1.parent_id = t.node)
    WHERE NOT nodeid = ANY (t.path)
  )
  SELECT DISTINCT
    m.name AS name,
    m.uuid AS uuid,
    module_version(m.major_version, m.minor_version) AS version,
    -- TODO move the unnest(xpath()) block into its own function because DRY
    unnest(xpath(e%(xpath_string)s, CAST(convert_from(file, 'UTF-8') AS XML),
                 ARRAY[ARRAY['cnx', 'http://cnx.rice.edu/cnxml'],
                       ARRAY['c', 'http://cnx.rice.edu/cnxml'],
                       ARRAY['system', 'http://cnx.rice.edu/system-info'],
                       ARRAY['math', 'http://www.w3.org/1998/Math/MathML'],
                       ARRAY['mml', 'http://www.w3.org/1998/Math/MathML'],
                       ARRAY['m', 'http://www.w3.org/1998/Math/MathML'],
                       ARRAY['md', 'http://cnx.rice.edu/mdml'],
                       ARRAY['qml', 'http://cnx.rice.edu/qml/1.0'],
                       ARRAY['bib', 'http://bibtexml.sf.net/'],
                       ARRAY['xhtml', 'http://www.w3.org/1999/xhtml'],
                       ARRAY['h', 'http://www.w3.org/1999/xhtml'],
                       ARRAY['data', 'http://www.w3.org/TR/html5/dom.html#custom-data-attribute'],
                       ARRAY['cmlnle', 'http://katalysteducation.org/cmlnle/1.0']]
          ))::TEXT as xpath_result
  FROM t
    JOIN module_files mf ON t.value = mf.module_ident
    JOIN modules m ON t.value = m.module_ident
    JOIN files f ON mf.fileid = f.fileid

  WHERE filename = 'index.cnxml'
) tree

GROUP BY name, uuid, version;
