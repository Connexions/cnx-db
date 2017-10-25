# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import subprocess
import sys

import pytest
from psycopg2 import Binary


def py3_too_old(*args):
    if sys.version_info >= (3,) and os.path.exists('/usr/bin/python3'):
        out = subprocess.check_output(['/usr/bin/python3', '--version'])
        return out < b'Python 3.4'


class BaseTestCase(object):

    @pytest.fixture(autouse=True)
    def suite_fixture(self, xxx_archive_data, faux_plpy, db_cursor):
        self.faux_plpy = faux_plpy
        self.db_cursor = db_cursor


# ############### #
#   cnxml->html   #
# ############### #

class TestAbstractToHtml(BaseTestCase):

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from cnxdb.triggers.transforms.producers import (
            produce_html_for_abstract)
        return produce_html_for_abstract(self.faux_plpy,
                                         *args, **kwargs)

    def test_success(self):
        # Case to test for a successful tranformation of an abstract from
        #   cnxml to html.
        document_ident, abstractid = 2, 2  # m42955
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT html FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        html = self.db_cursor.fetchone()[0]
        expected = '<ul><li>one</li><li>two</li><li>three</li></ul>'
        assert html.find(expected) >= 0

    def test_success_w_reference(self):
        # Case with an abstract containing an internal reference.
        document_ident, abstractid = 3, 3
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT html FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        html = self.db_cursor.fetchone()[0]
        expected = 'href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce"'
        assert expected in html

    def test_success_w_cnxml_root_element(self):
        # Case with an abstract that contains an outter xml element
        #   (e.g. <para>).
        document_ident, abstractid = 4, 4
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT html FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        html = self.db_cursor.fetchone()[0]
        expected = ('<p>A link to the <a href="http://example.com">'
                    'outside world</a>.</p>')
        assert html.find(expected) >= 0

    def test_success_w_no_cnxml(self):
        # Case that ensures plaintext abstracts get wrapped with xml
        #   and include the various namespaces.
        document_ident, abstractid = 5, 5
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT html FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        html = self.db_cursor.fetchone()[0]
        expected = 'A rather short plaintext abstract.</div>'
        # Check for the ending wrapper tag, but not the initial one, because
        #   the namespaces are unordered and can't reliably be tested.
        assert html.find(expected) >= 0

    def test_success_w_empty(self):
        # Case that ensures an empty abstract is saved as an empty html
        #   entry.
        document_ident, abstractid = 6, 6
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT html FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        html = self.db_cursor.fetchone()[0]
        assert html is None

    def test_failure_on_nonexistent_document(self):
        # Case to ensure failure the requested document doesn't exist.
        document_ident = 50

        with pytest.raises(ValueError) as exc_info:
            self.call_target(document_ident)
        # Just ensure that we aren't blind when the exception is raised.
        assert str(exc_info.value).find(str(document_ident)) >= 0

    def test_failure_on_missing_abstract(self):
        # Case to ensure failure when an abstract is missing.
        document_ident, abstractid = 5, 5
        self.db_cursor.execute(
            "UPDATE modules SET (abstractid) = (null) "
            "WHERE module_ident = %s;",
            (document_ident,))
        self.db_cursor.execute(
            "DELETE FROM abstracts WHERE abstractid = %s;",
            (abstractid,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import MissingAbstract
        with pytest.raises(MissingAbstract):
            self.call_target(document_ident)

    @pytest.mark.skipif(py3_too_old)
    def test_abstract_w_resource_reference(self):
        # Case to ensure the reference resolution for resources.
        # This test requires a document_ident in order match with
        #   a module_files record.
        abstract = ('Image: <media><image mime-type="image/jpeg" '
                    'src="Figure_01_00_01.jpg" /></media>')
        self.db_cursor.execute(
            "INSERT INTO abstracts (abstract) VALUES (%s) "
            "RETURNING abstractid", (abstract,))
        abstractid = self.db_cursor.fetchone()[0]

        # Create a minimal module entry to have a module_ident to work with.
        self.db_cursor.execute("""\
INSERT INTO modules
  (moduleid, portal_type, version, name, created, revised, authors,
   maintainers, licensors,  abstractid, stateid, licenseid, doctype,
   submitter, submitlog, language, parent)
VALUES
  ('m42119', 'Module', '1.1', 'New Version', '2013-09-13 15:10:43.000000+02' ,
   '2013-09-13 15:10:43.000000+02', NULL, NULL, NULL, %s, NULL, 11,
        '', NULL, '', 'en', NULL) RETURNING module_ident""", (abstractid,))
        document_ident = self.db_cursor.fetchone()[0]

        # Insert the resource file
        self.db_cursor.execute("""\
INSERT INTO module_files (module_ident, fileid, filename)
  SELECT %s, fileid, filename FROM module_files
  WHERE module_ident = 3 AND fileid = 6""", (document_ident,))

        # In the typical execution path, the target function
        #   would be using the same cursor, so there would be no
        #   reason to commit. But in this case, a new connection is made.
        self.db_cursor.connection.commit()
        self.call_target(document_ident)

        self.db_cursor.execute(
            "select html from abstracts where abstractid = %s",
            (abstractid,))
        html_abstract = self.db_cursor.fetchone()[0]
        expected = (
            'Image: <span data-type="media"><img '
            'src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/'
            'Figure_01_00_01.jpg" data-media-type="image/jpeg" '
            'alt=""/></span>')
        assert expected in html_abstract


class TestModuleToHtml(BaseTestCase):

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from cnxdb.triggers.transforms.producers import produce_html_for_module
        return produce_html_for_module(self.faux_plpy,
                                       *args, **kwargs)

    def test_cnxml_source_missing(self):
        # Case to test that we catch/raise exceptions when the source
        #   CNXML file for a document can't be found.
        ident, filename = 2, 'index.cnxml'
        self.db_cursor.execute(
            "DELETE FROM module_files "
            "WHERE module_ident = %s AND filename = %s;",
            (ident, filename,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import MissingDocumentOrSource
        with pytest.raises(MissingDocumentOrSource) as exc_info:
            self.call_target(ident, filename)
        exception = exc_info.value

        assert exception.document_ident == ident
        assert exception.filename == filename

    def test_missing_document(self):
        # Case to test that we catch/raise exceptions when the document
        #   can't be found.
        ident, filename = 0, 'index.cnxml'

        from cnxdb.triggers.transforms.producers import MissingDocumentOrSource
        with pytest.raises(MissingDocumentOrSource) as exc_info:
            self.call_target(ident, filename)
        exception = exc_info.value

        assert exception.document_ident == ident
        assert exception.filename == filename

    @pytest.mark.skipif(py3_too_old)
    def test_success(self):
        # Case to test for a successful tranformation of a module from
        #   cnxml to html.
        ident = 2  # m42955

        # Delete module_ident 2 index.cnxml.html
        self.db_cursor.execute("DELETE FROM module_files "
                               "WHERE module_ident = 2 "
                               "AND filename = 'index.cnxml.html'")
        self.db_cursor.connection.commit()
        self.call_target(ident)

        self.db_cursor.execute(
            "SELECT file FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = 'index.cnxml.html');",
            (ident,))
        index_html = self.db_cursor.fetchone()[0][:]

        if sys.version_info >= (3,):
            index_html = index_html.tobytes()

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        assert index_html.find(b'<html') >= 0

    @pytest.mark.skipif(py3_too_old)
    def test_module_transform_remove_index_html(self):
        # Test when overwrite_html is True, the index.cnxml.html is removed
        # from the database before a new one is added

        # Create an index.cnxml.html for module_ident 2
        # Delete module_ident 2 index.cnxml.html
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename = 'index.cnxml.html'")

        self.db_cursor.execute(
            "SELECT fileid "
            "FROM module_files "
            "WHERE filename = 'index.cnxml.html' "
            "AND module_ident != 2 LIMIT 1")
        fileid = self.db_cursor.fetchone()[0]
        self.db_cursor.execute(
            "INSERT INTO module_files "
            "(module_ident, fileid, filename) "
            "VALUES (2, %s, 'index.cnxml.html')", (fileid,))
        self.db_cursor.connection.commit()

        msg = self.call_target(2, overwrite_html=True)

        # Assert there are no error messages
        assert msg is None

        # Check cnxml is transformed to html
        self.db_cursor.execute(
            "SELECT fileid, file FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = 2 "
            "         AND filename = 'index.cnxml.html');")
        index_html_id, index_html = self.db_cursor.fetchone()
        index_html = index_html[:]

        if sys.version_info >= (3,):
            index_html = index_html.tobytes()

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        assert index_html.find(b'<html') >= 0

        # Assert index.html has been replaced
        assert fileid != index_html_id

    @pytest.mark.skipif(py3_too_old)
    def test_module_transform_index_html_exists(self):
        # Test when overwrite_html is False, the index.cnxml.html causes an
        # error when a new one is generated

        # Create an index.cnxml.html for module_ident 2
        # Delete module_ident 2 index.cnxml.html
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename = 'index.cnxml.html'")

        self.db_cursor.execute(
            "SELECT fileid "
            "FROM module_files "
            "WHERE filename = 'index.cnxml.html' "
            "AND module_ident != 2 LIMIT 1")
        fileid = self.db_cursor.fetchone()[0]
        self.db_cursor.execute(
            "INSERT INTO module_files "
            "(module_ident, fileid, filename) "
            "VALUES (2, %s, 'index.cnxml.html')", (fileid,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import IndexFileExistsError

        with pytest.raises(IndexFileExistsError) as exc_info:
            self.call_target(2, overwrite_html=False)

        # Check the error message
        expected_msg = ("One of ('index.cnxml.html',) already "
                        "exists for document 2")
        assert str(exc_info.value) == expected_msg

        # Assert index.cnxml.html is not deleted
        self.db_cursor.execute(
            "SELECT fileid FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = 2 "
            "         AND filename = 'index.cnxml.html');")
        index_html_id = self.db_cursor.fetchone()[0]

        assert fileid == index_html_id

    def _make_document_data_invalid(self, ident=2,
                                    filename='index.cnxml'):
        """Hacks a chunk out of the file given as ``filename``
        at module with the given ``ident``.
        This to ensure a transform failure.
        """
        self.db_cursor.execute(
            "SELECT file from files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = %s);",
            (ident, filename))
        index_cnxml = self.db_cursor.fetchone()[0][:]
        if sys.version_info > (3,):
            index_cnxml = index_cnxml.tobytes()
        # Make a mess of things...
        content = index_cnxml[:600] + index_cnxml[700:]
        payload = (Binary(content), ident, filename,)
        self.db_cursor.execute(
            "UPDATE files SET file = %s "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = %s);",
            payload)
        return ident

    def test_transform_w_invalid_data(self):
        # Case to test for an unsuccessful transformation of a module.
        #   The xml is invalid, therefore the transform cannot succeed.
        ident = self._make_document_data_invalid()

        # Delete ident index.cnxml.html
        self.db_cursor.execute(
            'DELETE FROM module_files WHERE '
            'module_ident = %s AND filename = %s',
            [ident, 'index.cnxml.html'])
        self.db_cursor.connection.commit()

        with pytest.raises(Exception) as exc_info:
            self.call_target(ident)

        exception = exc_info.value
        from lxml.etree import XMLSyntaxError
        assert isinstance(exception, XMLSyntaxError)
        expected_msg = (u"Failed to parse QName 'md:tit47:', "
                        "line 11, column 12")
        assert str(exception).startswith(expected_msg)


# ############### #
#   html->cnxml   #
# ############### #

class TestAbstractToCnxml(BaseTestCase):

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from cnxdb.triggers.transforms.producers import (
            produce_cnxml_for_abstract)
        return produce_cnxml_for_abstract(self.faux_plpy,
                                          *args, **kwargs)

    def test_success(self):
        # Case to test for a successful tranformation of an abstract from
        #   html to cnxml.
        document_ident, abstractid = 2, 2  # m42955
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT abstract FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        abstract = self.db_cursor.fetchone()[0]
        expected = ('A number list: <list list-type="bulleted">'
                    '<item>one</item><item>two</item>'
                    '<item>three</item></list>')
        assert expected in abstract

    def test_success_w_reference(self):
        # Case with an abstract containing an internal reference.
        document_ident, abstractid = 3, 3
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT abstract FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        abstract = self.db_cursor.fetchone()[0]
        expected = 'document="m42092"'
        assert expected in abstract

    def test_success_w_cnxml_root_element(self):
        # Case with an abstract that contains an outter xml element
        #   (e.g. <p>).
        document_ident, abstractid = 4, 4
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT abstract FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        abstract = self.db_cursor.fetchone()[0]
        expected = ('<para>A link to the <link url="http://example.com">'
                    'outside world</link>.</para>')
        assert expected in abstract

    def test_success_w_no_cnxml(self):
        # Case that ensures plaintext abstracts remain unwrapped.
        document_ident, abstractid = 5, 5
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT abstract FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        abstract = self.db_cursor.fetchone()[0]
        expected = 'A rather short plaintext abstract.'
        # Check for no tags.
        assert expected in abstract

    def test_success_w_empty(self):
        # Case that ensures an empty abstract is saved as an empty html
        #   entry.
        document_ident, abstractid = 6, 6
        self.call_target(document_ident)

        self.db_cursor.execute(
            "SELECT abstract FROM abstracts "
            "  WHERE abstractid = %s;",
            (abstractid,))
        abstract = self.db_cursor.fetchone()[0]
        assert abstract == ''

    def test_failure_on_nonexistent_document(self):
        # Case to ensure failure the requested document doesn't exist.
        document_ident = 50

        with pytest.raises(ValueError) as exc_info:
            self.call_target(document_ident)
        exception = exc_info.value
        # Just ensure that we aren't blind when the exception is raised.
        assert str(document_ident) in str(exception)

    def test_failure_on_missing_abstract(self):
        # Case to ensure failure when an abstract is missing.
        document_ident, abstractid = 5, 5
        self.db_cursor.execute(
            "UPDATE modules SET (abstractid) = (null) "
            "WHERE module_ident = %s;",
            (document_ident,))
        self.db_cursor.execute(
            "DELETE FROM abstracts WHERE abstractid = %s;",
            (abstractid,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import MissingAbstract
        with pytest.raises(MissingAbstract):
            self.call_target(document_ident)


class TestModuleToCnxml(BaseTestCase):

    def call_target(self, *args, **kwargs):
        """Call the target function. This wrapping takes care of the
        connection parameters.
        """
        from cnxdb.triggers.transforms.producers import (
            produce_cnxml_for_module)
        return produce_cnxml_for_module(self.faux_plpy,
                                        *args, **kwargs)

    def test_html_source_missing(self):
        # Case to test that we catch/raise exceptions when the source
        #   file for a document can't be found.
        ident, filename = 2, 'index.cnxml.html'
        self.db_cursor.execute(
            "DELETE FROM module_files "
            "WHERE module_ident = %s AND filename = %s;",
            (ident, filename,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import MissingDocumentOrSource
        with pytest.raises(MissingDocumentOrSource) as exc_info:
            self.call_target(ident, filename)
        exception = exc_info.value

        assert exception.document_ident == ident
        assert exception.filename == filename

    def test_missing_document(self):
        # Case to test that we catch/raise exceptions when the document
        #   can't be found.
        ident, filename = 0, 'index.cnxml'

        from cnxdb.triggers.transforms.producers import MissingDocumentOrSource
        with pytest.raises(MissingDocumentOrSource) as exc_info:
            self.call_target(ident, filename)
        exception = exc_info.value

        assert exception.document_ident == ident
        assert exception.filename == filename

    @pytest.mark.skipif(py3_too_old)
    def test_success(self):
        # Case to test for a successful tranformation of a module
        ident = 2  # m42955

        # Delete module_ident 2 index.cnxml.html
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename LIKE %s", ('%.cnxml',))
        self.db_cursor.connection.commit()
        self.call_target(ident)

        self.db_cursor.execute(
            "SELECT file FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = 'index.html.cnxml');",
            (ident,))
        index_cnxml = self.db_cursor.fetchone()[0][:]
        if sys.version_info >= (3,):
            index_cnxml = index_cnxml.tobytes()

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        assert b'<document' in index_cnxml

    @pytest.mark.skipif(py3_too_old)
    def test_module_transform_remove_index_cnxml(self):
        # Test when overwrite is True, the index.html.cnxml is removed
        # from the database before a new one is added

        # Delete module_ident 2 *.cnxml
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        self.db_cursor.execute(
            "INSERT INTO module_files "
            "(module_ident, fileid, filename) "
            "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        self.db_cursor.connection.commit()

        msg = self.call_target(2, overwrite=True)

        # Assert there are no error messages
        assert msg is None

        # Check cnxml is transformed to html
        self.db_cursor.execute(
            "SELECT fileid, file FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = 2 "
            "         AND filename = 'index.html.cnxml');")
        index_cnxml_id, index_cnxml = self.db_cursor.fetchone()
        index_cnxml = index_cnxml[:]
        if sys.version_info >= (3,):
            index_cnxml = index_cnxml.tobytes()

        # We only need to test that the file got transformed and placed
        #   placed in the database, the transform itself should be verified.
        #   independent of this code.
        assert b'<document' in index_cnxml

        # Assert index.cnxml.html has been replaced
        assert fileid != index_cnxml_id

    @pytest.mark.skipif(py3_too_old)
    def test_module_transform_index_html_cnxml_exists(self):
        # Test when overwrite is False, the index.html.cnxml
        # causes an error when a new one is generated

        # Create an index.html.cnxml for module_ident 2
        # Delete module_ident 2 index.html.cnxml
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        self.db_cursor.execute(
            "INSERT INTO module_files "
            "(module_ident, fileid, filename) "
            "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import IndexFileExistsError

        with pytest.raises(IndexFileExistsError) as exc_info:
            self.call_target(2, overwrite=False)

        # Check the error message
        expected_msg = ("One of ('index.html.cnxml', 'index.cnxml') "
                        "already exists for document 2")
        assert str(exc_info.value) == expected_msg

        # Assert index.cnxml.html is not deleted
        self.db_cursor.execute(
            "SELECT fileid FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = 2 "
            "         AND filename = 'index.html.cnxml');")
        index_cnxml_id = self.db_cursor.fetchone()[0]

        assert fileid == index_cnxml_id

    @pytest.mark.skipif(py3_too_old)
    def test_module_transform_index_cnxml_exists(self):
        # Test when overwrite is False, the index.html.cnxml
        # causes an error when a new one is generated

        # Create an index.html.cnxml for module_ident 2
        # Delete module_ident 2 index.cnxml
        self.db_cursor.execute(
            "DELETE FROM module_files WHERE module_ident = 2 "
            "AND filename LIKE %s", ('%.cnxml',))

        fileid = 1
        self.db_cursor.execute(
            "INSERT INTO module_files "
            "(module_ident, fileid, filename) "
            "VALUES (2, %s, 'index.html.cnxml')", (fileid,))
        self.db_cursor.connection.commit()

        from cnxdb.triggers.transforms.producers import IndexFileExistsError

        with pytest.raises(IndexFileExistsError) as exc_info:
            self.call_target(2, overwrite=False)

        # Check the error message
        expected_msg = ("One of ('index.html.cnxml', 'index.cnxml') "
                        "already exists for document 2")
        assert str(exc_info.value) == expected_msg

        # Assert index.cnxml.html is not deleted
        self.db_cursor.execute(
            "SELECT fileid FROM files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = 2 "
            "         AND filename = 'index.html.cnxml');")
        index_cnxml_id = self.db_cursor.fetchone()[0]

        assert fileid == index_cnxml_id

    def _make_document_data_invalid(self, ident, filename):
        """Hacks a chunk out of the file given as ``filename``
        at module with the given ``ident``.
        This to ensure a transform failure.
        """
        self.db_cursor.execute(
            "SELECT file from files "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = %s);",
            (ident, filename))
        file = self.db_cursor.fetchone()[0][:]
        if sys.version_info > (3,):
            file = file.tobytes()
        # Make a mess of things...
        content = file[:600] + file[700:]
        payload = (Binary(content), ident, filename,)
        self.db_cursor.execute(
            "UPDATE files SET file = %s "
            "  WHERE fileid = "
            "    (SELECT fileid FROM module_files "
            "       WHERE module_ident = %s "
            "         AND filename = %s);",
            payload)
        return ident

    def test_transform_w_invalid_data(self):
        # Case to test for an unsuccessful transformation of a module.
        #   The xml is invalid, therefore the transform cannot succeed.
        ident = self._make_document_data_invalid(2, 'index.cnxml.html')

        # Delete ident *.cnxml
        self.db_cursor.execute(
            'DELETE FROM module_files WHERE '
            'module_ident = %s AND filename LIKE %s',
            [ident, '%.cnxml'])
        self.db_cursor.connection.commit()

        with pytest.raises(Exception) as exc_info:
            self.call_target(ident)

        exception = exc_info.value
        from lxml.etree import XMLSyntaxError
        assert isinstance(exception, XMLSyntaxError)
        assert u"attributes construct error, line 2" in str(exc_info.value)
