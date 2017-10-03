# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
CREATE TABLE featured_books (
    "uuid" UUID NOT NULL,
    "major_version" INT,
    "minor_version" INT
);""")
    cursor.execute("""\
INSERT INTO featured_books (uuid, major_version, minor_version)
    SELECT uuid, major_version, minor_version FROM modules
        JOIN moduletags ON moduletags.module_ident = modules.module_ident
        WHERE moduletags.tagid=9;
""")

def down(cursor):
    cursor.execute("DROP TABLE featured_books")
