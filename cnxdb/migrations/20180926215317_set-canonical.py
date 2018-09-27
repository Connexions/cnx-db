# -*- coding: utf-8 -*-
from dbmigrator import deferred


@deferred
def up(cursor):

    cursor.execute("""
    UPDATE modules set canonical = default_canonical_book(uuid);
    """)


def down(cursor):
    cursor.execute("UPDATE modules set canonical = NULL")
