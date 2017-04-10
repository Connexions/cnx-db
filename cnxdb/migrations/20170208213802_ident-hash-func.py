# -*- coding: utf-8 -*-
import os

from contextlib import contextmanager


@contextmanager
def open_here(filepath, *args, **kwargs):
    """open a file relative to this files location"""

    here = os.path.abspath(os.path.dirname(__file__))
    fp = open(os.path.join(here, filepath), *args, **kwargs)
    yield fp
    fp.close()


@contextmanager
def super_user(cur):
    import psycopg2
    cur.execute('select CURRENT_USER')
    old_user = cur.fetchone()[0]
    old_dsn = cur.connection.dsn
    new_dsn = old_dsn.replace('user={}'.format(old_user), 'user=postgres')
    # FIXME test if old_user is superuser
    new_con = psycopg2.connect(new_dsn)
    yield new_con.cursor()
    new_con.commit()


def up(cursor):
    with open_here('../archive-sql/schema/functions.sql', 'rb') as f:
        with super_user(cursor) as cur:
            cur.execute(f.read())

    cursor.execute("""
CREATE INDEX modules_ident_hash on modules(ident_hash(uuid, major_version, minor_version));
CREATE INDEX modules_short_ident_hash on modules(short_ident_hash(uuid, major_version, minor_version));""")


def down(cursor):
    cursor.execute('drop function ident_hash(uuid, int, int) CASCADE')
    cursor.execute('drop function short_ident_hash(uuid, int, int) CASCADE')
