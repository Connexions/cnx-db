import os

__all__ = ('discover_settings')


def discover_settings(settings=None):
    """Discover settings from environment variables

    :param dict settings: An existing settings value
    :return: dictionary of settings
    :rtype: dict

    .. seealso::

       See also :ref:`configuration_chapter` for environment variables,
       defaults and required settings.

    """
    if settings is None:
        settings = {}

    common_url = os.environ.get('DB_URL', None)
    super_url = os.environ.get('DB_SUPER_URL', common_url)

    if common_url is None and settings.get('db.common.url') is None:
        raise RuntimeError("'DB_URL' environment variable "
                           "OR the 'db.common.url' setting MUST be defined")

    new_settings = {
        'db.common.url': common_url,
        'db.super.url': super_url,
    }

    for k, v in new_settings.items():
        settings.setdefault(k, v)
    return settings
