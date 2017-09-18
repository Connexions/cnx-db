# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("DROP FUNCTION IF EXISTS derived_book_ruleset() CASCADE")
    cursor.execute("""CREATE OR REPLACE FUNCTION derived_book_ruleset()
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
$function$ """)

    cursor.execute("""
CREATE TRIGGER duplicate_ruleset_for_derived AFTER INSERT ON modules
FOR EACH ROW
WHEN (NEW.portal_type = 'Collection'
      AND NEW.parent is not NULL
      AND NEW.version = '1.1'
      AND NEW.major_version = 1
      AND NEW.minor_version = 1) EXECUTE PROCEDURE derived_book_ruleset();
""")


def down(cursor):
    cursor.execute("DROP FUNCTION IF EXISTS derived_book_ruleset() CASCADE")
