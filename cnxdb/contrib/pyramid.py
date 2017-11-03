# -*- coding: utf-8 -*-
"""\
When used in conjunction with the `Pyramid Web Framework
<http://docs.pylonsproject.org/projects/pyramid/en/latest/>`_
this module will setup the cnx-db library within the Pyramid application.

"""
from cnxdb.scripting import prepare


__all__ = ('includeme',)


def includeme(config):
    """Used by pyramid to include this package.

    This sets up a dictionary of engines for use.
    They can be retrieved via the registry at ``registry.engines``.

    """
    env = prepare(config.registry.settings)
    config.registry.engines = env['engines']
