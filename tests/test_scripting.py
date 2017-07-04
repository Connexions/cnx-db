import pytest

from cnxdb.connection import engine
from cnxdb.scripting import prepare


def test_prepare(mocker):
    settings = {'sqlalchemy.url': 'sqlite:///:memory:'}
    env = prepare(settings=settings)

    # look for the definition of cnxdb.connection.engine::_engine
    assert engine._engine._engine is not None  # None by default
    assert env['engine'] is engine.get_current_engine()

    with mocker.patch.object(env['engine'], 'dispose'):
        env['closer']()
        env['engine'].dispose.assert_called_with()
    assert engine._engine._engine is None


def test_prepare_missing_settings():
    with pytest.raises(RuntimeError) as exc_info:
        prepare()
    assert 'missing' in exc_info.value.args[0].lower()
