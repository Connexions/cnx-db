from collections import OrderedDict

import pretend
import psycopg2
import pytest
from pyramid import testing
from sqlalchemy.engine import Engine
from zope.interface.interfaces import ComponentLookupError

from cnxdb.contrib.pyramid import (
    _Tables,
    db_tables,
    get_db_engine,
    includeme,
    IEngine,
    ITables,
)


# Allow pretend's call_recorder to check by instance
# See also https://github.com/alex/pretend/issues/7
class _InstanceOf:
    """Allow pretend's call_recorder equality test
    to check for instance equality rather than value/identity.

    """

    def __init__(self, type_):
        self._type = type_

    def __eq__(self, other):
        return isinstance(other, self._type)

    def __ne__(self, other):
        return not isinstance(other, self._type)


def instance_of(type_):
    return _InstanceOf(type_)


@pytest.fixture
def pyramid_config(db_settings):
    """Preset the discoverable settings, where the pyramid
    application may want to define these itself, rather than
    have cnx-db discover them.

    """
    with testing.testConfig(settings=db_settings) as config:
        yield config


def test_includeme(db_settings, db_engines, monkeypatch):
    env = {'engines': OrderedDict(db_engines)}
    prepare = pretend.call_recorder(lambda s: env)
    monkeypatch.setattr('cnxdb.contrib.pyramid.prepare', prepare)

    registerUtility = pretend.call_recorder(lambda *a, **kw: None)
    registry = pretend.stub(
        registerUtility=registerUtility,
        settings=db_settings,
    )
    add_request_method = pretend.call_recorder(lambda *a, **kw: None)
    config = pretend.stub(
        add_request_method=add_request_method,
        registry=registry,
    )

    includeme(config)

    expected_calls = [pretend.call(instance_of(_Tables), ITables)]
    expected_calls.extend([
        pretend.call(engine, IEngine, name=name)
        for name, engine in env['engines'].items()
    ])
    expected_calls.append(pretend.call(instance_of(Engine), IEngine))
    assert registerUtility.calls == expected_calls

    assert add_request_method.calls == [
        pretend.call(get_db_engine),
        pretend.call(db_tables, reify=True),
    ]


def test_includeme_with_missing_settings(pyramid_config, mocker):
    pyramid_config.registry.settings = {}
    mocker.patch.dict('os.environ', {}, clear=True)

    with pytest.raises(RuntimeError) as exc_info:
        includeme(pyramid_config)
    expected_msg = 'must be defined'
    assert expected_msg in exc_info.value.args[0].lower()


def test_includeme_with_usage(db_settings, db_wipe):
    # Initialize a table to ensure table reflection is working.
    conn_str = db_settings['db.common.url']
    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE smurfs ("
                        "  name TEXT PRIMARY KEY,"
                        "  role TEXT,"
                        "  tastiness INTEGER);")
        conn.commit()

    # Call the target function
    request = testing.DummyRequest()
    with testing.testConfig(request=request, settings=db_settings) as config:
        includeme(config)

        # The request doesn't yet have the added methods and I'm not sure
        # how to make the test request have those, so we'll call them
        # directly instead. We aren't testing the framework's
        # add_request_method anyhow.

        # Check the engines definitions
        # ... looking for the unnamed util lookup
        assert str(get_db_engine(request).url) == db_settings['db.common.url']
        # ... looking for the named util lookup
        expected_url = db_settings['db.readonly.url']
        assert str(get_db_engine(request, 'readonly').url) == expected_url

        with pytest.raises(ComponentLookupError):
            get_db_engine(request, 'foobar')

        # Check the tables definition
        assert hasattr(db_tables(request), 'smurfs')
