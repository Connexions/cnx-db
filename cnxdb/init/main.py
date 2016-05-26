# -*- coding: utf-8 -*-
import os
import logging
import sys
import warnings

import psycopg2

from . import exceptions
from .manifest import get_schema


here = os.path.abspath(os.path.dirname(__file__))
SCHEMA_DIR = os.path.join(here, '..', 'schema')

logger = logging.getLogger('cnxdb')


SCHEMA_INITIALIZED_CHECK = """\
DO LANGUAGE plpgsql
$$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_class WHERE relname='modules') THEN
    RAISE EXCEPTION USING MESSAGE = 'Database schema is initialized.';
  END IF;
END;
$$;
"""


def _has_schema(cursor):
    """Checks for the existence of the database schema.
    Returns a boolean to indicate if the database schema exists or not.

    """
    try:
        cursor.execute(SCHEMA_INITIALIZED_CHECK)
    except psycopg2.InternalError as exc:
        if 'Database schema is initialized.' in exc.args[0]:
            return True
        else:  # pragma: no cover
            return False
    else:
        return False


def init_db(connection_string, as_venv_importable=False):
    """Initialize the database from the given ``connection_string``."""
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            if _has_schema(cursor):
                raise exceptions.DBSchemaInitialized()
            for schema_part in get_schema(SCHEMA_DIR):
                cursor.execute(schema_part)
    if as_venv_importable:
        init_venv(connection_string)


ACTIVATE_VENV_SQL_FUNCTION = """\
CREATE FUNCTION venv.activate_venv()
RETURNS void LANGUAGE plpythonu AS $_$
import sys
import os
import site
old_os_path = os.environ.get('PATH','')
os.environ['PATH'] = os.path.dirname(os.path.abspath('{activate_path}')) \
+ os.pathsep + old_os_path
base = os.path.dirname(os.path.dirname(os.path.abspath('{activate_path}')))
site_packages = os.path.join(base, 'lib', 'python%s' % sys.version[:3], \
'site-packages')
prev_sys_path = list(sys.path)
site.addsitedir(site_packages)
sys.real_prefix = sys.prefix
sys.prefix = base
# Move the added items to the front of the path:
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path
$_$"""


def _is_localhost_connection(db_connection):
    """Given a database connection, check this is a connection to localhost.

    """
    # If you are connecting to a database that is not localhost,
    # don't initalize with virtualenv
    db_dict = dict(p.split('=') for p in db_connection.dsn.split())
    return db_dict.get('host', 'localhost') != 'localhost'


def init_venv(connection_string):
    """Initialize a Python virtual environment for trigger importation."""
    # If virtualenv is active, use that for postgres
    if hasattr(sys, 'real_prefix'):  # attr is only present within a venv
        activate_path = os.path.join(os.path.realpath(sys.prefix),
                                     'bin/activate_this.py')
    else:  # pragma: no cover
        return

    with psycopg2.connect(connection_string) as db_connection:
        if _is_localhost_connection(db_connection):  # pragma: no cover
            warnings.warn("An attempt to use ``init_venv`` was made, "
                          "but not on the same host as the postgres service.")
            return
        with db_connection.cursor() as cursor:
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]

            cursor.execute("SELECT schema_name "
                           "FROM information_schema.schemata "
                           "WHERE schema_name = 'venv';")
            try:
                schema_exists = cursor.fetchone()[0]
            except TypeError:
                cursor.execute("CREATE SCHEMA venv")
                try:
                    cursor.execute("SAVEPOINT session_preload")
                    cursor.execute("ALTER DATABASE \"{}\" SET "
                                   "session_preload_libraries ="
                                   "'session_exec'".format(db_name))
                except psycopg2.ProgrammingError as e:  # pragma: no cover
                    if e.message.startswith(
                            'unrecognized configuration parameter'):

                        cursor.execute("ROLLBACK TO SAVEPOINT "
                                       "session_preload")
                        logger.warning("Postgresql < 9.4: make sure "
                                       "to set "
                                       "'local_preload_libraries "
                                       "= session_exec' in "
                                       "postgresql.conf and restart")
                    else:  # pragma: no cover
                        raise

                cursor.execute("ALTER DATABASE \"{}\" "
                               "SET session_exec.login_name = "
                               "'venv.activate_venv'"
                               .format(db_name))
                sql = ACTIVATE_VENV_SQL_FUNCTION.format(
                    activate_path=activate_path)
                cursor.execute(sql)


__all__ = (
    'init_db',
    'init_venv',
)
