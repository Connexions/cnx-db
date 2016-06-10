# -*- coding: utf-8 -*-
import os
import sys

import psycopg2
import pytest

from .. import testing


def _translate_parts_to_args(parts):
    """Translates connection string parts to arguments"""
    return ['-h', parts['host'],
            '-p', parts['port'],
            '-d', parts['dbname'],
            '-U', parts['user'],
            ]


def test_init(connection_string_parts, db_wipe):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(connection_string_parts)
    return_code = main(args)

    assert return_code == 0

    def table_name_filter(table_name):
        return (not table_name.startswith('pg_') and
                not table_name.startswith('_pg_'))

    with psycopg2.connect(**connection_string_parts) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_name "
                           "FROM information_schema.tables "
                           "ORDER BY table_name")
            tables = [table_name for (table_name,) in cursor.fetchall()
                      if table_name_filter(table_name)]

    assert 'modules' in tables
    assert 'pending_documents' in tables


def test_init_called_twice(capsys, connection_string_parts, db_wipe):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(connection_string_parts)

    return_code = main(args)
    assert return_code == 0

    return_code = main(args)
    assert return_code == 3
    out, err = capsys.readouterr()
    assert 'already initialized' in err


@pytest.mark.skipif(not testing.is_db_local(),
                    reason="not testing against a local database")
def test_init_local(connection_string_parts, db_wipe):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(connection_string_parts)[4:]

    return_code = main(args)
    assert return_code == 0


def test_init_without_dbname(connection_string_parts, db_wipe):
    from cnxdb.cli.main import main
    args = ['init']
    args.extend(_translate_parts_to_args(connection_string_parts)[:4])
    args.extend(_translate_parts_to_args(connection_string_parts)[6:])

    with pytest.raises(SystemExit) as exc_info:
        return_code = main(args)
    assert exc_info.value.code == 2


def test_init_without_user(connection_string_parts, db_wipe):
    from cnxdb.cli.main import main
    args = ['init'] + _translate_parts_to_args(connection_string_parts)[:6]

    with pytest.raises(SystemExit) as exc_info:
        return_code = main(args)
    assert exc_info.value.code == 2

# TODO test venv ...
