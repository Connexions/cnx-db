-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- arguments: id:string
SELECT
module_version(m.major_version, m.minor_version)
FROM modules m 
        WHERE m.uuid = %(id)s 
            AND m.major_version = (
            SELECT max(major_version) FROM modules m2
                WHERE m.uuid = m2.uuid
        )
        AND
        (m.minor_version IS NULL OR
         m.minor_version = (
            SELECT max(minor_version) FROM modules m3
                WHERE m.uuid = m3.uuid AND
                m.major_version = m3.major_version
            )
    );
