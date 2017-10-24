import os

from cnxdb.scripting import prepare


def test_prepare(mocker):
    db_url = 'sqlite:///:memory:'
    mocker.patch.dict(os.environ, {'DB_URL': db_url})
    env = prepare()

    assert sorted(env.keys()) == ['closer', 'engines', 'settings']
    assert sorted(env['engines'].keys()) == ['common', 'super']
    from sqlalchemy.engine import Engine
    assert isinstance(env['engines']['common'], Engine)

    # Use the engines to create a connection pool.
    for e in env['engines'].values():
        r = e.execute("select 1")
        r.fetchall()
        assert 'size: 1' in e.pool.status()

    # Close the environment, which disposes of all connections.
    env['closer']()
    for e in env['engines'].values():
        assert 'size: 0' in e.pool.status()

    expected_settings = {
        'db.common.url': db_url,
        'db.super.url': db_url,
    }
    assert env['settings'] == expected_settings
