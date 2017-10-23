# -*- coding: utf-8 -*-
import os
import sys

import pytest

from cnxdb.contrib import testing


@pytest.mark.usefixtures('db_wipe')
def test_db_init(db_engines, db_cursor_without_db_init):
    from cnxdb.init.main import init_db
    init_db(db_engines['super'])

    def table_name_filter(table_name):
        return (not table_name.startswith('pg_') and
                not table_name.startswith('_pg_'))

    cursor = db_cursor_without_db_init
    tables = testing.get_database_table_names(cursor, table_name_filter)

    assert 'modules' in tables
    assert 'pending_documents' in tables


@pytest.mark.usefixtures('db_wipe')
def test_db_init_called_twice(db_engines):
    from cnxdb.init.main import init_db
    init_db(db_engines['super'])

    from cnxdb.init.exceptions import DBSchemaInitialized
    try:
        init_db(db_engines['super'])
    except DBSchemaInitialized:
        pass
    else:
        assert False, "the initialization check failed"


@pytest.mark.skipif(not testing.is_venv(), reason="not within a venv")
@pytest.mark.usefixtures('db_wipe')
def test_db_init_with_venv(db_engines):
    from cnxdb.init.main import init_db
    init_db(db_engines['super'], True)

    conn = db_engines['common'].raw_connection()
    with conn.cursor() as cursor:
        cursor.execute("CREATE FUNCTION pyprefix() RETURNS text LANGUAGE "
                       "plpythonu AS $$import sys;return sys.prefix$$")
        cursor.execute("SELECT pyprefix()")
        db_pyprefix = cursor.fetchone()[0]
    conn.close()

    assert os.path.samefile(db_pyprefix, sys.prefix)
