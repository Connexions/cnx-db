import pytest

from cnxdb.connection.engine import get_engine


@pytest.fixture
def test_engine_marker():
    """Set the cnxdb.connection._engine with a marker object"""
    import cnxdb.connection.engine
    o = object()
    cnxdb.connection.engine._engine = o
    yield o
    cnxdb.connection.engine._engine = None


def test_get_engine_with_prepared_engine(test_engine_marker):
    engine = get_engine()
    assert engine is test_engine_marker


def test_get_engine_with_pyramid():
    engine = get_engine()
    # TODO implmt & test includeme func
