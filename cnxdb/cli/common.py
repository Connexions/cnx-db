# -*- coding: utf-8 -*-
import argparse


def add_db_args_to_parser(parser):
    """Adds the database arguments. These arguments are modeled after ``psql``'s
    arguments.

    """
    parser.add_argument('-h', '--host',
                        default='localhost',
                        help="database host name")
    parser.add_argument('-p', '--port',
                        default='5432',
                        help="database port")
    parser.add_argument('-d', '--dbname',
                        required=True,
                        help="database name")
    parser.add_argument('-U', '--user',
                        required=True,
                        help="database user")
    # parser.add_argument('-W', '--password', help="database password")


# Variable used to combined the parser callback and parser keyword arguments
# for use with the register_subcommand.
assign_db_args = (add_db_args_to_parser, {'add_help': False},)


__all__ = ('add_db_args_to_parser', 'assign_db_args',)
