import pytest


from cnxdb.connection.util import libpq_dsn_to_url, url_to_libpq_dsn


class ConnInfo(object):

    # database type
    scheme = 'postgresql'

    # basic info
    dbname = 'deebee'
    user = 'uzer'
    password = 'pa$$word'
    host = 'example.com'
    port = 5432

    # extra connection args
    application_name = 'appz'

    @staticmethod
    def parse_dsn_to_dict(dsn):
        return {x: y for x, y in [z.split('=') for z in dsn.split()]}

    # These are properties to extract the info as either a libpq DSN or url.

    @property
    def libpq_dsn(self):
        return ("user={0.user} password={0.password} "
                "host={0.host} port={0.port} "
                "dbname={0.dbname} "
                "application_name={0.application_name}"
                .format(self))

    @property
    def libpq_dsn_as_dict(self):
        return self.__class__.parse_dsn_to_dict(self.libpq_dsn)

    @property
    def url(self):
        return ("{0.scheme}://{0.user}:{0.password}@"
                "{0.host}:{0.port}/{0.dbname}"
                "?application_name={0.application_name}"
                .format(self))


@pytest.fixture(scope='module')
def conn_info():
    return ConnInfo()


def test_libpq_dsn_to_url(conn_info):
    url = libpq_dsn_to_url(conn_info.libpq_dsn)
    assert url == conn_info.url


def test_url_to_libpq_dsn(conn_info):
    dsn = url_to_libpq_dsn(conn_info.url)
    assert ConnInfo.parse_dsn_to_dict(dsn) == conn_info.libpq_dsn_as_dict
