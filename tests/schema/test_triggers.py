# -*- coding: utf-8 -*-
import json
import os
import uuid

import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from cnxdb.contrib import testing


# Note, the triggers are only python 2.x compatible. It's assumed,
# at least for now, that in-database logic (i.e. triggers) are only
# run within a python2 environment. This product is to be setup in a
# production environment running within the database under python2 and
# optionally running within application code under either python2 or python3.


@pytest.mark.skipif(testing.is_py3(),
                    reason="triggers are only python2.x compat")
class TestPostPublication:

    channel = 'post_publication'

    def _make_one(self, cursor):
        """Insert the minimum necessary for creating a 'modules' entry."""
        uuid_ = str(uuid.uuid4())
        cursor.execute("INSERT INTO document_controls (uuid) VALUES (%s)",
                       (uuid_,))
        # The important bit here is `stateid = 5`
        cursor.execute("""\
        INSERT INTO modules
          (module_ident, portal_type, uuid, name, licenseid, doctype, stateid)
        VALUES
          (DEFAULT, 'Collection', %s, 'Physics: An Introduction', 11, '', 5)
        RETURNING
          module_ident,
          ident_hash(uuid, major_version, minor_version)""",
                       (uuid_,))
        module_ident, ident_hash = cursor.fetchone()
        cursor.connection.commit()
        return (module_ident, ident_hash)

    def test_payload(self, db_cursor):
        # Listen for notifications
        db_cursor.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        db_cursor.execute('LISTEN {}'.format(self.channel))
        db_cursor.connection.commit()

        module_ident, ident_hash = self._make_one(db_cursor)

        # Commit and poll to get the notifications
        db_cursor.connection.commit()
        db_cursor.connection.poll()
        notify = db_cursor.connection.notifies.pop(0)

        # Test the contents of the notification
        assert notify.channel == self.channel
        payload = json.loads(notify.payload)
        assert payload['module_ident'] == module_ident
        assert payload['ident_hash'] == ident_hash
        assert payload['timestamp']


def insert_test_data(conn_str, i):
    # We use pyscopg2 directly because the caller has entered a fork
    # via os.fork. If we were to use the connection pool here,
    # shared connections would be closed.
    import psycopg2
    conn = psycopg2.connect(conn_str)
    for minor_version in range(2, 12):
        with conn.cursor() as cursor:
            cursor.execute("""\
INSERT INTO MODULES (moduleid, version, name, \
    created, revised, \
    abstractid, licenseid, doctype, submitter, submitlog, stateid, \
    parent, language, authors, maintainers, licensors, parentauthors, \
    portal_type, uuid, major_version, minor_version) VALUES \
('col11170', '1.100', 'Solid State Physics and Devices', \
 '2010-01-10 05:50:16-08', NOW(), \
 1, 7, '', 'bijay_maniari', 'Modules added', 1, \
 NULL, 'en', '{bijay_maniari}', '{bijay_maniari}', '{bijay_maniari}', '{}', \
 'Collection', '94919e72-7573-4ed4-828e-673c1fe0cf9b', 100, %s)""",
                           (i * 10 + minor_version,))
    conn.commit()
    conn.close()


@pytest.mark.usefixtures('db_init_and_wipe')
def test_update_latest_race_condition(db_engines):
    conn = db_engines['super'].raw_connection()
    with conn.cursor() as db_cursor:
        db_cursor.execute("""\
INSERT INTO document_controls
    (uuid, licenseid)
VALUES (%s, 1)""", ('94919e72-7573-4ed4-828e-673c1fe0cf9b',))
        db_cursor.execute("""\
INSERT INTO abstracts
    (abstractid, abstract)
VALUES (1, 'test')""")
        db_cursor.execute("""\
ALTER TABLE modules DISABLE TRIGGER USER;
ALTER TABLE latest_modules DISABLE TRIGGER USER;
ALTER TABLE modules ENABLE TRIGGER update_latest_version;""")
        db_cursor.execute("""\
INSERT INTO latest_modules (moduleid, version, name, \
    created, revised, \
    abstractid, licenseid, doctype, submitter, submitlog, stateid, \
    parent, language, authors, maintainers, licensors, parentauthors, \
    portal_type, uuid, major_version, minor_version) VALUES \
('col11170', '1.100', 'Solid State Physics and Devices', \
'2010-01-10 05:50:16-08', '2017-08-15 12:18:30-07', \
 1, 7, '', 'bijay_maniari', 'Modules added', 1, \
 NULL, 'en', '{bijay_maniari}', '{bijay_maniari}', '{bijay_maniari}', '{}', \
 'Collection', '94919e72-7573-4ed4-828e-673c1fe0cf9b', 100, 1)""")
        db_cursor.connection.commit()
    conn_str = conn.dsn
    conn.close()

    pids = []
    for i in range(2):
        pid = os.fork()
        if pid:
            pids.append(pid)
        else:
            insert_test_data(conn_str, i)
            os._exit(0)

    for pid in pids:
        _, exit_code = os.waitpid(pid, 0)
        if exit_code != 0:
            assert False, 'update_latest trigger test failed'
