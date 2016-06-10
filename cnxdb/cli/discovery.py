# -*- coding: utf-8 -*-
import venusian


SUBCOMMAND_CATEGORY = 'subcommands'


def register_subcommand(command_name, parser_callback=None):
    """Register a function as a subcommand.
    For example::

        def assign_args(parser):
            parser.add_argument('argh', action='store_true')

        @register_subcommand('pirate', assign_args)
        def command(args):
            return args.argh and 'ARGH' or 'zZz'

    """
    def wrapper(wrapped):
        def callback(scanner, name, obj):
            # Create a parser for the subcommand with the given command_name.
            parser = scanner.sub_parsers.add_parser(command_name)
            # Call the parser's callback, which assigns arguments.
            if parser_callback is not None:
                parser_callback(parser)
            # Assign the command's execution function to the wrapped function.
            parser.set_defaults(cmd=wrapped)
        venusian.attach(wrapped, callback, category=SUBCOMMAND_CATEGORY)
        return wrapped
    return wrapper


def discover_subcommands(parser):
    """Discover registered subcommands. The side-effect of running this
    function is that it adds the subcommands to the given parser.

    """
    raise NotImplementedError()


__all__ = (
    'discover_subcommands',
    'register_subcommand',
    'SUBCOMMAND_CATEGORY',
)
