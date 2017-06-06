# -*- coding: utf-8 -*-
import os
import sys

import psycopg2
import pytest

from cnxdb.contrib import testing


def _translate_parts_to_args(parts):
    """Translates connection string parts to arguments"""
    return ['-h', parts['host'],
            '-p', parts['port'],
            '-d', parts['dbname'],
            '-U', parts['user'],
            ]


@pytest.mark.usefixtures('db_wipe')
def test_init(db_connection_string_parts, db_cursor_without_db_init):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(db_connection_string_parts)
    return_code = main(args)

    assert return_code == 0

    def table_name_filter(table_name):
        return (not table_name.startswith('pg_') and
                not table_name.startswith('_pg_'))

    cursor = db_cursor_without_db_init
    tables = testing.get_database_table_names(cursor, table_name_filter)

    assert 'modules' in tables
    assert 'pending_documents' in tables


@pytest.mark.usefixtures('db_wipe')
def test_init_called_twice(capsys, db_connection_string_parts):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(db_connection_string_parts)

    return_code = main(args)
    assert return_code == 0

    return_code = main(args)
    assert return_code == 3
    out, err = capsys.readouterr()
    assert 'already initialized' in err


@pytest.mark.skipif(not testing.is_db_local(),
                    reason="not testing against a local database")
@pytest.mark.usefixtures('db_wipe')
def test_init_local(db_connection_string_parts):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(db_connection_string_parts)[4:]

    return_code = main(args)
    assert return_code == 0


@pytest.mark.usefixtures('db_wipe')
def test_init_without_dbname(db_connection_string_parts):
    from cnxdb.cli.main import main
    args = ['init']
    args.extend(_translate_parts_to_args(db_connection_string_parts)[:4])
    args.extend(_translate_parts_to_args(db_connection_string_parts)[6:])

    with pytest.raises(SystemExit) as exc_info:
        main(args)
    assert exc_info.value.code == 2


@pytest.mark.usefixtures('db_wipe')
def test_init_without_user(db_connection_string_parts):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(db_connection_string_parts)[:6]

    with pytest.raises(SystemExit) as exc_info:
        main(args)
    assert exc_info.value.code == 2


def assert_venv_is_active(db_connection_string_parts):
    """Asserts the venv is active and working"""
    with psycopg2.connect(**db_connection_string_parts) as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE OR REPLACE FUNCTION pyprefix() "
                           "RETURNS text LANGUAGE "
                           "plpythonu AS $$import sys;return sys.prefix$$")
            cursor.execute("SELECT pyprefix()")
            db_pyprefix = cursor.fetchone()[0]

    assert os.path.samefile(db_pyprefix, sys.prefix)


@pytest.mark.skipif(not testing.is_venv(), reason="not within a venv")
@pytest.mark.usefixtures('db_init_and_wipe')
def test_venv(db_connection_string_parts):
    # Remove the venv schema before trying to initialize it.
    with psycopg2.connect(**db_connection_string_parts) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA venv CASCADE")

    from cnxdb.cli.main import main
    args = ['venv'] + _translate_parts_to_args(db_connection_string_parts)

    return_code = main(args)
    assert return_code == 0

    assert_venv_is_active(db_connection_string_parts)


@pytest.mark.skipif(not testing.is_venv(), reason="not within a venv")
@pytest.mark.usefixtures('db_init_and_wipe')
def test_venv_called_twice(db_connection_string_parts):
    # Note, the initialization already setup the venv,
    # so this really calles 3 times.
    from cnxdb.cli.main import main
    args = ['venv'] + _translate_parts_to_args(db_connection_string_parts)

    return_code = main(args)
    assert return_code == 0

    return_code = main(args)
    assert return_code == 0

    assert_venv_is_active(db_connection_string_parts)
