# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os

import psycopg2
import pytest
from sqlalchemy import create_engine

from .testing import (
    get_settings,
    get_database_table_names,
)


@pytest.fixture(scope='session')
def db_settings():
    """Returns database connection settings. These settings are provided
    in a similar format to that of `cnxdb.config.discover_settings`.

    """
    return get_settings()


@pytest.fixture(scope='session')
def db_engines(db_settings):
    """Returns a dictionary of database engine values. These are similar
    to the format used in `cnxdb.scripting.prepare`.

    """
    engines = {
        'common': create_engine(db_settings['db.common.url']),
        'super': create_engine(db_settings['db.super.url']),
    }
    return engines


@pytest.fixture
def db_env_vars(mocker, db_settings):
    """Sets the environment variables used by this project"""
    env_vars = os.environ.copy()
    env_vars.update({
        'DB_URL': db_settings['db.common.url'],
        'DB_SUPER_URL': db_settings['db.super.url'],
    })
    mocker.patch.dict(os.environ, env_vars)
    yield env_vars
    pass


def _db_wipe(db_engine):
    """Removes the schema from the database"""
    conn = db_engine.raw_connection()
    with conn.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE; "
                       "CREATE SCHEMA public")
        cursor.execute("DROP SCHEMA IF EXISTS venv CASCADE")
        cursor.connection.commit()
    conn.close()


@pytest.fixture
def db_wipe(db_engines, request, db_cursor_without_db_init):
    """Cleans up the database after a test run"""
    cursor = db_cursor_without_db_init
    tables = get_database_table_names(cursor)
    # Assume that if db_wipe is used it means we want to start fresh as well.
    if 'modules' in tables:
        _db_wipe(db_engines['super'])

    def finalize():
        _db_wipe(db_engines['super'])

    request.addfinalizer(finalize)


@pytest.fixture
def db_init(db_engines):
    """Initializes the database"""
    from cnxdb.init.main import init_db
    venv = os.getenv('AS_VENV_IMPORTABLE', 'true').lower() == 'true'
    init_db(db_engines['super'], venv)


@pytest.fixture
def db_init_and_wipe(db_wipe, db_init):
    """Combination of the initialization and wiping procedures."""
    # The argument order, 'wipe' then 'init' is important, because
    #   db_wipe assumes you want to start with a clean database.
    pass


@pytest.fixture
def db_cursor_without_db_init(db_engines):
    """Creates a database connection and cursor"""
    conn = db_engines['common'].raw_connection()
    cursor = conn.cursor()
    yield cursor
    cursor.close()
    conn.close()


# Used to flag whether tests have been run before
_db_cursor__first_run = True


def _maybe_init_database(db_engines):
    """Initializes the database if it isn't already initialized"""
    global _db_cursor__first_run

    conn = db_engines['super'].raw_connection()
    with conn.cursor() as cursor:
        tables = get_database_table_names(cursor)
    # Use the database if it exists, otherwise initialize it
    if _db_cursor__first_run:
        _db_wipe(db_engines['super'])
        db_init(db_engines)
        _db_cursor__first_run = False
    elif 'modules' not in tables:
        db_init(db_engines)
    conn.close()


@pytest.fixture
def db_cursor(db_engines):
    """Creates a database connection and cursor"""
    _maybe_init_database(db_engines)

    # Create a new connection to activate the virtual environment
    # as it would normally be used.
    conn = db_engines['common'].raw_connection()
    cursor = conn.cursor()
    yield cursor
    cursor.close()
    conn.close()


@pytest.fixture
def db_dict_cursor(db_engines, db_settings):
    """Creates a database connection and cursor that outputs a dict"""
    _maybe_init_database(db_engines)

    # Create a new connection to activate the virtual environment
    # as it would normally be used.
    # FIXME use db_engines instead of psycopg2
    conn = psycopg2.connect(db_settings['db.common.url'])
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    yield cursor
    cursor.close()
    conn.close()
