# -*- coding: utf-8 -*-
"""\
These are functions that are useful in testing. They deal with testing
configuration discovery, setting defaults, and inspect the environment.

"""
import os
import sys


__all__ = (
    'get_settings',
    'is_py3',
    'is_venv',
    'is_venv_importable',
)


_DEFAULT_DB_URL = 'postgresql://tester:tester@localhost:5432/testing'


def get_settings():
    """Lookup database connection settings. This provides similar results
    to that of :func:`cnxdb.config.discover_settings`.

    :return: A dictionary of settings
    :rtype: dict

    """
    common_url = os.environ.get('DB_URL', _DEFAULT_DB_URL)
    super_url = os.environ.get('DB_SUPER_URL', common_url)

    settings = {
        'db.common.url': common_url,
        'db.super.url': super_url,
    }
    return settings


def is_venv():
    """Tells whether the application is running within a virtualenv
    (aka venv).

    :rtype: bool

    """
    return hasattr(sys, 'real_prefix')


def is_venv_importable():
    """Determines whether the tests should be run with virtualenv
    (aka venv) database import features enabled.

    By default this will be true if the process is running within a venv.
    This can be overridden by setting the `AS_VENV_IMPORTABLE` environment
    variable to anything other than the string 'true'.

    :return: enable venv features
    :rtype: bool

    """
    x = os.environ.get('AS_VENV_IMPORTABLE', 'true') == 'true'
    return is_venv() and x


def is_py3():
    """Returns a boolean value if running under python3.x

    :rtype: bool

    """
    return sys.version_info > (3,)


def db_is_local():
    return '@localhost' in get_settings()['db.common.url']


if not is_venv():
    # BBB (22-Apr-2016) https://github.com/pypa/virtualenv/issues/355
    from site import getsitepackages
else:
    # Copy of `site.getsitepackages` from the standard library.
    PREFIXES = [sys.prefix, sys.exec_prefix]

    def getsitepackages(prefixes=None):
        """Returns a list containing all global site-packages directories.
        For each directory present in ``prefixes`` (or the global ``PREFIXES``),
        this function will find its `site-packages` subdirectory depending on the
        system environment, and will return a list of full paths.
        """
        sitepackages = []
        seen = set()

        if prefixes is None:
            prefixes = PREFIXES

        for prefix in prefixes:
            if not prefix or prefix in seen:
                continue
            seen.add(prefix)

            if os.sep == '/':
                sitepackages.append(os.path.join(prefix, "lib",  # noqa
                                            "python%d.%d" % sys.version_info[:2],
                                            "site-packages"))
            else:
                sitepackages.append(prefix)
                sitepackages.append(os.path.join(prefix, "lib", "site-packages"))
            if sys.platform == "darwin":
                # for framework builds *only* we add the standard Apple
                # locations.
                from sysconfig import get_config_var
                framework = get_config_var("PYTHONFRAMEWORK")
                if framework:
                    sitepackages.append(  # noqa
                            os.path.join("/Library", framework,
                                '%d.%d' % sys.version_info[:2], "site-packages"))
        return sitepackages
