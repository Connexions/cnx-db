from sqlalchemy import create_engine

from cnxdb import db
from cnxdb.connection import engine


__all__ = ('includeme',)


def _set_current_engine(config):
    """Enable ``cnxdb.connection.engine.get_current_engine``
    to use the same engine as pyramid.

    """
    engine.set_current_engine(config.registry.engine)


def _unset_current_engine(config):
    """Disable ``cnxdb.connection.engine.get_current_engine``.
    Careful, this will unset the engine regardless if you have set it or not.

    """
    engine.set_current_engine(None)


def includeme(config):
    """Used by pyramid to include this package."""
    s = config.registry.settings
    assert 'sqlalchemy.url' in s, "Missing 'sqlalchemy.url' setting"

    config.registry.engine = create_engine(s['sqlalchemy.url'])

    # Initialize the tables data
    db.tables.metadata.reflect(bind=config.registry.engine)
    config.registry.tables = db.tables

    config.add_directive('set_current_engine', _set_current_engine)
    config.add_directive('unset_current_engine', _unset_current_engine)
