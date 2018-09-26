# -*- coding: utf-8 -*-
from dbmigrator import deferred, super_user


@deferred
def up(cursor):

    with super_user() as super_cursor:
        super_cursor.execute("""
        ALTER TABLE modules DISABLE TRIGGER ALL;
        UPDATE modules set canonical = default_canonical_book(uuid);
        ALTER TABLE modules ENABLE TRIGGER ALL;
        ALTER TABLE latest_modules DISABLE TRIGGER ALL;
        UPDATE latest_modules set canonical = default_canonical_book(uuid);
        ALTER TABLE latest_modules ENABLE TRIGGER ALL;
        """)


def down(cursor):
    # TODO rollback code
    with super_user() as super_cursor:
        super_cursor.execute("""
        ALTER TABLE modules DISABLE TRIGGER ALL;
        UPDATE modules set canonical = NULL;
        ALTER TABLE modules ENABLE TRIGGER ALL;
        ALTER TABLE latest_modules DISABLE TRIGGER ALL;
        UPDATE latest_modules set canonical = NULL;
        ALTER TABLE latest_modules ENABLE TRIGGER ALL;
        """)
