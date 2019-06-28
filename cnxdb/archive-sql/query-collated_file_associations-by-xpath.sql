-- ###
-- Copyright (c) 2019, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- Search the collated files by `xpath` against the given array
-- of module_ident's (as `idents`).
-- arguments: xpath:string; idents:list;
SELECT item, array_agg(matches)
FROM (
SELECT
  item,
  unnest(xpath(
    e%(xpath)s, CAST(convert_from(file, 'UTF-8') AS XML),
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
      ARRAY['data',
            'http://www.w3.org/TR/html5/dom.html#custom-data-attribute'],
      ARRAY['cmlnle', 'http://katalysteducation.org/cmlnle/1.0']]
  ))::TEXT AS matches
FROM collated_file_associations AS cfa
NATURAL JOIN files
WHERE cfa.item = any(%(idents)s)
AND cfa.context = %(context)s -- book context
) AS results
GROUP BY item;
