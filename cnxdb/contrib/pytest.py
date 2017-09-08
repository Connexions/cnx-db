# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import psycopg2
import pytest

from .testing import (
    get_connection_string,
    get_connection_string_parts,
    get_database_table_names,
)


@pytest.fixture
def db_connection_string_parts():
    """Returns a connection string as parts (dict)"""
    return get_connection_string_parts()


@pytest.fixture
def db_connection_string():
    """Returns a connection string"""
    return get_connection_string()


def _db_wipe(db_connection_string):
    """Removes the schema from the database"""
    with psycopg2.connect(db_connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE; "
                           "CREATE SCHEMA public")
            cursor.execute("DROP SCHEMA IF EXISTS venv CASCADE")


@pytest.fixture
def db_wipe(db_connection_string, request, db_cursor_without_db_init):
    """Cleans up the database after a test run"""
    cursor = db_cursor_without_db_init
    tables = get_database_table_names(cursor)
    # Assume that if db_wipe is used it means we want to start fresh as well.
    if 'modules' in tables:
        _db_wipe(db_connection_string)

    def finalize():
        _db_wipe(db_connection_string)

    request.addfinalizer(finalize)


@pytest.fixture
def db_init(db_connection_string):
    """Initializes the database"""
    from cnxdb.init.main import init_db
    venv = os.getenv('AS_VENV_IMPORTABLE', 'true').lower() == 'true'
    init_db(db_connection_string, venv)


@pytest.fixture
def db_init_and_wipe(db_wipe, db_init):
    """Combination of the initialization and wiping procedures."""
    # The argument order, 'wipe' then 'init' is important, because
    #   db_wipe assumes you want to start with a clean database.
    pass


@pytest.fixture
def db_cursor_without_db_init(db_connection_string):
    """Creates a database connection and cursor"""
    conn = psycopg2.connect(db_connection_string)
    cursor = conn.cursor()
    yield cursor
    cursor.close()
    conn.close()


# Used to flag whether tests have been run before
_db_cursor__first_run = True


@pytest.fixture
def db_cursor(db_connection_string):
    """Creates a database connection and cursor"""
    global _db_cursor__first_run

    with psycopg2.connect(db_connection_string) as conn:
        with conn.cursor() as cursor:
            tables = get_database_table_names(cursor)
    # Use the database if it exists, otherwise initialize it
    if _db_cursor__first_run:
        _db_wipe(db_connection_string)
        db_init(db_connection_string)
        _db_cursor__first_run = False
    elif 'modules' not in tables:
        db_init(db_connection_string)

    # Create a new connection to activate the virtual environment
    # as it would normally be used.
    conn = psycopg2.connect(db_connection_string)
    cursor = conn.cursor()
    yield cursor
    cursor.close()
    conn.close()
