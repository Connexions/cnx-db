# -*- coding: utf-8 -*-
import json
import uuid

from datetime import datetime
import hashlib
import os
import unittest

import pytest


import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from cnxdb.contrib import testing
from cnxdb.contrib import use_cases

from ..init.test_manifest import DATA_DIR as DATA_DIRECTORY


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


@pytest.mark.skipif(testing.is_py3(),
                    reason="triggers are only python2.x compat")
class TestModulePublishTriggerTestCase:
    """Tests for the postgresql triggers when a module is published
    """

    def resetTables(self, cursor):
        cursor.execute("DELETE FROM moduletags;")
        cursor.execute("DELETE FROM module_files;")
        cursor.execute("DELETE FROM collated_file_associations;")
        cursor.execute("DELETE FROM files;")
        cursor.execute("DELETE FROM modulekeywords;")
        cursor.execute("DELETE FROM latest_modules;")
        cursor.execute("DELETE FROM modules;")
        cursor.execute("DELETE FROM trees;")
        cursor.execute("DELETE FROM document_acl;")
        cursor.execute("DELETE FROM document_controls;")
        cursor.execute("DELETE FROM abstracts;")
        cursor.execute('ALTER TABLE modules ENABLE TRIGGER module_published;')
        # use_cases.empty_all_tables(cursor)

    @testing.db_connect
    def test_get_current_module_ident(self, cursor):
        self.resetTables(cursor)
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from cnxdb.triggers import get_current_module_ident

        use_cases.add_module(cursor, version='1.1', minor_version=1,
                             revised='2013-10-03 21:14:11.000000+02')
        # module_ident_1 = cursor.fetchone()[0]
        use_cases.add_module(cursor, version='1.2', minor_version=2,
                             returning='module_ident')
        module_ident_2 = cursor.fetchone()[0]

        cursor.connection.commit()
        module_ident = get_current_module_ident('m1', testing.fake_plpy)

        assert(module_ident == module_ident_2)

    @testing.db_connect
    def test_next_version(self, cursor):
        self.resetTables(cursor)
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from cnxdb.triggers import next_version

        use_cases.add_module(cursor, version='1.2', minor_version=2,
                             returning='module_ident')
        module_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        assert(next_version(module_ident, testing.fake_plpy) == 3)

    @testing.db_connect
    def test_get_collections(self, cursor):
        self.resetTables(cursor)
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from cnxdb.triggers import get_collections

        use_cases.add_collection(cursor, version='1.9', minor_version=9,
                                 moduleid='col2', returning='module_ident')
        collection_ident = cursor.fetchone()[0]

        use_cases.add_collection(cursor, version='1.8', minor_version=8,
                                 returning='module_ident')
        collection2_ident = cursor.fetchone()[0]

        use_cases.add_module(cursor, version='1.2', minor_version=2,
                             returning='module_ident')
        module_ident = cursor.fetchone()[0]

        use_cases.add_tree(cursor, documentid=collection_ident,
                           returning='nodeid')
        nodeid_1 = cursor.fetchone()[0]
        use_cases.add_tree(cursor, parent_id=nodeid_1, documentid=module_ident,
                           childorder=1)

        use_cases.add_tree(cursor, documentid=collection2_ident,
                           returning='nodeid')
        nodeid_2 = cursor.fetchone()[0]
        use_cases.add_tree(cursor, parent_id=nodeid_2, documentid=module_ident,
                           childorder=1)

        cursor.connection.commit()

        # The collection will not be in latest modules yet because they need to
        # be processed by the post publication worker.
        assert(list(get_collections(module_ident, testing.fake_plpy)) == [])

        # The post-publication worker will change the module state to "current"
        # (1).
        cursor.execute(
            "UPDATE modules SET stateid = 1 WHERE module_ident IN %s",
            ((collection_ident, collection2_ident),))

        cursor.connection.commit()

        # Now the collection should be in latest modules.
        assert(list(get_collections(module_ident, testing.fake_plpy)) ==
               [collection_ident, collection2_ident])

    @testing.db_connect
    def test_rebuild_collection_tree(self, cursor):
        self.resetTables(cursor)
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from cnxdb.triggers import rebuild_collection_tree

        use_cases.add_collection(cursor, version='1.9', minor_version=9,
                                 returning='module_ident')
        collection_ident = cursor.fetchone()[0]

        use_cases.add_module(cursor, version='1.2', minor_version=2,
                             returning='module_ident')
        module_ident = cursor.fetchone()[0]

        use_cases.add_module(cursor, moduleid='m2', name='Name of m2',
                             returning='module_ident')
        module2_ident = cursor.fetchone()[0]

        use_cases.add_tree(cursor, documentid=collection_ident,
                           returning='nodeid')
        nodeid = cursor.fetchone()[0]

        use_cases.add_tree(cursor, parent_id=nodeid, documentid=module_ident,
                           childorder=1)

        use_cases.add_tree(cursor, parent_id=nodeid, documentid=module2_ident,
                           childorder=1)

        use_cases.add_collection(cursor, version='1.9', minor_version=10,
                                 returning='module_ident')
        new_collection_ident = cursor.fetchone()[0]

        use_cases.add_module(cursor, version='1.2', minor_version=3,
                             returning='module_ident')
        new_module_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        new_document_id_map = {
            collection_ident: new_collection_ident,
            module_ident: new_module_ident}

        rebuild_collection_tree(collection_ident, new_document_id_map,
                                testing.fake_plpy)

        cursor.execute('''\
        WITH RECURSIVE t(node, parent, document, path) AS (
            SELECT tr.nodeid, tr.parent_id, tr.documentid, ARRAY[tr.nodeid]
            FROM trees tr WHERE tr.documentid = %s
        UNION ALL
            SELECT c.nodeid, c.parent_id, c.documentid, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON (t.node = c.parent_id)
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT document FROM t
        ''', [new_collection_ident])
        assert(cursor.fetchall() ==
               [(new_collection_ident,), (new_module_ident,),
                (module2_ident,)])

    @testing.db_connect
    def test_republish_collection(self, cursor):
        self.resetTables(cursor)
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')

        from cnxdb.triggers import republish_collection

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        cursor.execute("""INSERT INTO abstracts (abstractid) VALUES (1)""")

        use_cases.add_collection(cursor, version='7.10', major_version=7,
                                 minor_version=10,
                                 uuid='3a5344bd-410d-4553-a951-87bccd996822',
                                 created='2013-07-31 14:00:00.000000-05',
                                 revised='2013-10-03 21:59:12.000000-07',
                                 abstractid=1, doctype='doctype',
                                 submitter='submitter', submitlog='submitlog',
                                 authors=['authors'], licensors=['licensors'],
                                 maintainers=['maintainers'],
                                 parentauthors=['parentauthors'],
                                 google_analytics='analytics code',
                                 buylink='buylink',
                                 returning='module_ident')
        collection_ident = cursor.fetchone()[0]
        cursor.connection.commit()

        republished_submitter = "republished_submitter"
        republished_submitlog = "republished_submitlog"

        new_ident = republish_collection(republished_submitter,
                                         republished_submitlog, 3,
                                         collection_ident, testing.fake_plpy)

        cursor.execute('''SELECT
            portal_type, moduleid, uuid, version, name, created, abstractid,
            licenseid, doctype, submitter, submitlog, stateid, parent,
            language, authors, maintainers, licensors, parentauthors,
            google_analytics, buylink, major_version, minor_version
                 FROM modules WHERE module_ident = %s''', [new_ident])
        data = cursor.fetchone()
        assert(data ==
               ('Collection', 'col1', '3a5344bd-410d-4553-a951-87bccd996822',
                '7.10', 'Name of col1',
                datetime(2013, 7, 31, 14, 0,
                         tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=-300,
                                                                name=None)),
                1, 11, 'doctype', republished_submitter, republished_submitlog,
                5, None, 'en', ['authors'], ['maintainers'], ['licensors'],
                ['parentauthors'], 'analytics code', 'buylink', 7, 3))

    @testing.db_connect
    def test_republish_collection_w_keywords(self, cursor):
        # Ensure association of the new collection with existing keywords.
        self.resetTables(cursor)
        cursor.execute("ALTER TABLE modules DISABLE TRIGGER module_published")
        cursor.connection.commit()

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")

        use_cases.add_collection(cursor, version='1.10', minor_version=10,
                                 uuid='3a5344bd-410d-4553-a951-87bccd996822',
                                 returning='module_ident')
        collection_ident = cursor.fetchone()[0]
        keywords = ['smoo', 'dude', 'gnarly', 'felice']
        values_expr = ", ".join("('{}')".format(v) for v in keywords)
        cursor.execute("""INSERT INTO keywords (word)
        VALUES {}
        RETURNING keywordid;""".format(values_expr))
        keywordids = [x[0] for x in cursor.fetchall()]
        values_expr = ", ".join(["({}, '{}')".format(collection_ident, id)
                                 for id in keywordids])
        cursor.execute("""INSERT INTO modulekeywords (module_ident, keywordid)
        VALUES {};""".format(values_expr))
        cursor.connection.commit()

        from cnxdb.triggers import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT",
                                         3, collection_ident,
                                         testing.fake_plpy)

        cursor.execute("""\
        SELECT word
        FROM modulekeywords NATURAL JOIN keywords
        WHERE module_ident = %s""", (new_ident,))

        inserted_keywords = [x[0] for x in cursor.fetchall()]
        assert(sorted(inserted_keywords) == sorted(keywords))

    @testing.db_connect
    def test_republish_collection_w_files(self, cursor):
        # Ensure association of the new collection with existing files.
        self.resetTables(cursor)
        cursor.execute("ALTER TABLE modules DISABLE TRIGGER module_published")
        cursor.connection.commit()

        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('3a5344bd-410d-4553-a951-87bccd996822'::uuid)""")
        use_cases.add_collection(cursor, version='1.10', minor_version=10,
                                 uuid='3a5344bd-410d-4553-a951-87bccd996822',
                                 returning='module_ident')
        collection_ident = cursor.fetchone()[0]

        filepath = os.path.join(DATA_DIRECTORY, 'ruleset.css')
        with open(filepath, 'r') as f:
            cursor.execute('''\
            INSERT INTO files (file, media_type) VALUES
            (%s, 'text/css') RETURNING fileid''', [memoryview(f.read())])
            fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename) VALUES
        (%s, %s, 'ruleset.css');''', [collection_ident, fileid])

        cursor.connection.commit()

        from cnxdb.triggers import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT",
                                         3, collection_ident,
                                         testing.fake_plpy)

        cursor.execute("""\
        SELECT fileid, filename
        FROM module_files
        WHERE module_ident = %s""", (new_ident,))

        inserted_files = cursor.fetchall()
        assert(sorted(inserted_files) == sorted([(fileid, 'ruleset.css')]))

    @testing.db_connect
    def test_republish_collection_w_subjects(self, cursor):
        # Ensure association of the new collection with existing subjects/tags.
        self.resetTables(cursor)
        cursor.execute("ALTER TABLE modules DISABLE TRIGGER module_published")
        cursor.connection.commit()

        use_cases.add_collection(cursor, returning='module_ident')
        collection_ident = cursor.fetchone()[0]

        subjects = [(2, 'Business',), (3, 'Humanities',)]

        values_expr = ", ".join(["({}, '{}')".format(collection_ident, id)
                                 for id, name in subjects])
        cursor.execute("""INSERT INTO moduletags (module_ident, tagid)
        VALUES {};""".format(values_expr))
        cursor.connection.commit()

        from cnxdb.triggers import republish_collection
        new_ident = republish_collection("DEFAULT", "DEFAULT", 3,
                                         collection_ident, testing.fake_plpy)

        cursor.execute("""\
        SELECT tag
        FROM moduletags NATURAL JOIN tags
        WHERE module_ident = %s""", (new_ident,))

        inserted_subjects = [x[0] for x in cursor.fetchall()]
        assert(sorted(inserted_subjects) ==
               sorted([name for id, name in subjects]))

    def test_set_version(self):
        from cnxdb.triggers import set_version

        # set_version for modules
        td = {
            'new': {
                'portal_type': 'Module',
                'major_version': 1,
                'minor_version': None,
                'version': '1.13',
            }
        }
        modified = set_version(td['new']['portal_type'],
                               td['new']['version'],
                               td)
        assert(modified == 'MODIFY')
        assert(td['new'] == {
            'portal_type': 'Module',
            'major_version': 13,
            'minor_version': None,
            'version': '1.13', })

        # set_version for collections
        td = {
            'new': {
                'portal_type': 'Collection',
                'major_version': 1,
                'minor_version': None,
                'version': '1.100',
            }
        }
        modified = set_version(td['new']['portal_type'],
                               td['new']['version'],
                               td)
        assert(modified == 'MODIFY')
        assert(td['new'] == {
            'portal_type': 'Collection',
            'major_version': 100,
            'minor_version': 1,
            'version': '1.100', })

    @testing.plpy_connect
    def test_get_module_uuid(self, plpy):
        from cnxdb.triggers import get_module_uuid

        plpy.execute("""INSERT INTO modules
                        (name, licenseid, doctype, moduleid, uuid)
                        VALUES ('name of module', 11, '', 'm41237',
                                '91cb5f28-2b8a-4324-9373-dac1d617bc24');""")

        mod_uuid = get_module_uuid(plpy, 'm41237')
        assert(mod_uuid == '91cb5f28-2b8a-4324-9373-dac1d617bc24')

    @testing.plpy_connect
    def test_get_subcols(self, plpy):
        self.resetTables(plpy)
        from cnxdb.triggers import get_subcols

        module_ident = use_cases.add_module_plpy(plpy)

        expected_results = []
        for i in range(3):
            collection_ident = use_cases.add_module_plpy(
                plpy, portal_type='SubCollection')
            expected_results.append(collection_ident)
            nodeid = plpy.execute("""
            INSERT INTO trees
                (parent_id, documentid, title, childorder, latest, is_collated)
            VALUES
                (NULL, {}, 'title', 0, NULL, False) RETURNING nodeid;
            """.format(collection_ident))[0][0]
            plpy.execute("""
            INSERT INTO trees
                (parent_id, documentid, title, childorder, latest, is_collated)
            VALUES
                ({}, {}, 'title', 0, NULL, False);
            """.format(nodeid, module_ident))

        subcols = tuple(get_subcols(module_ident, plpy))
        assert(subcols == tuple(expected_results))

    @testing.db_connect
    def test_insert_new_module(self, cursor):
        self.resetTables(cursor)
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert abstract
        use_cases.add_abstract(cursor, abstractid=20802, abstract='')

        # Insert a new module
        cursor.execute('''\
        INSERT INTO modules (
            moduleid, portal_type, version, name, created,
            revised, authors, maintainers,
            licensors,  abstractid, stateid, licenseid, doctype,
            submitter, submitlog, language, parent)
        VALUES (
            'm47638', 'Module', '1.13', 'test convert', '2013-12-09T16:57:29Z',
            '2013-12-09T17:14:08Z', ARRAY ['user1'], ARRAY ['user1'],
            ARRAY ['user1'],  20802, null, 7, '',
            'user1', 'Created module', 'en', null
        )''')

        # module_republished trigger should not insert anything
        cursor.execute('SELECT COUNT(*) FROM modules')
        n_modules = cursor.fetchone()[0]
        assert(n_modules == old_n_modules + 1)

        # Check that major and minor version are set correctly
        cursor.execute("""SELECT major_version, minor_version
                          FROM modules ORDER BY module_ident DESC""")
        major, minor = cursor.fetchone()
        assert(major == 13)
        assert(minor is None)

    @unittest.skip("Not implemented")
    @testing.db_connect
    def test_module(self, cursor):
        use_cases.empty_all_tables(cursor)
        file_data = os.path.join(DATA_DIRECTORY, 'data.sql')
        use_cases.add_all_data(cursor, file_data)

        # Create a fake collated tree for College Physics
        # which contains the module that is going to have a new version
        cursor.execute("""\
INSERT INTO trees (parent_id, documentid, is_collated)
    VALUES (NULL, 1, TRUE) RETURNING nodeid""")
        nodeid = cursor.fetchone()[0]
        cursor.execute("""\
INSERT INTO trees (parent_id, documentid, is_collated)
    VALUES (%s, 2, TRUE)""", (nodeid,))
        cursor.connection.commit()

        # update other collection to have subcollection uuids
        cursor.execute(
            "SELECT subcol_uuids('e79ffde3-7fb4-4af3-9ec8-df648b391597','7.1')"
        )

        cursor.execute('SELECT nodeid FROM trees WHERE documentid = 18')
        old_nodeid = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM modules')
        old_n_modules = cursor.fetchone()[0]

        # Insert a new version of an existing module
        cursor.execute('''\
        INSERT INTO modules
        (moduleid, portal_type, version, name, created, revised,
         authors, maintainers, licensors, abstractid, stateid, licenseid,
         doctype, submitter, submitlog, language, parent)
        VALUES ('m42119', 'Module', '1.4',
        'Introduction to Science and the Realm of Physics, ...',
        '2013-07-31 14:07:20.590652-05' , '2013-07-31 15:07:20.590652-05',
        NULL, NULL, NULL, 1, NULL, 11, '', 'reedstrm',
        'I did not change something', 'en', NULL) RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # After the new module is inserted, there should be a new module and
        # two new collections, and two new subcollections
        cursor.execute('SELECT COUNT(*) FROM modules')
        assert(cursor.fetchone()[0] == old_n_modules + 5)

        # Test that the module inserted has the right major and minor versions
        cursor.execute('''SELECT major_version, minor_version, uuid
                          FROM modules
                          WHERE portal_type = 'Module'
                          ORDER BY module_ident DESC''')
        major, minor, uuid = cursor.fetchone()
        assert(major == 4)
        assert(minor is None)
        # Test that the module inserted has the same uuid as an older version
        # of m42955
        assert(uuid == 'f3c9ab70-a916-4d8c-9256-42953287b4e9')

        # Test that the latest row in modules is a collection with updated
        # version
        cursor.execute('SELECT * FROM modules m ORDER BY module_ident DESC')
        results = cursor.fetchone()
        new_collection_id = results[0]

        assert(results[1] == 'Collection')  # portal_type
        assert(results[5] ==
               '<span style="color:red;">Derived</span>'
               ' Copy of College <i>Physics</i>')  # name
        assert(results[11] == 'reedstrm')  # submitter
        assert(results[12] == 'I did not change something')  # submitlog
        assert(results[-5] == 1)  # major_version
        assert(results[-4] == 2)  # minor_version
        assert(results[-3] is None)  # print_style

        results = cursor.fetchone()
        new_collection_2_id = results[0]

        assert(results[1] == 'Collection')  # portal_type
        assert(results[5] == 'College Physics')  # name
        assert(results[11] == 'reedstrm')  # submitter
        assert(results[12] == 'I did not change something')  # submitlog
        assert(results[-5] == 7)  # major_version
        assert(results[-4] == 2)  # minor_version
        assert(results[-3] is None)  # print_style

        results = cursor.fetchone()
        new_subcollection_id = results[0]

        assert(results[1] == 'SubCollection')  # portal_type
        # name
        assert(results[5] == 'Introduction: The Nature of Science and Physics')
        assert(results[11] == 'reedstrm')  # submitter
        assert(results[12] == 'I did not change something')  # submitlog
        assert(results[-5] == 7)  # major_version
        assert(results[-4] == 2)  # minor_version
        assert(results[-3] is None)  # print_style

        results = cursor.fetchone()
        new_subcollection_2_id = results[0]

        assert(results[1] == 'SubCollection')  # portal_type
        # name
        assert(results[5] == 'Introduction: The Nature of Science and Physics')
        assert(results[11] == 'reedstrm')  # submitter
        assert(results[12] == 'I did not change something')  # submitlog
        assert(results[-5] == 1)  # major_version
        assert(results[-4] == 2)  # minor_version
        assert(results[-3] is None)  # print_style

        cursor.execute("UPDATE modules SET print_style = '*NEW PRINT STYLE*'"
                       " WHERE abstractid = 1")

        cursor.execute("SELECT print_style FROM modules WHERE abstractid = 1")

        print_style = cursor.fetchone()[0]

        assert(print_style == '*NEW PRINT STYLE*')

        cursor.execute('SELECT nodeid FROM trees '
                       'WHERE parent_id IS NULL ORDER BY nodeid DESC')
        new_nodeid = cursor.fetchone()[0]

        sql = '''
        WITH RECURSIVE t(node, parent, document,
                         title, childorder, latest, path) AS (
            SELECT tr.nodeid, tr.parent_id, tr.documentid, tr.title,
                   tr.childorder, tr.latest, ARRAY[tr.nodeid]
            FROM trees tr
            WHERE tr.nodeid = %(nodeid)s
        UNION ALL
            SELECT c.nodeid, c.parent_id, c.documentid, c.title,
                   c.childorder, c.latest, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON c.parent_id = t.node
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t'''

        cursor.execute(sql, {'nodeid': old_nodeid})
        old_tree = cursor.fetchall()

        cursor.execute(sql, {'nodeid': new_nodeid})
        new_tree = cursor.fetchall()

        # Test that the new collection tree is identical to the old collection
        # tree except for the new document ids
        assert(len(old_tree) == len(new_tree))

        # make sure all the node ids are different from the old ones
        old_nodeids = [i[0] for i in old_tree]
        new_nodeids = [i[0] for i in new_tree]
        all_nodeids = old_nodeids + new_nodeids
        assert(len(set(all_nodeids)) == len(all_nodeids))

        new_document_ids = {
            # old module_ident: new module_ident
            18: new_collection_id,
            1: new_collection_2_id,
            24: new_subcollection_id,
            22: new_subcollection_2_id,
            3: new_module_ident,
        }
        for i, old_node in enumerate(old_tree):
            assert(new_document_ids.get(old_node[2], old_node[2]) ==
                   new_tree[i][2])  # documentid
            assert(old_node[3] == new_tree[i][3])  # title
            assert(old_node[4] == new_tree[i][4])  # child order
            assert(old_node[5] == new_tree[i][5])  # latest
        use_cases.empty_all_tables(cursor)

    @unittest.skip("Not implemented")
    @testing.db_connect
    def test_module_files_from_cnxml(self, cursor):
        use_cases.empty_all_tables(cursor)
        file_data = os.path.join(DATA_DIRECTORY, 'data.sql')
        use_cases.add_all_data(cursor, file_data)

        # Insert abstract with cnxml
        cursor.execute('''\
        INSERT INTO abstracts
        (abstractid, abstract)
        VALUES
        (20802, 'Here is my <emphasis>string</emphasis> summary.')
        ''')

        # Insert a new version of an existing module
        cursor.execute('''\
        INSERT INTO modules
            (moduleid, portal_type, version, name, created, revised, authors,
             maintainers, licensors,  abstractid, stateid, licenseid, doctype,
             submitter, submitlog, language, parent)
        VALUES (
            'm42119', 'Module', '1.2', 'New Version',
            '2013-09-13 15:10:43.000000+02', '2013-09-13 15:10:43.000000+02',
            NULL, NULL, NULL, 20802, NULL, 11, '', NULL, '', 'en', NULL)
        RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        assert(cursor.fetchone()[0] == 0)

        # Make sure there's no fulltext index info
        cursor.execute('''SELECT count(*)
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        assert(cursor.fetchone()[0] == 0)

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''\
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''\
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''',
                           (new_module_ident, fileid, filename,))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''\
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''\
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
                       (new_module_ident, fileid,))

        # Test that html abstract is generated
        cursor.execute('''SELECT abstract, html FROM abstracts
            WHERE abstractid = 20802''')
        abstract, html = cursor.fetchone()
        assert(abstract ==
               'Here is my <emphasis>string</emphasis> summary.')
        assert('Here is my <strong>string</strong> summary.' in html)

        # Get the index.cnxml.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.cnxml.html' ''',
                       (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we generated exactly one index.cnxml.html for
        # new_module_ident
        assert(len(index_htmls) == 1)
        # Test that the index.cnxml.html contains html
        html = index_htmls[0][0][:]
        assert('<html' in html)

        # Test that the generated index.cnxml.html was processed for
        # fulltext search
        cursor.execute('''SELECT module_idx, fulltext
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        idx, fulltext = cursor.fetchall()[0]
        assert(len(idx) == 3545)
        assert('Introduction to Science and the Realm of Physics, '
               'Physical Quantities, and Units' in fulltext)
        use_cases.empty_all_tables(cursor)

    @unittest.skip("Not implemented")
    @testing.db_connect
    def test_module_files_from_html(self, cursor):
        use_cases.empty_all_tables(cursor)
        file_data = os.path.join(DATA_DIRECTORY, 'data.sql')
        use_cases.add_all_data(cursor, file_data)

        # Insert abstract with cnxml -- (this is tested elsewhere)
        # This also tests for when a abstract has a resource. The transfomr
        #   happens within when the add_module_file trigger is executed.
        #   This means the resouces should be available.
        abstract = ('Image: <media><image mime-type="image/jpeg"'
                    ' src="Figure_01_00_01.jpg" /></media>')
        cursor.execute("INSERT INTO abstracts (abstractid, abstract) "
                       "VALUES (20802, %s)",
                       (abstract,))

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules
            (moduleid, portal_type, version, name, created, revised, authors,
            maintainers, licensors,  abstractid, stateid, licenseid, doctype,
            submitter, submitlog, language, parent)
        VALUES (
            'm42119', 'Module', '1.2', 'New Version',
            '2013-09-13 15:10:43.000000+02', '2013-09-13 15:10:43.000000+02',
            NULL, NULL, NULL, 20802, NULL, 12, '', NULL, '', 'en', NULL)
        RETURNING module_ident''')
        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        assert(cursor.fetchone()[0] == 0)

        # Make sure there's no fulltext index info
        cursor.execute('''SELECT count(*)
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        assert(cursor.fetchone()[0] == 0)

        # Copy files for m42119 except *.html and *.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename NOT LIKE '%.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''', (new_module_ident, fileid, filename,))

        # Insert index.cnxml.html only after adding all the other files
        cursor.execute('''
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml.html'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml.html' ''',
                       (new_module_ident, fileid,))

        # Test that html abstract is generated
        cursor.execute('''SELECT abstract, html FROM abstracts
            WHERE abstractid = 20802''')
        old_abstract, html = cursor.fetchone()
        assert(old_abstract == abstract)
        assert(('Image: <span data-type="media"><img src="/resources/'
                'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"'
                ' data-media-type="image/jpeg" alt=""/></span>') in html)

        # Get the index.html.cnxml generated by the trigger
        cursor.execute("""SELECT file, filename
                        FROM module_files m JOIN files f ON m.fileid = f.fileid
                        WHERE module_ident = %s AND filename LIKE %s;""",
                       (new_module_ident, '%.cnxml'))
        index_cnxmls = cursor.fetchall()

        # Test that we generated index.html.cnxml and index.cnxml
        #   for new_module_ident
        assert(len(index_cnxmls) == 2)
        assert(sorted([fn for f, fn in index_cnxmls]) ==
               ['index.cnxml', 'index.html.cnxml'])
        # Test that the index.html.cnxml contains cnxml
        cnxml = index_cnxmls[0][0][:]
        assert('<document' in cnxml)

        # Test that the inserted index.cnxml.html was processed for fulltext
        # search
        cursor.execute('''SELECT module_idx, fulltext
        FROM modulefti WHERE module_ident = %s''',
                       (new_module_ident,))
        idx, fulltext = cursor.fetchall()[0]
        assert(len(idx) == 3556)
        assert('Introduction to Science and the Realm of Physics, '
               'Physical Quantities, and Units' in fulltext)
        use_cases.empty_all_tables(cursor)

    @unittest.skip("Not implemented")
    @testing.db_connect
    def test_module_files_overwrite_index_html(self, cursor):
        use_cases.empty_all_tables(cursor)
        file_data = os.path.join(DATA_DIRECTORY, 'data.sql')
        use_cases.add_all_data(cursor, file_data)

        # Insert a new version of an existing module
        cursor.execute('''
        INSERT INTO modules
            (moduleid, portal_type, version, name, created, revised, authors,
             maintainers, licensors,  abstractid, stateid, licenseid, doctype,
             submitter, submitlog, language, parent)
        VALUES (
            'm42119', 'Module', '1.2', 'New Version',
            '2013-09-13 15:10:43.000000+02', '2013-09-13 15:10:43.000000+02',
            NULL, NULL, NULL, 1, NULL, 11, '', NULL, '', 'en', NULL)
        RETURNING module_ident''')

        new_module_ident = cursor.fetchone()[0]

        # Make sure there are no module files for new_module_ident in the
        # database
        cursor.execute('''SELECT count(*) FROM module_files
        WHERE module_ident = %s''', (new_module_ident,))
        assert(cursor.fetchone()[0] == 0)

        # Create index.cnxml.html to make sure module files trigger will
        # NOT overwrite it
        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        custom_content = 'abcd'
        cursor.execute('''
            INSERT INTO files (file, media_type)
            VALUES (%s, 'text/html') RETURNING fileid''',
                       [custom_content])
        fileid = cursor.fetchone()[0]
        cursor.execute('''INSERT INTO module_files
            (module_ident, fileid, filename)
            VALUES (%s, %s, 'index.cnxml.html')''',
                       [new_module_ident, fileid])
        cursor.execute('ALTER TABLE module_files ENABLE TRIGGER ALL')

        # Copy files for m42119 except *.html and index.cnxml
        cursor.execute('''
        SELECT f.file, m.filename, f.media_type
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE m.module_ident = 3 AND m.filename NOT LIKE '%.html'
        AND m.filename != 'index.cnxml'
        ''')

        for data, filename, media_type in cursor.fetchall():
            sha1 = hashlib.new('sha1', data[:]).hexdigest()
            cursor.execute("SELECT fileid from files where sha1 = %s",
                           (sha1,))
            try:
                fileid = cursor.fetchone()[0]
            except TypeError:
                cursor.execute('''INSERT INTO files (file, media_type)
                VALUES (%s, %s)
                RETURNING fileid''', (data, media_type,))
                fileid = cursor.fetchone()[0]
            cursor.execute('''
            INSERT INTO module_files (module_ident, fileid, filename)
            VALUES (%s, %s, %s)''', (new_module_ident, fileid, filename))

        # Insert index.cnxml only after adding all the other files
        cursor.execute('''
        SELECT fileid
        FROM module_files
        WHERE module_ident = 3 AND filename = 'index.cnxml'
        ''')
        fileid = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO module_files (module_ident, fileid, filename)
            SELECT %s, %s, m.filename
            FROM module_files m JOIN files f ON m.fileid = f.fileid
            WHERE m.module_ident = 3 AND m.filename = 'index.cnxml' ''',
                       (new_module_ident, fileid,))

        # Get the index.cnxml.html generated by the trigger
        cursor.execute('''SELECT file
        FROM module_files m JOIN files f ON m.fileid = f.fileid
        WHERE module_ident = %s AND filename = 'index.cnxml.html' ''',
                       (new_module_ident,))
        index_htmls = cursor.fetchall()

        # Test that we DID NOT generate an index.cnxml.html for
        # new_module_ident
        assert(len(index_htmls) == 1)
        # Test that the index.cnxml.html contains the custom content.
        html = index_htmls[0][0][:]
        assert(custom_content == html)
        use_cases.empty_all_tables(cursor)

    @testing.db_connect
    def test_collated_fulltext_indexing_triggers(self, cursor):
        """Verify that inserting a collated file association builds
        the necessary indexes.  This is used when a book is cooked.
        """
        self.resetTables(cursor)
        cursor.execute("""INSERT INTO files (fileid, file, media_type)
                       VALUES(108,
                            '<?xml version="1.0" encoding="UTF-8"?>
                            <html>
                                <body>text følger the text hello test</body>
                            </html>',
                            'text/html')""")
        use_cases.add_module(cursor, returning='module_ident')
        module1_ident = cursor.fetchone()[0]
        use_cases.add_module(cursor, moduleid='m2', returning='module_ident')
        module2_ident = cursor.fetchone()[0]

        cursor.execute("""INSERT INTO collated_file_associations
                          (context, item, fileid)
                          VALUES(%s,%s,108)""",
                       (module1_ident, module2_ident, ))
        # Verify that the inserted file has been indexed
        cursor.execute('SELECT length(module_idx) FROM collated_fti '
                       'WHERE context=%s AND item=%s',
                       (module1_ident, module2_ident, ))
        assert(cursor.fetchone()[0] == 4)

        cursor.execute('SELECT lexeme FROM  collated_fti_lexemes '
                       'WHERE context=%s AND item=%s',
                       (module1_ident, module2_ident, ))
        lexemes = cursor.fetchall()
        assert(len(lexemes) == 4)
        assert(("'følger",) in lexemes)

    @testing.db_connect
    def test_tree_to_json(self, cursor):
        """Verify the results of the ``tree_to_json_for_legacy`` sql function.
        This is used during a cnx-publishing publication.
        """
        self.resetTables(cursor)
        cursor.execute("""INSERT INTO document_controls (uuid)
        VALUES ('e79ffde3-7fb4-4af3-9ec8-df648b391597'::uuid)""")

        # populate modules tables
        use_cases.add_collection(cursor, moduleid='col11406',
                                 uuid='e79ffde3-7fb4-4af3-9ec8-df648b391597',
                                 name='College Physics', version='1.7',
                                 major_version=7, minor_version=1,
                                 returning='module_ident')
        collection_ident = cursor.fetchone()[0]
        use_cases.add_module(cursor, moduleid='m42955', name='Preface',
                             version='1.7', returning='module_ident')
        module_ident_0 = cursor.fetchone()[0]

        use_cases.add_module(
            cursor, portal_type='SubCollection', moduleid='subcol',
            name='Introduction: The Nature of Science and Physics',
            returning='module_ident')
        subcol_ident_1 = cursor.fetchone()[0]
        cursor.execute("""UPDATE modules SET version=null
                          WHERE module_ident=%s;""", (subcol_ident_1,))
        use_cases.add_module(
            cursor, moduleid='m42119', version='1.3',
            name=('Introduction to Science and the Realm of Physics, '
                  'Physical Quantities, and Units'),
            returning='module_ident')
        module_ident_1_1 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42092', version='1.4',
            name='Physics: An Introduction', returning='module_ident')
        module_ident_1_2 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42091', version='1.6',
            name='Physical Quantities and Units', returning='module_ident')
        module_ident_1_3 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42120', version='1.7',
            name='Accuracy, Precision, and Significant Figures',
            returning='module_ident')
        module_ident_1_4 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42121', version='1.5',
            name='Approximation', returning='module_ident')
        module_ident_1_5 = cursor.fetchone()[0]

        use_cases.add_module(
            cursor, portal_type='SubCollection', moduleid='subcol',
            name=("Further Applications of Newton's Laws:"
                  " Friction, Drag, and Elasticity"),
            returning='module_ident')
        subcol_ident_2 = cursor.fetchone()[0]
        cursor.execute("""UPDATE modules SET version=null
                          WHERE module_ident=%s;""", (subcol_ident_2,))
        use_cases.add_module(
            cursor, moduleid='m42138', version='1.2',
            name='Introduction: Further Applications of Newton’s Laws',
            returning='module_ident')
        module_ident_2_1 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42139', version='1.5',
            name='Friction', returning='module_ident')
        module_ident_2_2 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42080', version='1.6',
            name='Drag Forces', returning='module_ident')
        module_ident_2_3 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42081', version='1.8',
            name='Elasticity: Stress and Strain', returning='module_ident')
        module_ident_2_4 = cursor.fetchone()[0]

        use_cases.add_module(
            cursor, moduleid='m42699', version='1.3',
            name='Atomic Masses', returning='module_ident')
        module_ident_3 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42702', version='1.2',
            name='Selected Radioactive Isotopes', returning='module_ident')
        module_ident_4 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42720', version='1.5',
            name='Useful Information', returning='module_ident')
        module_ident_5 = cursor.fetchone()[0]
        use_cases.add_module(
            cursor, moduleid='m42709', version='1.5',
            name='Glossary of Key Symbols and Notation',
            returning='module_ident')
        module_ident_6 = cursor.fetchone()[0]

        # Create a tree
        use_cases.add_tree(cursor, documentid=collection_ident,
                           title='College Physics', returning='nodeid')
        collection_node = cursor.fetchone()[0]

        use_cases.add_tree(
            cursor, parent_id=collection_node,
            documentid=module_ident_0, childorder=0, title='Preface')
        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=module_ident_3,
            childorder=3, title='Atomic Masses')
        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=module_ident_4,
            childorder=4, title='Selected Radioactive Isotopes')
        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=module_ident_5,
            childorder=5, title='Useful Information')
        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=module_ident_6,
            childorder=6, title='Glossary of Key Symbols and Notation')

        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=subcol_ident_1,
            childorder=1, returning='nodeid',
            title='Introduction: The Nature of Science and Physics',)
        subcol_node_1 = cursor.fetchone()[0]
        use_cases.add_tree(
            cursor, parent_id=subcol_node_1, documentid=module_ident_1_1,
            childorder=0, title=('Introduction to Science and the Realm of '
                                 'Physics, Physical Quantities, and Units'))
        use_cases.add_tree(
            cursor, parent_id=subcol_node_1, documentid=module_ident_1_2,
            childorder=1, title='Physics: An Introduction')
        use_cases.add_tree(
            cursor, parent_id=subcol_node_1, documentid=module_ident_1_3,
            childorder=2, title='Physical Quantities and Units')
        use_cases.add_tree(
            cursor, parent_id=subcol_node_1, documentid=module_ident_1_4,
            childorder=3, title='Accuracy, Precision, and Significant Figures')
        use_cases.add_tree(
            cursor, parent_id=subcol_node_1, documentid=module_ident_1_5,
            childorder=4, title='Approximation')

        use_cases.add_tree(
            cursor, parent_id=collection_node, documentid=subcol_ident_2,
            childorder=2, title=("Further Applications of Newton's Laws: "
                                 "Friction, Drag, and Elasticity"),
            returning='nodeid')
        subcol_node_2 = cursor.fetchone()[0]
        use_cases.add_tree(
            cursor, parent_id=subcol_node_2, documentid=module_ident_2_1,
            childorder=0, title=('Introduction: Further Applications of'
                                 ' Newton\u2019s Laws'))
        use_cases.add_tree(
            cursor, parent_id=subcol_node_2, documentid=module_ident_2_2,
            childorder=1, title='Friction')
        use_cases.add_tree(
            cursor, parent_id=subcol_node_2, documentid=module_ident_2_3,
            childorder=2, title='Drag Forces')
        use_cases.add_tree(
            cursor, parent_id=subcol_node_2, documentid=module_ident_2_4,
            childorder=3, title='Elasticity: Stress and Strain')

        expected_tree = {
            u'id': u'col11406',
            u'title': u'College Physics',
            u'version': u'1.7',
            u'contents': [
                {u'id': u'm42955', u'title': u'Preface', u'version': u'1.7'},
                {u'id': u'subcol',
                 u'title': u'Introduction: The Nature of Science and Physics',
                 u'version': None,
                 u'contents': [
                     {u'id': u'm42119',
                      u'title': u'Introduction to Science and the Realm of '
                                u'Physics, Physical Quantities, and Units',
                      u'version': u'1.3'},
                     {u'id': u'm42092',
                      u'title': u'Physics: An Introduction',
                      u'version': u'1.4'},
                     {u'id': u'm42091',
                      u'title': u'Physical Quantities and Units',
                      u'version': u'1.6'},
                     {u'id': u'm42120',
                      u'title': u'Accuracy, Precision, and Significant '
                                u'Figures',
                      u'version': u'1.7'},
                     {u'id': u'm42121',
                      u'title': u'Approximation',
                      u'version': u'1.5'}]},
                {u'id': u'subcol',
                 u'title': u"Further Applications of Newton's Laws: Friction,"
                           u" Drag, and Elasticity",
                 u'version': None,
                 u'contents': [
                     {u'id': u'm42138',
                      u'title': u'Introduction: Further Applications of '
                                u'Newton\\u2019s Laws',
                      u'version': u'1.2'},
                     {u'id': u'm42139',
                      u'title': u'Friction',
                      u'version': u'1.5'},
                     {u'id': u'm42080',
                      u'title': u'Drag Forces',
                      u'version': u'1.6'},
                     {u'id': u'm42081',
                      u'title': u'Elasticity: Stress and Strain',
                      u'version': u'1.8'}]},
                {u'id': u'm42699',
                 u'title': u'Atomic Masses',
                 u'version': u'1.3'},
                {u'id': u'm42702',
                 u'title': u'Selected Radioactive Isotopes',
                 u'version': u'1.2'},
                {u'id': u'm42720',
                 u'title': u'Useful Information',
                 u'version': u'1.5'},
                {u'id': u'm42709',
                 u'title': u'Glossary of Key Symbols and Notation',
                 u'version': u'1.5'}]}
        cursor.execute("""\
            SELECT tree_to_json_for_legacy(
                'e79ffde3-7fb4-4af3-9ec8-df648b391597', '7.1')::json
        """)
        tree = cursor.fetchone()[0]
        assert(expected_tree == json.loads(tree))

    @unittest.skip("Not implemented")
    def test_blank_abstract(self, cursor):
        # Insert blank abstract
        with self.assertRaises(psycopg2.InternalError) as caught_exception:
            cursor.execute("INSERT INTO abstracts (abstractid) "
                           "VALUES (20801)")
        self.assertIn("Blank entry", caught_exception.exception.message)


@pytest.mark.skipif(testing.is_py3(),
                    reason="triggers are only python2.x compat")
class TestUpdateLatestTriggerTestCase:
    """Test case for updating the latest_modules table
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def resetTables(self, cursor):
        cursor.execute("DELETE FROM moduletags;")
        cursor.execute("DELETE FROM modules;")

    @testing.db_connect
    def test_insert_new_module(self, cursor):
        self.resetTables(cursor)

        use_cases.add_module(cursor, stateid=1, returning='module_ident, uuid')
        module_ident, uuid = cursor.fetchone()

        cursor.execute("SELECT module_ident FROM latest_modules WHERE uuid=%s",
                       (uuid, ))
        assert(cursor.fetchone()[0] == module_ident)

    @testing.db_connect
    def test_insert_existing_module(self, cursor):
        self.resetTables(cursor)
        use_cases.add_module(cursor, stateid=1, returning='module_ident, uuid')
        module_ident, uuid = cursor.fetchone()

        # FIXME the stateid for this insert was originally 2
        # but that is no longer a valid state id
        use_cases.add_module(cursor, stateid=1, uuid=uuid,
                             name='Changed name of m1',
                             returning='module_ident, uuid')
        module_ident, uuid = cursor.fetchone()

        cursor.execute('''SELECT module_ident FROM latest_modules
        WHERE uuid = %s''', [uuid])
        assert(cursor.fetchone()[0] == module_ident)

    @testing.db_connect
    def test_insert_not_latest_version(self, cursor):
        self.resetTables(cursor)
        """This test case is specifically written for backfilling, new inserts
        may not mean new versions
        """
        use_cases.add_module(cursor, stateid=1, returning='module_ident, uuid')
        module_ident, uuid = cursor.fetchone()

        # FIXME the stateid for this insert was originally 3
        # but that is no longer a valid state id
        use_cases.add_module(cursor, stateid=5,
                             name='Changed name of m1 again',
                             uuid=uuid, returning='module_ident, uuid')
        module_ident, uuid = cursor.fetchone()

        # FIXME the stateid for this insert was originally 2
        # but that is no longer a valid state id
        use_cases.add_module(cursor, stateid=4, name='Changed name of m1',
                             uuid=uuid, returning='module_ident, uuid')

        cursor.execute("SELECT module_ident FROM latest_modules WHERE uuid=%s",
                       (uuid, ))


@pytest.mark.skipif(testing.is_py3(),
                    reason="triggers are only python2.x compat")
class TestLegacyCompatTriggerTestCase:
    """Test the legacy compotibilty trigger that fills in legacy data
    coming from contemporary publications.

    Contemporary publications MUST not set the legacy ``version``,
    which defaults to null. They also MUST supply the moduleid,
    but only when making a revision publication, which ties the ``uuid``
    to the legacy ``moduleid``.
    """

    def resetTables(self, cursor):
        cursor.execute("DELETE FROM document_acl;")
        cursor.execute("DELETE FROM document_controls;")
        cursor.execute("DELETE FROM moduletags;")
        cursor.execute("DELETE FROM modules;")
        cursor.execute("DELETE FROM persons;")
        cursor.execute("DELETE FROM users;")

    @testing.db_connect
    def test_new_module(self, cursor):
        """Verify publishing of a new module creates values for legacy fields.
        """
        cursor.execute("SELECT setval('moduleid_seq', 9999)")
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')
        abstract_id = cursor.fetchone()[0]

        # Insert a new module.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version, moduleid,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
               DEFAULT, 'Module', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              moduleid, major_version, minor_version, version
            """, (abstract_id,))
        moduleid, major_ver, minor_ver, ver = cursor.fetchone()

        # Check the fields where correctly assigned.
        assert(moduleid == 'm10000')
        assert(major_ver == 1)
        assert(minor_ver is None)
        assert(ver == '1.1')

    @testing.db_connect
    def test_new_collection(self, cursor):
        """Verify publishing a new collection creates values for legacy fields.
        """
        cursor.execute("SELECT setval('collectionid_seq', 9999)")

        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]

        # Insert a new collection.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (DEFAULT, DEFAULT, DEFAULT,
               DEFAULT, 'Collection', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              moduleid, major_version, minor_version, version
        """, (abstract_id, ))
        moduleid, major_ver, minor_ver, ver = cursor.fetchone()

        # Check the fields where correctly assigned.
        assert(moduleid == 'col10000')
        assert(major_ver == 1)
        assert(minor_ver == 1)
        assert(ver == '1.1')

    @testing.db_connect
    def test_module_revision(self, cursor):
        """Verify publishing of a module revision uses legacy field values.
        """
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]

        cursor.execute("SELECT setval('moduleid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'm{}'.format(id_num)  # m10101
        # Insert a new module to base a revision on.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version, moduleid,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
               DEFAULT, 'Module', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              uuid, moduleid, major_version, minor_version, version;
            """, (abstract_id,))
        uuid_, moduleid, major_ver, minor_ver, ver = cursor.fetchone()
        assert(moduleid == expected_moduleid)

        # Now insert the revision.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version, moduleid,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (%s, 2, DEFAULT, %s,
               DEFAULT, 'Module', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              uuid, moduleid, major_version, minor_version, version
            """, (uuid_, moduleid, abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        assert(rev_moduleid == expected_moduleid)
        assert(ver == '1.1')
        assert(rev_major_ver == 2)
        assert(rev_minor_ver is None)
        assert(rev_ver == '1.2')

    @testing.db_connect
    def test_collection_revision(self, cursor):
        """Verify publishing of a collection revision uses legacy field values.
        """
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]

        cursor.execute("SELECT setval('collectionid_seq', 10100)")
        id_num = cursor.fetchone()[0] + 1
        expected_moduleid = 'col{}'.format(id_num)  # col10101
        # Insert a new module to base a revision on.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version, moduleid,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
               DEFAULT, 'Collection', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              uuid, moduleid, major_version, minor_version, version
            """, (abstract_id,))
        uuid_, moduleid, major_ver, minor_ver, ver = cursor.fetchone()
        assert(moduleid == expected_moduleid)

        # Now insert the revision.
        cursor.execute("""\
            INSERT INTO modules
              (uuid, major_version, minor_version, moduleid,
               module_ident, portal_type, name, created, revised, language,
               submitter, submitlog,
               abstractid, licenseid, parent, parentauthors,
               authors, maintainers, licensors,
               google_analytics, buylink,
               stateid, doctype)
            VALUES
              (%s, 2, 1, %s,
               DEFAULT, 'Collection', 'Plug into the collective conscious',
               '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
               'publisher', 'published',
               %s, 11, DEFAULT, DEFAULT,
               '{smoo, fred}', DEFAULT, '{smoo, fred}',
               DEFAULT, DEFAULT,
               DEFAULT, ' ')
            RETURNING
              uuid, moduleid, major_version, minor_version, version
            """, (uuid_, moduleid, abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        assert(rev_moduleid == expected_moduleid)
        assert(ver == '1.1')
        assert(rev_major_ver == 2)
        assert(rev_minor_ver == 1)
        assert(rev_ver == '1.2')

    @testing.db_connect
    def test_anti_republish_module_on_collection_revision(self, cursor):
        """Verify publishing of a collection revision with modules included
        in other collections. Contemporary publications should not republish
        the modules within the current collections in the publication context.

        Note, contemporary publications do NOT utilize the trigger
        that causes minor republications of collections. This feature
        is only enabled for legacy publications.

        This introduces two collections with a shared module.
        The goal is to publish one of the collections and not have
        the other collection republish.
        """
        self.resetTables(cursor)
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]

        cursor.execute("SELECT setval('collectionid_seq', 10100)")
        id_num = cursor.fetchone()[0]
        expected_col_one_id = 'col{}'.format(id_num + 1)  # col10101
        expected_col_two_id = 'col{}'.format(id_num + 2)  # col10102
        cursor.execute("SELECT setval('moduleid_seq', 10100)")
        id_num = cursor.fetchone()[0]
        expected_m_one_id = 'm{}'.format(id_num + 1)  # m10101
        expected_m_two_id = 'm{}'.format(id_num + 2)  # m10102

        entries = [expected_m_one_id, expected_m_two_id,
                   expected_col_one_id, expected_col_two_id,
                   ]
        for mid in entries:
            portal_type = mid.startswith('m') and 'Module' or 'Collection'
            # Insert a new module to base a revision on.
            cursor.execute("""\
                INSERT INTO modules
                  (uuid, major_version, minor_version, moduleid,
                   module_ident, portal_type, name, created, revised, language,
                   submitter, submitlog,
                   abstractid, licenseid, parent, parentauthors,
                   authors, maintainers, licensors,
                   google_analytics, buylink,
                   stateid, doctype)
                VALUES
                  (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
                   DEFAULT, %s, %s,
                   '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
                   'publisher', 'published',
                   %s, 11, DEFAULT, DEFAULT,
                   '{smoo, fred}', DEFAULT, '{smoo, fred}',
                   DEFAULT, DEFAULT,
                   DEFAULT, ' ')
                RETURNING
                  module_ident, uuid, moduleid, major_version,
                  minor_version, version
                """, (portal_type, "title for {}".format(mid), abstract_id,))
            ident, uuid_, moduleid, maj_ver, min_ver, ver = cursor.fetchone()
            assert(moduleid == mid)

            if portal_type == 'Collection':
                args = (ident, "**{}**".format(moduleid),)
                cursor.execute("""\
                INSERT INTO trees
                  (nodeid, parent_id, documentid, title, childorder, latest)
                VALUES
                  (DEFAULT, NULL, %s, %s, DEFAULT, DEFAULT)
                RETURNING nodeid""", args)
                root_node_id = cursor.fetchone()[0]
                # Insert the tree for the collections.
                for i, sub_mid in enumerate(entries[:2]):
                    args = (root_node_id, sub_mid, sub_mid, i,)
                    cursor.execute("""\
                    INSERT INTO trees
                      (nodeid, parent_id,
                       documentid,
                       title, childorder, latest)
                    VALUES
                      (DEFAULT, %s,
                       (select module_ident from latest_modules
                        where moduleid = %s),
                       %s, %s, DEFAULT)""", args)

        # Now insert a revision.
        cursor.execute("""\
        INSERT INTO modules
          (uuid, major_version, minor_version, moduleid,
           module_ident, portal_type, name, created, revised, language,
           submitter, submitlog,
           abstractid, licenseid, parent, parentauthors,
           authors, maintainers, licensors,
           google_analytics, buylink,
           stateid, doctype)
        VALUES
          ((SELECT uuid FROM latest_modules WHERE moduleid = %s),
           2, NULL, %s,
           DEFAULT, 'Module', ' MOO ',
           '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
           'publisher', 'published',
           %s, 11, DEFAULT, DEFAULT,
           '{smoo, fred}', DEFAULT, '{smoo, fred}',
           DEFAULT, DEFAULT,
           DEFAULT, ' ')
        RETURNING
          uuid, moduleid,  major_version, minor_version, version
        """, (expected_m_one_id, expected_m_one_id, abstract_id,))
        res = cursor.fetchone()
        rev_uuid_, rev_moduleid, rev_major_ver, rev_minor_ver, rev_ver = res

        # Check the fields where correctly assigned.
        assert(rev_moduleid == expected_m_one_id)
        assert(rev_major_ver == 2)
        assert(rev_minor_ver is None)
        assert(rev_ver == '1.2')

        # Lastly check that no republications took place.
        # This can be done by simply counting the entries. We inserted
        # four entries (two modules and two collections) and one revision.
        cursor.execute("""\
        SELECT portal_type, count(*)
        FROM modules
        GROUP BY portal_type""")
        counts = dict(cursor.fetchall())
        expected_counts = {
            'Module': 3,
            'Collection': 2,
        }
        assert(counts == expected_counts)

    @testing.db_connect
    def test_new_module_wo_uuid(self, cursor):
        """Verify legacy publishing of a new module creates a UUID
        and licenseid in a 'document_controls' entry.
        """
        self.resetTables(cursor)

        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]

        # Insert a new module.
        cursor.execute("""\
        INSERT INTO modules
          (uuid, major_version, minor_version, moduleid,
           module_ident, portal_type, name, created, revised, language,
           submitter, submitlog,
           abstractid, licenseid, parent, parentauthors,
           authors, maintainers, licensors,
           google_analytics, buylink,
           stateid, doctype)
        VALUES
          (DEFAULT, DEFAULT, DEFAULT, DEFAULT,
           DEFAULT, 'Module', 'Plug into the collective conscious',
           '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
           'publisher', 'published',
           %s, 11, DEFAULT, DEFAULT,
           '{smoo, fred}', DEFAULT, '{smoo, fred}',
           DEFAULT, DEFAULT,
           DEFAULT, ' ')
        RETURNING
          uuid, licenseid""", (abstract_id,))
        uuid_, license_id = cursor.fetchone()

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("SELECT uuid, licenseid from document_controls")
        try:
            controls_uuid, controls_license_id = cursor.fetchone()
        except TypeError:
            assert(False), "the document_controls entry was not made."

        # Check the values match
        assert(uuid_ == controls_uuid)
        assert(license_id == controls_license_id)

    @testing.db_connect
    def test_new_module_user_upsert(self, cursor):
        """Verify legacy publishing of a new module upserts users
        from the persons table into the users table.
        """
        self.resetTables(cursor)
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')

        abstract_id = cursor.fetchone()[0]
        # Insert the legacy persons records.
        #   These people would have registered on legacy after the initial
        #   migration of legacy users.
        cursor.execute("""\
        INSERT INTO persons
          (personid, honorific, firstname, surname, fullname)
        VALUES
          ('cnxcap', NULL, 'College', 'Physics', 'OSC Physics Maintainer'),
          ('legacy', NULL, 'Legacy', 'User', 'Legacy User'),
          ('ruins', NULL, 'Legacy', 'Ruins', 'Legacy Ruins')""")
        # Insert one existing user into the users shadow table.
        cursor.execute("""\
            INSERT INTO users (username, first_name, last_name,
                               full_name, is_moderated)
            VALUES ('cnxcap', 'College', 'Physics',
                    'OSC Physics Maintainer', 't')""")
        # Insert a new legacy module.
        cursor.execute("""\
        INSERT INTO modules
          (moduleid, version,
           module_ident, portal_type, name, created, revised, language,
           submitter, submitlog,
           abstractid, licenseid, parent, parentauthors,
           authors, maintainers, licensors,
           google_analytics, buylink,
           stateid, doctype)
        VALUES
          (DEFAULT, '1.1',
           DEFAULT, 'Module', 'Plug into the collective conscious',
           '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
           'publisher', 'published',
           %s, 11, DEFAULT, DEFAULT,
           '{legacy}', '{cnxcap}', '{ruins}',
           DEFAULT, DEFAULT,
           DEFAULT, ' ')
        RETURNING
          uuid, licenseid""", (abstract_id,))
        uuid_, license_id = cursor.fetchone()

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("""\
        SELECT username, first_name, last_name, full_name
        FROM users
        WHERE username = any('{legacy, ruins}'::text[])
        ORDER BY username""")
        user_records = cursor.fetchall()

        # Check for the upsert.
        assert(user_records[0] ==
               ('legacy', 'Legacy', 'User', 'Legacy User',))
        assert(user_records[1] ==
               ('ruins', 'Legacy', 'Ruins', 'Legacy Ruins',))

    @testing.db_connect
    def test_update_user_update(self, cursor):
        """Verify legacy updating of user account also updates rewrite
        """
        self.resetTables(cursor)
        # Insert the legacy persons records.
        #   This person would have registered on legacy already,
        #   so we insert them there too.
        cursor.execute("""\
            INSERT INTO persons
            (personid, firstname, surname, fullname)
            VALUES
            ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer')
        """)
        cursor.execute("""\
            INSERT INTO users
            (username, first_name, last_name, full_name)
            VALUES
            ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer')
        """)

        # Update user profile on legacy
        cursor.execute("""\
            UPDATE persons
            SET firstname = 'Univeristy',
                surname = 'Maths',
                fullname = 'OSC Maths Maintainer'
            WHERE personid = 'cnxcap'
        """)

        # Grab the user from users table to verify it's updated
        cursor.execute("""\
            SELECT username, first_name, last_name, full_name
            FROM users
            WHERE username = 'cnxcap'
        """)
        rewrite_user_record = cursor.fetchone()

        # Check for the update.
        assert(rewrite_user_record ==
               ('cnxcap', 'Univeristy', 'Maths', 'OSC Maths Maintainer'))

    @testing.db_connect
    def test_new_moduleoptionalroles_user_insert(self, cursor):
        """Verify publishing of a new moduleoptionalroles record
        inserts users from the persons table into the users table.
        This should only insert new records and leave the existing
        records as they are, because we have no way of telling whether
        the publication was by legacy or cnx-publishing.
        """
        self.resetTables(cursor)
        use_cases.add_abstract(cursor, abstract=' ', returning='abstractid')
        abstract_id = cursor.fetchone()[0]
        # Insert the legacy persons records.
        #   These people would have registered on legacy after the initial
        #   migration of legacy users.
        # The '***' on the cnxcap user is to test that the users record
        #   is not updated from the persons record.
        cursor.execute("""\
        INSERT INTO persons
          (personid, honorific, firstname, surname, fullname)
        VALUES
          ('cnxcap', NULL, '*** College ***', '*** Physics ***',
           '*** OSC Physics Maintainer ***'),
          ('legacy', NULL, 'Legacy', 'User', 'Legacy User'),
          ('ruins', NULL, 'Legacy', 'Ruins', 'Legacy Ruins')""")
        # Insert one existing user into the users shadow table.
        cursor.execute("""\
        INSERT INTO users
            (username, first_name, last_name, full_name, is_moderated)
        VALUES
            ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer', 't')""")
        # Insert a new legacy module.
        cursor.execute("""\
        INSERT INTO modules
          (moduleid, version,
           module_ident, portal_type, name, created, revised, language,
           submitter, submitlog,
           abstractid, licenseid, parent, parentauthors,
           authors, maintainers, licensors,
           google_analytics, buylink,
           stateid, doctype)
        VALUES
          (DEFAULT, '1.1',
           DEFAULT, 'Module', 'Plug into the collective conscious',
           '2012-02-28T11:37:30', '2012-02-28T11:37:30', 'en-us',
           'publisher', 'published',
           %s, 11, DEFAULT, DEFAULT,
           '{legacy}', '{legacy}', '{legacy}',
           DEFAULT, DEFAULT,
           DEFAULT, ' ')
        RETURNING
          module_ident, uuid, licenseid""", (abstract_id,))
        module_ident, uuid_, license_id = cursor.fetchone()
        # Insert the moduleoptionalroles records.
        cursor.execute("""\
        INSERT INTO moduleoptionalroles (module_ident, roleid, personids)
        VALUES (%s, 4, '{cnxcap, ruins}')""", (module_ident,))

        # Hopefully pull the UUID out of the 'document_controls' table.
        cursor.execute("""\
        SELECT username, first_name, last_name, full_name
        FROM users
        ORDER BY username
        """)
        user_records = cursor.fetchall()

        # Check for the record set...
        # The cnxcap user should not have been updated.
        assert([x[0] for x in user_records] == ['cnxcap', 'legacy', 'ruins'])
        assert(user_records[0] ==
               ('cnxcap', 'College', 'Physics', 'OSC Physics Maintainer',))
        assert(user_records[1] == ('legacy', 'Legacy', 'User', 'Legacy User',))
        # The ruins user will be a newly inserted record, copied from
        #   the persons record.
        assert(user_records[2] ==
               ('ruins', 'Legacy', 'Ruins', 'Legacy Ruins',))
