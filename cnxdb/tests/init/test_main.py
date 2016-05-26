# -*- coding: utf-8 -*-
import os
import sys

import psycopg2
import pytest

from .. import testing


def test_db_init(connection_string, db_wipe):
    from cnxdb.init.main import init_db
    init_db(connection_string)

    def table_name_filter(table_name):
        return (not table_name.startswith('pg_') and
                not table_name.startswith('_pg_'))

    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_name "
                           "FROM information_schema.tables "
                           "ORDER BY table_name")
            tables = [table_name for (table_name,) in cursor.fetchall()
                      if table_name_filter(table_name)]

    assert 'modules' in tables
    assert 'pending_documents' in tables


def test_db_init_called_twice(connection_string, db_wipe):
    from cnxdb.init.main import init_db
    init_db(connection_string)

    from cnxdb.init.exceptions import DBSchemaInitialized
    try:
        init_db(connection_string)
    except DBSchemaInitialized as exc:
        pass
    else:
        assert False, "the initialization check failed"


@pytest.mark.skipif(not testing.is_venv(), reason="not within a venv")
def test_db_init_with_venv(connection_string, db_wipe):
    from cnxdb.init.main import init_db
    init_db(connection_string, True)

    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE FUNCTION pypath() RETURNS text LANGUAGE "
                           "plpythonu AS $$import sys;return sys.prefix$$")
            cursor.execute("SELECT pypath()")
            db_pypath = cursor.fetchone()[0]

    assert os.path.samefile(db_pypath, sys.prefix)
