CREATE VIEW all_modules as
	SELECT module_ident, uuid, portal_type, moduleid, version, name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM modules
	UNION ALL
	SELECT module_ident, uuid, portal_type, moduleid, 'latest', name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM latest_modules;

CREATE OR REPLACE VIEW current_modules AS
WITH latest_idents (module_ident) AS (
          SELECT module_ident FROM modules m2 join modulestates ms
                on m2.stateid = ms.stateid
                WHERE m2.major_version = (
                    SELECT max(major_version) FROM modules m3
                        WHERE m2.uuid = m3.uuid
                )
                AND
                (m2.minor_version IS NULL OR
                 m2.minor_version = (
                    SELECT max(minor_version) FROM modules m4
                        WHERE m2.uuid = m4.uuid AND
                        m2.major_version = m4.major_version
                    )
                )
                AND ms.statename = 'current'
        )
SELECT m.* FROM latest_idents li JOIN modules m
ON m.module_ident = li.module_ident;
