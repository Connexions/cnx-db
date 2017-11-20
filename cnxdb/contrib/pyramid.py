# -*- coding: utf-8 -*-
"""\
When used in conjunction with the `Pyramid Web Framework
<http://docs.pylonsproject.org/projects/pyramid/en/latest/>`_
this module will setup the cnx-db library within the Pyramid application.

For usage examples, see :ref:`pyramid_usage`

"""
from sqlalchemy import MetaData

from cnxdb.scripting import prepare


__all__ = ('includeme', 'meta',)


meta = MetaData()


class _Tables(object):

    metadata = None

    def __init__(self, metadata=meta):
        self.metadata = metadata

    def __getattr__(self, name):
        return self.metadata.tables[name]


def includeme(config):
    """Used by pyramid to include this package.

    This sets up a dictionary of engines for use
    and the a ``tables`` object
    containing the defined database tables
    as sqlalchemy ``Table`` objects.
    They can be retrieved via the registry
    at ``registry.engines`` and ``registry.tables``.

    """
    env = prepare(config.registry.settings)
    engines = env['engines']
    # Set the engines on the registry
    config.registry.engines = engines
    # Initialize the tables on the registry
    config.registry.tables = _Tables()
    config.registry.tables.metadata.reflect(bind=engines['common'])
