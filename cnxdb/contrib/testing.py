# -*- coding: utf-8 -*-
"""\
These are functions that are useful in testing. They deal with testing
configuration discovery, setting defaults, and inspect the environment.

"""
import os
import sys


__all__ = (
    'get_database_table_names',
    'get_settings',
    'is_py3',
    'is_venv',
)


_DEFAULT_DB_URL = 'postgresql://tester:tester@localhost:5432/testing'


def get_settings():
    """Lookup database connection settings. This provides similar results
    to that of :func:`cnxdb.config.discover_settings`.

    :return: A dictionary of settings
    :rtype: dict

    """
    common_url = os.environ.get('DB_URL', _DEFAULT_DB_URL)
    super_url = os.environ.get('DB_SUPER_URL', common_url)

    settings = {
        'db.common.url': common_url,
        'db.super.url': super_url,
    }
    return settings


def is_venv():
    """Tells whether the application is running within a virtualenv
    (aka venv).

    :rtype: bool

    """
    return hasattr(sys, 'real_prefix')


def is_py3():
    """Returns a boolean value if running under python3.x

    :rtype: bool

    """
    return sys.version_info > (3,)


def _default_table_name_filter(table_name):
    return (not table_name.startswith('pg_') and
            not table_name.startswith('_pg_'))


def get_database_table_names(cursor,
                             table_name_filter=_default_table_name_filter):
    """Query for the names of all the tables in the database.

    :return: tables names
    :rtype: list

    """
    cursor.execute("SELECT table_name "
                   "FROM information_schema.tables "
                   "ORDER BY table_name")
    tables = [table_name for (table_name,) in cursor.fetchall()
              if table_name_filter(table_name)]
    return list(tables)
