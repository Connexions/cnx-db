#!/var/cnx/venvs/archive/bin/python
"""
**Note**: strictly for development use only.

This script attempts to create a legacy user with SSHA password on a cnx
postgres db

1. You need to download this script onto a server that runs archive, but
    not on a non-development server, such as staging or prod

2. Use `./create_person.py user:passwd Group1 Group2` to create a user with
    the personid/username of 'user' and password 'passwd'

   2.1 If you are not using this on a cnx-deploy'd server, you can either
       specify the path to the archive config file using `CONFIG_INI` or the
       database connection string using `DB_URL` environment variables.

"""
import contextlib
import hashlib
import base64
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import os
import sys

import psycopg2.extras

DB_URL = os.getenv('DB_URL')
CONFIG_INI = os.getenv('CONFIG_INI', '/etc/cnx/archive/app.ini')
if not DB_URL:
    if not os.path.exists(CONFIG_INI):
        sys.stderr.write('DB_URL or CONFIG_INI must be set\n')
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(CONFIG_INI)
    DB_URL = config.get('app:main', 'db-connection-string')


@contextlib.contextmanager
def db_cursor(db_conn_str=DB_URL,
              cursor_factory=psycopg2.extras.RealDictCursor):
    with psycopg2.connect(db_conn_str) as db_conn:
        with db_conn.cursor(cursor_factory=cursor_factory) as cursor:
            yield cursor


def ssha_from_password(password):
    hash_type = b'{SSHA}'
    password_bytes = password.encode('utf-8')
    salt = os.urandom(6)
    digest = hashlib.sha1(password_bytes + salt).digest()
    result = hash_type + base64.b64encode(digest + salt)
    return result


def create_person(user_w_pass, groups):
    username, password = user_w_pass.split(':')
    print("Creating user: '{}' with pass: '{}'".format(
        username,
        password))

    groups_string = '{{{}}}'.format(','.join(groups))
    print("Groups: '{}'".format(groups_string))

    pass_ssha = ssha_from_password(password)

    sql_update = """
    UPDATE persons
    SET personid = %(user)s,
        passwd = %(pass_ssha)s,
        groups = %(groups)s
    WHERE personid = %(user)s"""

    sql_insert = """
    INSERT INTO persons (personid, passwd, groups)
    VALUES (%(user)s, %(pass_ssha)s, %(groups)s)
    """

    with db_cursor() as cursor:
        cursor.execute(sql_update, {'user': username,
                                    'pass_ssha': pass_ssha,
                                    'groups': groups_string})
        update_count = cursor.rowcount
        if update_count == 0:
            cursor.execute(sql_insert, {'user': username,
                                        'pass_ssha': pass_ssha,
                                        'groups': groups_string})
        else:
            print("username already exists - record updated")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write(
            'Usage: {name} <user:password> [groups ...]\n'
            .format(name=sys.argv[0]))
        sys.exit(1)

    create_person(sys.argv[1], sys.argv[2:])
