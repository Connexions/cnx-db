import psycopg2
import pytest
from pyramid import testing

from cnxdb.contrib.pyramid import includeme


@pytest.fixture
def pyramid_config(db_settings):
    """Preset the discoverable settings, where the pyramid
    application may want to define these itself, rather than
    have cnx-db discover them.

    """
    with testing.testConfig(settings=db_settings) as config:
        yield config


def test_includeme(pyramid_config):
    includeme(pyramid_config)


def test_includeme_with_missing_settings(pyramid_config, mocker):
    pyramid_config.registry.settings = {}
    mocker.patch.dict('os.environ', {}, clear=True)

    with pytest.raises(RuntimeError) as exc_info:
        includeme(pyramid_config)
    expected_msg = 'must be defined'
    assert expected_msg in exc_info.value.args[0].lower()


def test_includeme_with_usage(pyramid_config, db_wipe):
    # Initialize a table to ensure table reflection is working.
    conn_str = pyramid_config.registry.settings['db.common.url']
    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE smurfs ("
                        "  name TEXT PRIMARY KEY,"
                        "  role TEXT,"
                        "  tastiness INTEGER);")
        conn.commit()

    # Call the target function
    includeme(pyramid_config)

    # Check the engines definition
    assert hasattr(pyramid_config.registry, 'engines')
    engines = pyramid_config.registry.engines
    assert sorted(engines.keys()) == ['common', 'readonly', 'super']
    # Check the tables definition
    assert hasattr(pyramid_config.registry.tables, 'smurfs')
