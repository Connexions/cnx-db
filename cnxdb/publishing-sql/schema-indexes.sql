-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###


CREATE INDEX "pending_resources_hash_idx" on "pending_resources" ("hash");
CREATE INDEX "pending_documents_ident_hash" on pending_documents (ident_hash(uuid, major_version, minor_version));
CREATE INDEX document_baking_result_associations_module_ident_fkey ON document_baking_result_associations (module_ident);
