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


def up(cursor):

    with open_here('../archive-sql/schema/functions.sql', 'rb') as f:
        cursor.execute(f.read())

    cursor.execute("""
CREATE INDEX modules_ident_hash on modules(ident_hash(uuid, major_version, minor_version));
CREATE INDEX modules_short_ident_hash on modules(short_ident_hash(uuid, major_version, minor_version));""")


def down(cursor):
    # TODO rollback code

    cursor.execute('drop function ident_hash(uuid, int, int) CASCADE')
    cursor.execute('drop function short_ident_hash(uuid, int, int) CASCADE')
