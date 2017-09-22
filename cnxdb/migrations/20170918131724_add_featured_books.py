# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
CREATE TABLE featured_books (
    "uuid" UUID NOT NULL,
    "tagid" TEXT
);""")
    cursor.execute("""\
INSERT INTO featured_books (uuid, tagid)
    SELECT uuid, version FROM modules
        JOIN moduletags ON moduletags.module_ident = modules.module_ident
        WHERE moduletags.tagid=9;
""")

def down(cursor):
    cursor.execute("DROP TABLE featured_books")
