import inspect

from sqlalchemy.engine.url import make_url, URL


__all__ = (
    'libpq_dsn_to_url',
    'url_to_libpq_dsn',
)


def _dsn_to_args(dsn):
    """Translates a libpq DSN to dict
    to be used with ``sqlalchemy.engine.url.URL``.

    """
    args = {'query': {}}
    url_args = inspect.getargspec(URL.__init__).args
    for item in dsn.split():
        name, value = item.split('=')
        if name == 'user':
            name = 'username'
        elif name == 'dbname':
            name = 'database'
        if name in url_args:
            args[name] = value
        else:
            args['query'][name] = value
    return args


def libpq_dsn_to_url(dsn):
    """Translate a libpq DSN to URL"""
    args = _dsn_to_args(dsn)
    url = URL('postgresql', **args)
    return str(url)


def url_to_libpq_dsn(url):
    """Translate a URL to libpq DSN"""
    url_obj = make_url(url)
    items = {}
    for name, value in url_obj.translate_connect_args().items():
        if name == 'username':
            name = 'user'
        elif name == 'database':
            name = 'dbname'
        items[name] = str(value)
    for k, v in url_obj.query.items():
        items.setdefault(k, v)
    return ' '.join(['='.join([k, v]) for k, v in items.items()])
