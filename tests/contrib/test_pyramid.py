import pytest
from pyramid import testing

from cnxdb.contrib.pyramid import includeme


@pytest.fixture
def pyramid_config():
    """Preset the discoverable settings, where the pyramid
    application may want to define these itself, rather than
    have cnx-db discover them.

    """
    url = 'sqlite:///:memory:'
    settings = {
        'db.common.url': url,
        'db.super.url': url,
    }
    with testing.testConfig(settings=settings) as config:
        yield config


def test_includeme(pyramid_config):
    includeme(pyramid_config)


def test_includeme_with_missing_settings(pyramid_config):
    pyramid_config.registry.settings = {}
    with pytest.raises(RuntimeError) as exc_info:
        includeme(pyramid_config)
    expected_msg = 'must be defined'
    assert expected_msg in exc_info.value.args[0].lower()


def test_includeme_with_usage(pyramid_config):
    includeme(pyramid_config)

    assert hasattr(pyramid_config.registry, 'engines')
    engines = pyramid_config.registry.engines
    assert sorted(engines.keys()) == ['common', 'super']
