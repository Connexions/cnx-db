CREATE OR REPLACE FUNCTION update_users_from_legacy ()
RETURNS TRIGGER
LANGUAGE PLPGSQL
AS '
BEGIN
UPDATE users
SET first_name = NEW.firstname,
    last_name = NEW.surname,
    full_name = NEW.fullname
WHERE username = NEW.personid;
RETURN NULL;
END;
';

CREATE TRIGGER update_users_from_legacy
  BEFORE UPDATE ON persons FOR EACH ROW
  EXECUTE PROCEDURE update_users_from_legacy();


CREATE OR REPLACE FUNCTION update_default_modules_stateid ()
RETURNS TRIGGER
LANGUAGE PLPGSQL
AS $$
BEGIN
  IF NEW.portal_type = 'Collection' THEN
    NEW.stateid = 5;
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER update_default_modules_stateid
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE update_default_modules_stateid();

CREATE OR REPLACE FUNCTION public.derived_book_ruleset()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
PERFORM * FROM module_files WHERE module_ident = NEW.module_ident
                                  AND filename = 'ruleset.css';
IF NOT FOUND THEN
    INSERT INTO module_files (module_ident, fileid, filename)
        SELECT NEW.module_ident, fileid, filename
            FROM module_files
            WHERE module_ident = NEW.parent AND filename = 'ruleset.css' ;
END IF;
RETURN NULL;
END;
$function$;

create trigger duplicate_ruleset_for_derived AFTER INSERT ON modules FOR EACH ROW WHEN (NEW.portal_type = 'Collection' AND NEW.parent is not NULL and NEW.version = '1.1' and NEW.major_version = 1 and NEW.minor_version = 1) execute procedure derived_book_ruleset();
