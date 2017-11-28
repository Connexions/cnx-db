# -*- coding: utf-8 -*-
import os
import sys

import pytest
from sqlalchemy.engine.reflection import Inspector

from cnxdb.contrib import testing


@pytest.mark.usefixtures('db_wipe')
def test_init(db_env_vars, db_engines):
    from cnxdb.cli.main import main
    args = ['init']
    return_code = main(args)

    assert return_code == 0

    inspector = Inspector.from_engine(db_engines['common'])
    tables = inspector.get_table_names()

    assert 'modules' in tables
    assert 'pending_documents' in tables


@pytest.mark.usefixtures('db_wipe')
def test_init_called_twice(capsys, db_env_vars):
    from cnxdb.cli.main import main
    args = ['init']

    return_code = main(args)
    assert return_code == 0

    return_code = main(args)
    assert return_code == 3
    out, err = capsys.readouterr()
    assert 'already initialized' in err


@pytest.mark.usefixtures('db_wipe')
def test_init_without_env_vars(capsys, mocker):
    mocker.patch.dict('os.environ', {}, clear=True)

    from cnxdb.cli.main import main
    args = ['init']

    return_code = main(args)
    assert return_code == 4

    expected_msg = ("'DB_URL' environment variable "
                    "OR the 'db.common.url' setting MUST be defined\n")
    assert expected_msg in capsys.readouterr()


def assert_venv_is_active(db_engines):
    """Asserts the venv is active and working"""
    # Dispose of all existing pooled connections.
    db_engines['super'].dispose()

    conn = db_engines['super'].raw_connection()
    with conn.cursor() as cursor:
        cursor.execute("CREATE OR REPLACE FUNCTION pyprefix() "
                       "RETURNS text LANGUAGE "
                       "plpythonu AS $$import sys;return sys.prefix$$")
        cursor.execute("SELECT pyprefix()")
        db_pyprefix = cursor.fetchone()[0]
    conn.close()

    assert os.path.samefile(db_pyprefix, sys.prefix)


@pytest.mark.skipif(not testing.is_venv_importable(),
                    reason=("settings indicate this environment is not "
                            "virtualenv (venv) importable."))
@pytest.mark.usefixtures('db_init_and_wipe')
def test_venv(db_env_vars, db_engines):
    # Remove the venv schema before trying to initialize it.
    conn = db_engines['super'].raw_connection()
    with conn.cursor() as cursor:
        cursor.execute("DROP SCHEMA venv CASCADE")
    conn.commit()
    conn.close()

    from cnxdb.cli.main import main
    args = ['venv']

    return_code = main(args)
    assert return_code == 0

    assert_venv_is_active(db_engines)


@pytest.mark.skipif(not testing.is_venv_importable(),
                    reason=("settings indicate this environment is not "
                            "virtualenv (venv) importable."))
@pytest.mark.usefixtures('db_init_and_wipe')
def test_venv_called_twice(db_env_vars, db_engines):
    # Note, the initialization already setup the venv,
    # so this really calles 3 times.
    from cnxdb.cli.main import main
    args = ['venv']

    return_code = main(args)
    assert return_code == 0

    return_code = main(args)
    assert return_code == 0

    assert_venv_is_active(db_engines)


@pytest.mark.usefixtures('db_wipe')
def test_venv_without_env_vars(capsys, mocker):
    mocker.patch.dict('os.environ', {}, clear=True)

    from cnxdb.cli.main import main
    args = ['venv']

    return_code = main(args)
    assert return_code == 4

    expected_msg = ("'DB_URL' environment variable "
                    "OR the 'db.common.url' setting MUST be defined\n")
    assert expected_msg in capsys.readouterr()
