import os

import pytest

from cnxdb.config import discover_settings


def test_success(mocker):
    common_url = 'postgresql://common'
    super_url = 'postgresql://common'

    _patch = {
        'DB_URL': common_url,
        'SUPER_URL': super_url,
    }
    mocker.patch.dict(os.environ, _patch)

    settings = discover_settings()

    assert settings['db.common.url'] == common_url
    assert settings['db.super.url'] == super_url


def test_required(mocker):
    _patch = {}
    mocker.patch.dict(os.environ, _patch)

    with pytest.raises(RuntimeError) as exc_info:
        discover_settings()

    assert 'DB_URL' in exc_info.value.args[0]


def test_super_url_not_required(mocker):
    common_url = 'postgresql://common'

    _patch = {
        'DB_URL': common_url,
    }
    mocker.patch.dict(os.environ, _patch)

    settings = discover_settings()

    assert settings['db.common.url'] == common_url
    assert settings['db.super.url'] == common_url
