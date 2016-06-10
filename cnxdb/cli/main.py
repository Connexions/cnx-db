# -*- coding: utf-8 -*-
"""cnx-db database control"""
from __future__ import print_function
import argparse
import sys
from functools import reduce


def create_common_db_args_parser():
    """Creates a ``argparse.ArgumentParser`` instance containing common
    database arguments. These arguments are modeled after ``psql``'s
    arguments.

    """
    parser = argparse.ArgumentParser("database arguments", add_help=False)
    parser.add_argument('-h', '--host',
                        default='localhost',
                        help="database host name")
    parser.add_argument('-p', '--port',
                        default='5432',
                        help="database port")
    parser.add_argument('-d', '--dbname',
                        help="database name")
    parser.add_argument('-U', '--user',
                        help="database user")
    # parser.add_argument('-W', '--password', help="database password")
    return parser


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


def venv_cmd(args_namespace):
    """(re)initialize the venv within the database"""
    raise NotImplementedError()


def create_main_parser():
    parser = argparse.ArgumentParser(__doc__)
    sub_parsers = parser.add_subparsers()
    db_args_parser = create_common_db_args_parser()
    init_parser = sub_parsers.add_parser('init', add_help=False,
                                         help=init_cmd.__doc__,
                                         parents=[db_args_parser])
    init_parser.set_defaults(cmd=init_cmd)
    venv_parser = sub_parsers.add_parser('venv', add_help=False,
                                         help=venv_cmd.__doc__,
                                         parents=[db_args_parser])
    venv_parser.set_defaults(cmd=venv_cmd)
    return parser


def main(argv=None):
    parser = create_main_parser()
    args = parser.parse_args(argv)

    return args.cmd(args)


__all__ = ('main',)
