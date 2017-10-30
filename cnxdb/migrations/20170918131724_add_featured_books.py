# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""\
ALTER TABLE featured_books RENAME TO featured_books_temp;""")
    cursor.execute("""\
CREATE TABLE featured_books (
    "uuid" UUID NOT NULL,
    "major_version" INT,
    "minor_version" INT,
    "tagid" TEXT,
    "fileid" INT
);""")
    cursor.execute("""\
INSERT INTO featured_books (uuid, major_version, minor_version, tagid, fileid)
    SELECT uuid, major_version, minor_version, tagid, mf.fileid FROM modules
    JOIN moduletags ON moduletags.module_ident = modules.module_ident
    LEFT JOIN module_files as mf ON mf.module_ident=modules.module_ident
    WHERE moduletags.tagid in (8,9) AND mf.filename='featured-cover.png';
""")


def down(cursor):
    cursor.execute("DROP TABLE featured_books")
    cursor.execute("""\
ALTER TABLE featured_books_temp RENAME TO featured_books;""")
