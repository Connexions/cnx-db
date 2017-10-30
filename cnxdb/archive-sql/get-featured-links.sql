-- ###
-- Copyright (c) 2014, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments:

SELECT row_to_json(combined_rows) AS featured_links
FROM (SELECT
    m.uuid AS id,
    module_version(m.major_version, m.minor_version) AS version,
    m.name AS title,
    m.moduleid AS legacy_id,
    m.version AS legacy_version,
    a.html AS abstract,
    '/resources/' || files.sha1 AS "resourcePath",
    t.tag AS "type"
FROM featured_books as f
  LEFT JOIN modules as m
    ON (f.uuid=m.uuid
    and (f.major_version=m.major_version OR
         f.major_version is NULL)
    and (f.minor_version=m.minor_version OR
         f.minor_version is NULL))
  LEFT JOIN abstracts as a ON m.abstractid=a.abstractid
  LEFT JOIN moduletags mt ON m.module_ident = mt.module_ident
  LEFT JOIN tags t ON mt.tagid = t.tagid
  LEFT JOIN files
    ON files.fileid = f.fileid
) combined_rows;
