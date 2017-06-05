# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
DO $$
BEGIN

IF to_regclass('public.moduletags_module_ident_idx') IS NULL THEN
  CREATE INDEX moduletags_module_ident_idx ON moduletags (module_ident);
END IF;

END$$;
""")


def down(cursor):
    cursor.execute('DROP INDEX moduletags_module_ident_idx')
