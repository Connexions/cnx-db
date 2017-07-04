import pytest
from pyramid import testing

from cnxdb.contrib.pyramid import includeme
from cnxdb.connection.engine import get_current_engine


@pytest.fixture
def pyramid_config():
    settings = {'sqlalchemy.url': 'sqlite:///:memory:'}
    with testing.testConfig(settings=settings) as config:
        yield config
    # Incase of error, backup the get_engine func
    from cnxdb.connection import engine
    engine._engine._engine = None


def test_includeme_with_missing_settings(pyramid_config):
    pyramid_config.registry.settings = {}
    with pytest.raises(AssertionError) as exc_info:
        includeme(pyramid_config)
    assert 'missing' in exc_info.value.args[0].lower()


def test_includeme(pyramid_config):
    includeme(pyramid_config)

    assert hasattr(pyramid_config, 'set_current_engine')
    assert hasattr(pyramid_config, 'unset_current_engine')


def test_includeme_with_usage(pyramid_config):
    includeme(pyramid_config)

    pyramid_config.set_current_engine()

    from cnxdb.connection import engine as engine_module
    assert engine_module._engine._engine is not None

    engine = get_current_engine()
    assert engine is pyramid_config.registry.engine

    pyramid_config.unset_current_engine()

    with pytest.raises(RuntimeError) as exc_info:
        get_current_engine()
    assert 'not configured' in exc_info.value.args[0].lower()
