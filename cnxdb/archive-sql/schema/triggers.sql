CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF (TG_OP = ''INSERT'' OR TG_OP = ''UPDATE'') AND
          ARRAY [NEW.major_version, NEW.minor_version] >= (SELECT ARRAY [major_version, minor_version]
            FROM latest_modules WHERE uuid = NEW.uuid UNION ALL SELECT ARRAY[0, NULL] LIMIT 1) AND
          NEW.stateid = 1 THEN
      LOCK TABLE latest_modules IN SHARE ROW EXCLUSIVE MODE;
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

CREATE TRIGGER update_latest_version
  BEFORE INSERT OR UPDATE ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_latest();




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
' LANGUAGE 'plpgsql';

CREATE TRIGGER delete_from_latest_version
  AFTER DELETE ON modules FOR EACH ROW
  EXECUTE PROCEDURE delete_from_latest();




CREATE OR REPLACE FUNCTION post_publication() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('post_publication', '{"module_ident": '||NEW.module_ident||', "ident_hash": "'||ident_hash(NEW.uuid, NEW.major_version, NEW.minor_version)||'", "timestamp": "'||CURRENT_TIMESTAMP||'"}');
  RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER post_publication_trigger
  AFTER INSERT OR UPDATE ON modules FOR EACH ROW
  WHEN (NEW.stateid = 5)
  EXECUTE PROCEDURE post_publication();




CREATE OR REPLACE FUNCTION republish_module ()
  RETURNS trigger
AS $$
  from cnxarchive.database import republish_module_trigger
  return republish_module_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_moduleid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_moduleid_default_trigger
  return assign_moduleid_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_version_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_version_default_trigger
  return assign_version_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION assign_uuid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_document_controls_default_trigger
  return assign_document_controls_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION upsert_document_acl ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import upsert_document_acl_trigger
  return upsert_document_acl_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION upsert_user_shadow ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import upsert_users_from_legacy_publication_trigger
  return upsert_users_from_legacy_publication_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER act_10_module_uuid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_uuid_default();

CREATE TRIGGER act_20_module_acl_upsert
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE upsert_document_acl();

CREATE TRIGGER act_80_legacy_module_user_upsert
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE upsert_user_shadow();

CREATE TRIGGER module_moduleid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_moduleid_default();

CREATE TRIGGER module_published
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE republish_module();

CREATE TRIGGER module_version_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_version_default();




CREATE OR REPLACE FUNCTION optional_roles_user_insert ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import insert_users_for_optional_roles_trigger
  return insert_users_for_optional_roles_trigger(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER optional_roles_user_insert
  AFTER INSERT ON moduleoptionalroles FOR EACH ROW
  EXECUTE PROCEDURE optional_roles_user_insert();




CREATE FUNCTION update_md5() RETURNS "trigger"
    AS $$
BEGIN
  NEW.md5 = md5(NEW.file);
  RETURN NEW;
END;
$$
    LANGUAGE plpgsql;

CREATE TRIGGER update_file_md5
    BEFORE INSERT OR UPDATE OF file ON files
    FOR EACH ROW
    EXECUTE PROCEDURE update_md5();

CREATE OR REPLACE FUNCTION update_sha1()
    RETURNS TRIGGER
AS $$
    import hashlib

    TD['new']['sha1'] = hashlib.new('sha1', TD['new']['file']).hexdigest()
    return 'MODIFY'
$$ LANGUAGE plpythonu;

CREATE TRIGGER update_files_sha1
    BEFORE INSERT OR UPDATE OF file ON files
    FOR EACH ROW
    EXECUTE PROCEDURE update_sha1();

CREATE OR REPLACE FUNCTION add_module_file ()
  RETURNS trigger
AS $$
  from cnxarchive.database import add_module_file
  return add_module_file(plpy, TD)
$$ LANGUAGE plpythonu;

CREATE TRIGGER module_file_added
  AFTER INSERT ON module_files FOR EACH ROW
  EXECUTE PROCEDURE add_module_file();

CREATE OR REPLACE FUNCTION rebake()
 RETURNS trigger
 LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE modules SET stateid = 5 
    WHERE module_ident = NEW.module_ident and stateid not in (5, 6);
  RETURN NEW;
END;
$$;

CREATE TRIGGER ruleset_trigger
  AFTER INSERT OR UPDATE ON module_files FOR EACH ROW 
  WHEN (new.filename = 'ruleset.css'::text)
  EXECUTE PROCEDURE rebake();

-- default_recipe maintenace triggers

CREATE OR REPLACE FUNCTION update_default_recipes() RETURNS trigger AS
-- When a new recipe is inserted (or old one updated) make sure the
-- default_recipe table is appropriately updated
-- be careful to not allow changing a recipe that is the current recipe for
-- a baked book
$$
BEGIN
  IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND
          NEW.revised >= ((SELECT revised FROM print_style_recipes
              WHERE print_style = NEW.print_style ORDER BY revised DESC LIMIT 1)
              UNION ALL VALUES (NEW.revised) LIMIT 1) -- avoid compare to NULL
  THEN
      DELETE FROM default_print_style_recipes WHERE print_style = NEW.print_style;
      INSERT into default_print_style_recipes (
        print_style, title, tag, commit_id, fileid, recipe_type, revised)
  	VALUES (
        NEW.print_style, NEW.title, NEW.tag, NEW.commit_id, NEW.fileid, NEW.recipe_type, NEW.revised);
  END IF;

  IF TG_OP = 'UPDATE' THEN
    PERFORM 1 from modules where recipe = OLD.fileid;
    IF FOUND and NEW.fileid != OLD.fileid THEN
        RAISE WARNING 'Cannot change recipe file: recipe in use';
        RETURN NULL;
    END IF;
    UPDATE default_print_style_recipes SET
      tag=NEW.tag,
      title=NEW.title,
      fileid=NEW.fileid,
      recipe_type=NEW.recipe_type
      WHERE print_style=NEW.print_style and revised=NEW.revised;
  END IF;

RETURN NEW;
END;

$$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_default_recipes
  BEFORE INSERT OR UPDATE ON print_style_recipes FOR EACH ROW
  EXECUTE PROCEDURE update_default_recipes();


CREATE OR REPLACE FUNCTION delete_from_default_recipes() RETURNS trigger AS
-- Trigger function for handling deletes from print_style_recipes
-- If the recipe is in use (there is a book that has been cooked with that recipe),
-- do not allow delete.
-- If the recipe was the newest of its label, remove it from default_recipes, but
-- replace it with the next newest, if any
$$
BEGIN
  PERFORM 1 FROM modules where recipe = OLD.fileid;
  IF FOUND THEN
    RAISE WARNING 'Cannot delete: recipe in use';
    RETURN NULL;
  ELSE
    DELETE FROM  default_print_style_recipes
      WHERE print_style=OLD.print_style and tag=OLD.tag;
    IF FOUND THEN
      INSERT into default_print_style_recipes (
          print_style, title, tag, commit_id, fileid, recipe_type, revised)
      SELECT 
          print_style, title, tag, commit_id, fileid, recipe_type, revised
      from print_style_recipes where print_style=OLD.print_style
                                   and tag != OLD.tag
      order by revised desc LIMIT 1;
    END IF;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER delete_from_default_recipes
  BEFORE DELETE ON print_style_recipes FOR EACH ROW
  EXECUTE PROCEDURE delete_from_default_recipes();
