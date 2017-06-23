# -*- coding: utf-8 -*-


def up(cursor):
    # Latest now knows about baking and recipes for print_style

    cursor.execute("""
ALTER TABLE latest_modules ADD COLUMN baked timestamp with time zone;
ALTER TABLE latest_modules ADD COLUMN recipe integer;
ALTER TABLE modules ADD COLUMN baked timestamp with time zone;
ALTER TABLE modules ADD COLUMN recipe integer REFERENCES files (fileid);""")

    cursor.execute("""
CREATE TABLE print_style_recipes (
  print_style TEXT PRIMARY KEY,
  fileid INTEGER,
  type TEXT default 'web',
  FOREIGN KEY (fileid) REFERENCES files (fileid)
);""")

    cursor.execute("""
CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF (TG_OP = ''INSERT'' OR TG_OP = ''UPDATE'') AND
          NEW.revised >= ((SELECT revised FROM modules
              WHERE uuid = NEW.uuid ORDER BY revised DESC LIMIT 1)
              UNION ALL VALUES (NEW.revised) LIMIT 1) AND
          NEW.stateid = 1 THEN
      DELETE FROM latest_modules WHERE moduleid = NEW.moduleid OR uuid = NEW.uuid;
      INSERT into latest_modules (
                uuid, module_ident, portal_type, moduleid, version, name,
  		created, revised, abstractid, stateid, doctype, licenseid,
  		submitter,submitlog, parent, language,
		authors, maintainers, licensors, parentauthors, google_analytics,
                major_version, minor_version, print_style, baked, recipe)
  	VALUES (
         NEW.uuid, NEW.module_ident, NEW.portal_type, NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid,
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors, NEW.google_analytics,
         NEW.major_version, NEW.minor_version, NEW.print_style, NEW.baked, NEW.recipe);
  END IF;

  IF TG_OP = ''UPDATE'' THEN
      UPDATE latest_modules SET
        uuid=NEW.uuid,
        moduleid=NEW.moduleid,
        portal_type=NEW.portal_type,
        version=NEW.version,
        name=NEW.name,
        created=NEW.created,
        revised=NEW.revised,
        abstractid=NEW.abstractid,
        stateid=NEW.stateid,
        doctype=NEW.doctype,
        licenseid=NEW.licenseid,
	submitter=NEW.submitter,
	submitlog=NEW.submitlog,
        parent=NEW.parent,
	language=NEW.language,
	authors=NEW.authors,
	maintainers=NEW.maintainers,
	licensors=NEW.licensors,
	parentauthors=NEW.parentauthors,
	google_analytics=NEW.google_analytics,
        major_version=NEW.major_version,
        minor_version=NEW.minor_version,
        print_style=NEW.print_style,
        baked=NEW.baked,
        recipe=NEW.recipe
        WHERE module_ident=NEW.module_ident;
  END IF;

RETURN NEW;
END;

' LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION delete_from_latest() RETURNS trigger AS '
BEGIN
  DELETE FROM  latest_modules
    WHERE module_ident=OLD.module_ident;
  IF FOUND THEN
    INSERT into latest_modules (
         module_ident, portal_type, moduleid, uuid, version, name,
         created, revised, abstractid, licenseid, doctype, submitter,
         submitlog, stateid, parent, language, authors, maintainers,
         licensors, parentauthors, google_analytics, buylink,
         major_version, minor_version, print_style, baked, recipe)
    select
         module_ident, portal_type, moduleid, uuid, version, name,
         created, revised, abstractid, licenseid, doctype, submitter,
         submitlog, stateid, parent, language, authors, maintainers,
         licensors, parentauthors, google_analytics, buylink,
         major_version, minor_version, print_style, baked, recipe
    from current_modules where moduleid=OLD.moduleid;
  END IF;
  RETURN OLD;
END;
' LANGUAGE 'plpgsql';""")


def down(cursor):
    # Take it all back out

    cursor.execute("DROP TABLE print_style_recipes")
    cursor.execute("""
ALTER TABLE modules DROP COLUMN baked;
ALTER TABLE modules DROP COLUMN recipe;
ALTER TABLE latest_modules DROP COLUMN baked;
ALTER TABLE latest_modules DROP COLUMN recipe;
""")
    cursor.execute("""
CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF (TG_OP = ''INSERT'' OR TG_OP = ''UPDATE'') AND
          NEW.revised >= ((SELECT revised FROM modules
              WHERE uuid = NEW.uuid ORDER BY revised DESC LIMIT 1)
              UNION ALL VALUES (NEW.revised) LIMIT 1) AND
          NEW.stateid = 1 THEN
      DELETE FROM latest_modules WHERE moduleid = NEW.moduleid OR uuid = NEW.uuid;
      INSERT into latest_modules (
                uuid, module_ident, portal_type, moduleid, version, name,
  		created, revised, abstractid, stateid, doctype, licenseid,
  		submitter,submitlog, parent, language,
		authors, maintainers, licensors, parentauthors, google_analytics,
                major_version, minor_version, print_style)
  	VALUES (
         NEW.uuid, NEW.module_ident, NEW.portal_type, NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid,
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors, NEW.google_analytics,
         NEW.major_version, NEW.minor_version, NEW.print_style);
  END IF;

  IF TG_OP = ''UPDATE'' THEN
      UPDATE latest_modules SET
        uuid=NEW.uuid,
        moduleid=NEW.moduleid,
        portal_type=NEW.portal_type,
        version=NEW.version,
        name=NEW.name,
        created=NEW.created,
        revised=NEW.revised,
        abstractid=NEW.abstractid,
        stateid=NEW.stateid,
        doctype=NEW.doctype,
        licenseid=NEW.licenseid,
	submitter=NEW.submitter,
	submitlog=NEW.submitlog,
        parent=NEW.parent,
	language=NEW.language,
	authors=NEW.authors,
	maintainers=NEW.maintainers,
	licensors=NEW.licensors,
	parentauthors=NEW.parentauthors,
	google_analytics=NEW.google_analytics,
        major_version=NEW.major_version,
        minor_version=NEW.minor_version,
        print_style=NEW.print_style
        WHERE module_ident=NEW.module_ident;
  END IF;

RETURN NEW;
END;

' LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION delete_from_latest() RETURNS trigger AS '
BEGIN
  DELETE FROM  latest_modules
    WHERE module_ident=OLD.module_ident;
  IF FOUND THEN
    INSERT into latest_modules (
         module_ident, portal_type, moduleid, uuid, version, name,
         created, revised, abstractid, licenseid, doctype, submitter,
         submitlog, stateid, parent, language, authors, maintainers,
         licensors, parentauthors, google_analytics, buylink,
         major_version, minor_version, print_style)
    select
         module_ident, portal_type, moduleid, uuid, version, name,
         created, revised, abstractid, licenseid, doctype, submitter,
         submitlog, stateid, parent, language, authors, maintainers,
         licensors, parentauthors, google_analytics, buylink,
         major_version, minor_version, print_style
    from current_modules where moduleid=OLD.moduleid;
  END IF;
  RETURN OLD;
END;
' LANGUAGE 'plpgsql';""")

