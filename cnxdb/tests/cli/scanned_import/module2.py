# -*- coding: utf-8 -*-
from cnxdb.cli.discovery import register_subcommand


def assign_args(parser):
    parser.add_argument('module2')


@register_subcommand('module2-command', assign_args)
def command(args):
    return args.module2
