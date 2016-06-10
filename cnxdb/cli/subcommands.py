# -*- coding: utf-8 -*-
"""cnx-db subcommands"""
from __future__ import print_function
import sys
from functools import reduce

from .common import assign_db_args
from .discovery import register_subcommand


def _compile_connection_string_parts(args_namespace):
    """Given an ``argparse.Namespace``, translate this to a connection string
    parts (dict).

    """
    return {
        'dbname': args_namespace.dbname,
        'user': args_namespace.user,
        # 'password': None,
        'host': args_namespace.host,
        'port': args_namespace.port,
    }


def _translate_parts_to_string(connection_string_parts):
    """Translate the connection string parts ot a string"""
    return reduce(
        lambda x, y: ' '.join([x, y]),
        ['='.join(x) for x in connection_string_parts.items()
         if x[1] is not None])


@register_subcommand('init', *assign_db_args)
def init_cmd(args_namespace):
    """initialize the database"""
    connection_string_parts = _compile_connection_string_parts(args_namespace)
    connection_string = _translate_parts_to_string(connection_string_parts)
    from ..init import init_db, DBSchemaInitialized
    try:
        init_db(connection_string, False)
    except DBSchemaInitialized:
        print("Database is already initialized", file=sys.stderr)
        return 3
    return 0


@register_subcommand('venv', *assign_db_args)
def venv_cmd(args_namespace):
    """(re)initialize the venv within the database"""
    raise NotImplementedError()
