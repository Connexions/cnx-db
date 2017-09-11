-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: document_uuid:string document_version:string xpath_string:string

SELECT name, uuid, version, array_agg(xpath_result) FROM (
  -- TODO move the unnest(xpath()) block into its own function because DRY
  SELECT m.name AS name, m.uuid AS uuid,
    module_version(m.major_version, m.minor_version) AS version,
    unnest(
        xpath(e%(xpath_string)s, CAST(convert_from(file, 'UTF-8') AS XML),
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
        )
    )::TEXT AS xpath_result
FROM modules m
NATURAL JOIN module_files
NATURAL JOIN files
WHERE m.uuid = %(document_uuid)s::UUID
AND module_version(m.major_version, m.minor_version) = %(document_version)s
AND filename = 'index.cnxml'
) results
GROUP BY name, uuid, version;
