# -*- coding: utf-8 -*-
import os
import sys

import psycopg2
import pytest

from .. import testing


@pytest.mark.usefixtures('db_wipe')
def test_db_init(connection_string, db_cursor_without_db_init):
    from cnxdb.init.main import init_db
    init_db(connection_string)

    def table_name_filter(table_name):
        return (not table_name.startswith('pg_') and
                not table_name.startswith('_pg_'))

    cursor = db_cursor_without_db_init
    tables = testing.get_database_table_names(cursor, table_name_filter)

    assert 'modules' in tables
    assert 'pending_documents' in tables


@pytest.mark.usefixtures('db_wipe')
def test_db_init_called_twice(connection_string):
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
@pytest.mark.usefixtures('db_wipe')
def test_db_init_with_venv(connection_string):
    from cnxdb.init.main import init_db
    init_db(connection_string, True)

    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE FUNCTION pyprefix() RETURNS text LANGUAGE "
                           "plpythonu AS $$import sys;return sys.prefix$$")
            cursor.execute("SELECT pyprefix()")
            db_pyprefix = cursor.fetchone()[0]

    assert os.path.samefile(db_pyprefix, sys.prefix)
