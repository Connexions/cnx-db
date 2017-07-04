import pytest

from cnxdb.connection import engine


def test_get_engine_without_configuration():
    with pytest.raises(RuntimeError) as exc_info:
        engine.get_current_engine()
    assert 'not configured' in exc_info.value.args[0].lower()


def test_set_and_get_engine():
    o = object()
    engine.set_current_engine(o)
    assert engine.get_current_engine() is o
