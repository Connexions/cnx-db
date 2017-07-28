# -*- coding: utf-8 -*-
import functools
import os
import sys

import psycopg2


_DEFAULT_CONNECTION_SETTINGS = {
    'dbname': 'testing',
    'user': 'tester',
    'password': 'tester',
    'host': 'localhost',
    'port': '5432',
}


def parse_connection_string_to_parts(connection_string):
    """Parses a connection string to parts (dict of key values)."""
    return dict(map(lambda x: x.split('='), connection_string.split()))


def get_connection_string_parts():
    """Retrieves the connection string as dictionary key values."""
    parts = {}
    [parts.setdefault(k, v) for k, v in _DEFAULT_CONNECTION_SETTINGS.items()]
    connection_string = os.environ.get('TESTING_CONNECTION_STRING', None)
    if connection_string is not None:
        parts.update(parse_connection_string_to_parts(connection_string))
    return parts


def get_connection_string():
    """Retrieves the connection string from configuration."""
    return ' '.join(
        ['{}={}'.format(key, value)
         for key, value in get_connection_string_parts().items()])


def db_connection_factory(connection_string=None):
    if connection_string is None:
        connection_string = get_connection_string()

    def db_connect():
        return psycopg2.connect(connection_string)

    return db_connect


def db_connect(method):
    """Decorator for methods that need to use the database

    Example:
    @db_connect
    def setUp(self, cursor):
        cursor.execute(some_sql)
        # some other code
    """
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        connect = db_connection_factory()
        with connect() as db_connection:
            with db_connection.cursor() as cursor:
                return method(self, cursor, *args, **kwargs)
    return wrapped


def is_venv():
    """Returns a boolean telling whether the application is running
    within a virtualenv (aka venv).

    """
    return hasattr(sys, 'real_prefix')


def is_py3():
    """Returns a boolean value if running under python3.x"""
    return sys.version_info > (3,)


def is_db_local():
    """Returns a boolean telling whether the database is local or not."""
    return get_connection_string_parts()['host'] == 'localhost'


def _default_table_name_filter(table_name):
    return (not table_name.startswith('pg_') and
            not table_name.startswith('_pg_'))


def get_database_table_names(cursor,
                             table_name_filter=_default_table_name_filter):
    """Query for the names of all the tables in the database."""
    cursor.execute("SELECT table_name "
                   "FROM information_schema.tables "
                   "ORDER BY table_name")
    tables = [table_name for (table_name,) in cursor.fetchall()
              if table_name_filter(table_name)]
    return list(tables)


__all__ = (
    'db_connect',
    'db_connection_factory',
    'get_connection_string',
    'get_database_table_names',
    'is_db_local',
    'is_py3',
    'is_venv',
)
