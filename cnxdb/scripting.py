import os

from sqlalchemy import create_engine

from cnxdb.connection.engine import set_current_engine


def prepare(settings=None):
    """This function prepares an application for use with this codebase.
    This codebase depends on a ``sqlalchemy.engine.Engine`` for calling
    database functions. By preparing the application, one can call these
    functions without needing to explicitly pass in an engine or connection
    object. However, it is still a good idea to do so because it will give
    you control of the transaction.

    This will enable ``cnxdb.connection.engine.get_engine` to find
    a preconfigured engine instance.

    This function returns an environment dictionary containing
    the newly created ``engine`` and a ``closer`` function.

    """
    if settings is None:
        settings = {}

    db_url = 'DB_URL' in os.environ and os.environ['DB_URL'] or None
    settings.setdefault('sqlalchemy.url', db_url)
    if settings['sqlalchemy.url'] is None:
        raise RuntimeError("Missing 'sqlalchemy.url' settings. "
                           "You can define this using the DB_URL env var.")

    engine = create_engine(settings['sqlalchemy.url'])
    set_current_engine(engine)

    def closer():
        set_current_engine(None)
        engine.dispose()

    return {'engine': engine, 'closer': closer}
