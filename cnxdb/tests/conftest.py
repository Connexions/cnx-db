# -*- coding: utf-8 -*-
import pytest

from .testing import get_connection_string, get_connection_string_parts


@pytest.fixture
def connection_string_parts():
    """Returns a connection string as parts (dict)"""
    return get_connection_string_parts()


@pytest.fixture
def connection_string():
    """Returns a connection string"""
    return get_connection_string()


@pytest.fixture
def db_wipe(connection_string, request):
    """Cleans up the database after a test run"""
    import psycopg2

    def finalize():
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE; "
                               "CREATE SCHEMA public")
                cursor.execute("DROP SCHEMA IF EXISTS venv CASCADE")
    request.addfinalizer(finalize)


@pytest.fixture
def db_init(connection_string, request):
    """Initializes the database"""
    from cnxdb.init.main import init_db
    init_db(connection_string, True)
