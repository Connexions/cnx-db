# -*- coding: utf-8 -*-
"""This module contains testing fixtures.

The other testing fixtures are located in cnxdb.contrib.pytest.

The fixtures located in this module are specific to this
package's tests.

"""
import re

import psycopg2
import psycopg2.extras
import pytest

# XXX (2017-10-12) deps-on-cnx-archive: Depends on cnx-archive
from cnxarchive.config import TEST_DATA_SQL_FILE


# XXX (2017-10-13) deps-on-cnx-archive: Depends on cnx-archive
@pytest.fixture
def xxx_archive_data(db_init_and_wipe, db_cursor):
    # Load the database with example legacy data.
    with open(TEST_DATA_SQL_FILE, 'rb') as fb:
        db_cursor.execute(fb.read())
    db_cursor.connection.commit()


class FauxPlPy(object):

    def __init__(self, cursor):
        """Set up the cursor and plan store"""
        self._cursor = cursor
        self._plans = {}

    def prepare(self, stmt, param_types):
        return FauxPlPyPlan(self._cursor, stmt)

    def execute(self, plan, args, rows=None):
        return plan.execute(args, rows=rows)


class FauxPlPyPlan(object):

    def __init__(self, cursor, stmt):
        self._cursor = cursor
        self.stmt = re.sub(
            '\$([0-9]+)', lambda m: '%(param_{})s'.format(m.group(1)), stmt)

    def execute(self, args, rows=None):
        params = {}
        for i, value in enumerate(args):
            params['param_{}'.format(i + 1)] = value
        self._cursor.execute(self.stmt, params)
        self._cursor.connection.commit()
        try:
            results = self._cursor.fetchall()
            if rows is not None:
                results = results[:rows]
            return results
        except psycopg2.ProgrammingError as e:
            if str(e) != 'no results to fetch':
                raise


# FIXME (16-Oct-2017) Use the following class for plpy interactions
#       We'd like to be able to use the following because it uses the
#       PREPARE and EXECUTE statements, which technically should be similar
#       to what the actual plpy implementation does.
#       It's not currently used throughout, because plpy differs in how it
#       handles the uuid data type. The actual plpy.prepare seems to magically
#       convert a uuid to and from a string type in python.

# class FauxPlPy(object):
#     """Class to wrap access to DB in plpy style api"""

#     def __init__(self, cursor):
#         """Set up the cursor and plan store"""
#         self._cursor = cursor
#         self._plans = {}

#     def execute(self, query, args=None, rows=None):
#         """Execute a query or plan, with interpolated args"""

#         if query in self._plans:
#             args_fmt = self._plans[query]
#             stmt = 'EXECUTE "{}"({})'.format(query, args_fmt)
#             self._cursor.execute(stmt, args)
#         else:
#             self._cursor.execute(query, args)

#         if self._cursor.description is not None:
#             if rows is None:
#                 res = self._cursor.fetchall()
#             else:
#                 res = self._cursor.fetchmany(rows)
#         else:
#             res = None
#         return res

#     def prepare(self, query, args=None):
#         """"Prepare a plan, with optional placeholders for EXECUTE"""

#         plan = str(uuid.uuid4())
#         if args:
#             argstr = str(args).replace("'", '')
#             if len(args) < 2:
#                 argstr = argstr.replace(',', '')
#             stmt = 'PREPARE "{}"{} AS {}'.format(plan, argstr, query)
#             self._cursor.execute(stmt)
#         else:
#             self._cursor.execute('PREPARE "{}" AS {}'.format(plan, query))

#         self._plans[plan] = ', '.join(('%s',) * len(args))
#         return plan


@pytest.fixture
def faux_plpy(db_dict_cursor):
    """Allows the use of a plpythonu database object outside the scope of
    the database. This mimics the api of the plpy object.

    """
    plpy = FauxPlPy(db_dict_cursor)
    psycopg2.extras.register_default_json(globally=False, loads=lambda x: x)
    return plpy
