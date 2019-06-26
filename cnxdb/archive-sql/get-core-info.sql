-- ###
-- Copyright (c) 2019, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

-- Given an ident-hash, return the module's core information.
-- arguments: ident_hash:string
SELECT module_ident, portal_type AS type, name AS title, uuid,
       module_version(major_version, minor_version) AS version,
       ident_hash(uuid, major_version, minor_version) AS ident_hash
FROM modules
WHERE ident_hash(uuid, major_version, minor_version) = %(ident_hash)s;
