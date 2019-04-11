# -*- coding: utf-8 -*-
import os

import pytest


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
