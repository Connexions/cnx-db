import os

__all__ = ('discover_settings')


def discover_settings():
    """Discover settings from environment variables

    :return: dictionary of settings
    :rtype: dict

    .. seealso::

       See also :ref:`configuration_chapter` for environment variables,
       defaults and required settings.

    """
    common_url = os.environ.get('DB_URL', None)
    super_url = os.environ.get('DB_SUPER_URL', common_url)

    if common_url is None:
        raise RuntimeError("'DB_URL' environment variable must be defined")

    settings = {
        'db.common.url': common_url,
        'db.super.url': super_url,
    }
    return settings
