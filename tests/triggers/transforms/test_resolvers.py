# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2014-2017, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import subprocess
import io
import sys

import pytest
from lxml import etree
# XXX (2017-10-12) deps-on-cnx-archive: Depends on cnx-archive
from cnxarchive.config import TEST_DATA_DIRECTORY


def py3_too_old(*args):
    if sys.version_info >= (3,) and os.path.exists('/usr/bin/python3'):
        out = subprocess.check_output(['/usr/bin/python3', '--version'])
        return out < b'Python 3.4'


class BaseTestCase(object):

    @pytest.fixture(autouse=True)
    def suite_fixture(self, xxx_archive_data, faux_plpy, db_cursor):
        self.faux_plpy = faux_plpy
        self.db_cursor = db_cursor


class TestHtmlReferenceResolution(BaseTestCase):

    @property
    def target(self):
        from cnxdb.triggers.transforms.resolvers import resolve_cnxml_urls
        return resolve_cnxml_urls

    def test_reference_rewrites(self):
        # Case to test that a document's internal references have
        #   been rewritten to the cnx-archive's read-only API routes.
        ident = 3
        from cnxdb.triggers.transforms.converters import cnxml_to_full_html
        content_filepath = os.path.join(TEST_DATA_DIRECTORY,
                                        'm42119-1.3-modified.cnxml')
        with open(content_filepath, 'r') as fb:
            content = cnxml_to_full_html(fb.read())
            content = io.BytesIO(content.encode('utf-8'))
            content, bad_refs = self.target(content, self.faux_plpy, ident)

        # Read the content for the reference changes.
        expected_img_ref = (
            b'<img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/'
            b'Figure_01_00_01.jpg" data-media-type="image/jpg" '
            b'alt="The spiral galaxy Andromeda is shown."/>')
        assert expected_img_ref in content
        expected_internal_ref = (
            b'<a href="/contents/209deb1f-1a46-4369-9e0d-18674cf58a3e@7">')
        assert expected_internal_ref in content
        expected_resource_ref = (
            b'<a href="/resources/'
            b'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg">')
        assert expected_resource_ref in content

    def test_reference_not_parseable(self):
        ident = 3
        from cnxdb.triggers.transforms.converters import cnxml_to_full_html
        content_filepath = os.path.join(TEST_DATA_DIRECTORY,
                                        'm45070.cnxml')
        with open(content_filepath, 'r') as fb:
            content = cnxml_to_full_html(fb.read())
        content = io.BytesIO(content.encode('utf-8'))
        content, bad_refs = self.target(content, self.faux_plpy, ident)

        assert sorted(bad_refs) == [
            "Invalid reference value: document=3, reference=/m",
            ("Missing resource with filename 'InquiryQuestions.svg', "
             "moduleid None version None.: document=3, "
             "reference=InquiryQuestions.svg"),
            ("Unable to find a reference to 'm43540' at version 'None'.: "
             "document=3, reference=/m43540"),
        ]
        assert b'<a href="/m">' in content

    def test_reference_resolver(self):
        html = io.BytesIO(b'''\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/m42092#xn">
            <img src="Figure_01_00_01.jpg"/>
        </a>
        <a href="/ m42709@1.4">
            <img src="/Figure_01_00_01.jpg"/>
        </a>
        <a href="/m42092/latest?collection=col11406/latest#figure">
            Module link with collection
        </a>
        <a href="/m42955/latest?collection=col11406/1.6">
            Module link with collection and version
        </a>
        <img src=" Figure_01_00_01.jpg"/>
        <img src="/content/m42092/latest/PhET_Icon.png"/>
        <img src="/content/m42092/1.4/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="Figure_01_00_01.jpg"/>

        <audio src="Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"></audio>

        <video src="Figure_01_00_01.jpg" id="music" mime-type="video/mp4"></video>

        <object width="400" height="400" data="Figure_01_00_01.jpg"></object>

        <object width="400" height="400">
            <embed src="Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>''')  # noqa: E501

        html, bad_references = self.target(
            html,
            self.faux_plpy,
            document_ident=3)
        self.db_cursor.connection.commit()

        assert bad_references == [
            ("Missing resource with filename 'PhET_Icon.png', "
             "moduleid m42092 version 1.3.: document=3, "
             "reference=PhET_Icon.png")
        ]
        assert html == b'''\
<html xmlns="http://www.w3.org/1999/xhtml">
    <body>
        <a href="/contents/d395b566-5fe3-4428-bcb2-19016e3aa3ce#xn">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/ae3e18de-638d-4738-b804-dc69cd4db3a3@4">
            <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597:d395b566-5fe3-4428-bcb2-19016e3aa3ce#figure">
            Module link with collection
        </a>
        <a href="/contents/e79ffde3-7fb4-4af3-9ec8-df648b391597@6.2:209deb1f-1a46-4369-9e0d-18674cf58a3e">
            Module link with collection and version
        </a>
        <img src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/resources/075500ad9f71890a85fe3f7a4137ac08e2b7907c/PhET_Icon.png"/>
        <img src="/content/m42092/1.3/PhET_Icon.png"/>
        <span data-src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <audio src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="audio/mpeg"/>

        <video src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" id="music" mime-type="video/mp4"/>

        <object width="400" height="400" data="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>

        <object width="400" height="400">
            <embed src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg"/>
        </object>

        <audio controls="controls">
            <source src="/resources/d47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9/Figure_01_00_01.jpg" type="audio/mpeg"/>
        </audio>
    </body>
</html>'''  # noqa: E501

    def test_get_resource_info(self):
        from cnxdb.triggers.transforms.resolvers import (
            CnxmlToHtmlReferenceResolver as ReferenceResolver,
            ReferenceNotFound,
        )

        resolver = ReferenceResolver(io.BytesIO(b'<html></html>'),
                                     self.faux_plpy, 3)

        # Test file not found
        with pytest.raises(ReferenceNotFound):
            resolver.get_resource_info('PhET_Icon.png')

        # Test getting a file in module 3
        expected_info = {'hash': 'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9',
                         'id': 6}
        resource_info = resolver.get_resource_info('Figure_01_00_01.jpg')
        assert resource_info == expected_info

        # Test file not found outside of module 3
        with pytest.raises(ReferenceNotFound):
            resolver.get_resource_info('PhET_Icon.png', document_id='m42955')

        # Test getting a file in another module
        expected_info = {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c',
                         'id': 23}
        resource_info = resolver.get_resource_info('PhET_Icon.png',
                                                   document_id='m42092')
        assert resource_info == expected_info

        # Test file not found with version
        with pytest.raises(ReferenceNotFound):
            resolver.get_resource_info('PhET_Icon.png',
                                       document_id='m42092',
                                       version='1.3')

        # Test getting a file with version
        expected_info = {'hash': '075500ad9f71890a85fe3f7a4137ac08e2b7907c',
                         'id': 23}
        resource_info = resolver.get_resource_info('PhET_Icon.png',
                                                   document_id='m42092',
                                                   version='1.4')
        assert resource_info == expected_info

    def test_parse_reference(self):
        from cnxdb.triggers.transforms.resolvers import (
            MODULE_REFERENCE, RESOURCE_REFERENCE,
            parse_legacy_reference as parse_reference,
        )

        expected = (MODULE_REFERENCE, ('m12345', None, None, None, ''))
        assert parse_reference('/m12345') == expected

        expected = (MODULE_REFERENCE, ('m12345', None, None, None, ''))
        assert parse_reference('/content/m12345') == expected

        expected = (MODULE_REFERENCE, ('m12345', None, None, None, ''))
        assert parse_reference('http://cnx.org/content/m12345') == expected

        # m10278 "The Advanced CNXML"
        expected = (MODULE_REFERENCE, ('m9007', None, None, None, ''))
        assert parse_reference('/m9007') == expected

        # m11374 "KCL"
        expected = (MODULE_REFERENCE, ('m0015', None, None, None, '#current'))
        assert parse_reference('/m0015#current') == expected

        # m11351 "electron and hole density equations"
        expected = (MODULE_REFERENCE, ('m11332', None, None, None, '#ntypeq'))
        assert parse_reference('/m11332#ntypeq') == expected

        # m19809 "Gavin Bakers entry..."
        expected = (MODULE_REFERENCE, ('m19770', None, None, None, ''))
        assert parse_reference('/ m19770') == expected

        # m16562 "Flat Stanley.pdf"
        expected = (RESOURCE_REFERENCE, ('Flat Stanley.pdf', None, None))
        assert parse_reference(' Flat Stanley.pdf') == expected

        # m34830 "Auto_fatalities_data.xls"
        expected = (RESOURCE_REFERENCE,
                    ('Auto_fatalities_data.xls', None, None))
        assert parse_reference('/Auto_fatalities_data.xls') == expected

        # m35999 "version 2.3 of the first module"
        expected = (MODULE_REFERENCE, ('m0000', '2.3', None, None, ''))
        assert parse_reference('/m0000@2.3') == expected

        # m14396 "Adding a Table..."
        # m11837
        # m37415
        # m37430
        # m10885
        ref = '/content/m19610/latest/eip-edit-new-table.png'
        expected = (RESOURCE_REFERENCE,
                    ('eip-edit-new-table.png', 'm19610', None))
        assert parse_reference(ref) == expected

        # m45070
        assert parse_reference('/m') == (None, ())

        # m45136 "legacy format"
        ref = ('http://cnx.org/content/m48897/latest'
               '?collection=col11441/latest')
        expected = (MODULE_REFERENCE, ('m48897', None, 'col11441', None, ''))
        assert parse_reference(ref) == expected
        ref = 'http://cnx.org/content/m48897/1.2?collection=col11441/1.10'
        expected = (MODULE_REFERENCE,
                    ('m48897', '1.2', 'col11441', '1.10', ''))
        assert parse_reference(ref) == expected
        ref = ('http://cnx.org/content/m48897/1.2?collection=col11441/1.10'
               '#figure')
        expected = (MODULE_REFERENCE,
                    ('m48897', '1.2', 'col11441', '1.10', '#figure'))
        assert parse_reference(ref) == expected

        # legacy.cnx.org links
        ref = 'http://legacy.cnx.org/content/m48897/latest'
        assert parse_reference(ref) == (None, ())

        ref = ('http://legacy.cnx.org/content/m48897/latest'
               '?collection=col11441/latest')
        assert parse_reference(ref) == (None, ())

    @pytest.mark.skipif(py3_too_old)
    def test_get_page_ident_hash(self):
        book_uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        book_version = '7.1'
        page_uuid = '209deb1f-1a46-4369-9e0d-18674cf58a3e'
        page_version = '7'

        self.db_cursor.execute(
            '''\
CREATE FUNCTION test_get_page_ident_hash() RETURNS TEXT AS $$
import io

import plpy

from cnxdb.triggers.transforms.resolvers import (
    CnxmlToHtmlReferenceResolver)

resolver = CnxmlToHtmlReferenceResolver(io.BytesIO(b'<html></html>'), plpy, 3)
result = resolver.get_page_ident_hash(%s, %s, %s, %s)
return result[1]
$$ LANGUAGE plpythonu;
SELECT test_get_page_ident_hash();''',
            (page_uuid, page_version, book_uuid, book_version))
        expected = '{}@{}:{}@{}'.format(book_uuid,
                                        book_version,
                                        page_uuid,
                                        page_version)
        assert self.db_cursor.fetchone()[0] == expected


class TestCnxmlReferenceResolution(BaseTestCase):

    @property
    def target(self):
        from cnxdb.triggers.transforms.resolvers import resolve_html_urls
        return resolve_html_urls

    @property
    def target_cls(self):
        from cnxdb.triggers.transforms.resolvers import (
            HtmlToCnxmlReferenceResolver)
        return HtmlToCnxmlReferenceResolver

    def test_parse_reference(self):
        from cnxdb.triggers.transforms.resolvers import (
            DOCUMENT_REFERENCE, BINDER_REFERENCE,
            RESOURCE_REFERENCE,
            parse_html_reference as parse_reference,
        )

        title = "Something about nothing"
        id = '49f43184-728f-445f-b669-abda618ab8f4'
        ver = '155'
        id2 = 'ab107da9-84bb-4e3c-95e1-30cff398827a'
        ver2 = '5.1'  # used for binder
        sha1 = '0300e7c72015f9bfe30c3cb2d5e8da12a6fbb6f8'

        # *** Matching legacy
        ref = 'http://legacy.cnx.org/content/m48897/latest'
        assert parse_reference(ref) == (None, ())
        ref = ('http://legacy.cnx.org/content/m48897/latest?'
               'collection=col11441/latest')
        assert parse_reference(ref) == (None, (),)

        # *** Matching documents
        expected = (DOCUMENT_REFERENCE, (id, None, '',))
        assert parse_reference('/contents/{}'.format(id)) == expected

        expected = (DOCUMENT_REFERENCE, (id, ver, '',))
        assert parse_reference('/contents/{}@{}'.format(id, ver)) == expected

        # With a fragment...
        ref = '/contents/{}/{}'.format(id, title)
        expected = (DOCUMENT_REFERENCE, (id, None, '/{}'.format(title),))
        assert parse_reference(ref) == expected

        ref = '/contents/{}@{}/{}'.format(id, ver, title)
        expected = (DOCUMENT_REFERENCE, (id, ver, '/{}'.format(title),))
        assert parse_reference(ref) == expected

        ref = '/contents/{}#current'.format(id)
        expected = (DOCUMENT_REFERENCE, (id, None, '#current',))
        assert parse_reference(ref) == expected

        ref = '/contents/{}/{}#current'.format(id, title)
        expected = (DOCUMENT_REFERENCE,
                    (id, None, '/{}#current'.format(title),))
        assert parse_reference(ref) == expected

        # *** Binder with document
        ref = '/contents/{}@{}:{}@{}'.format(id, ver2, id2, ver)
        expected = (BINDER_REFERENCE,
                    (id, ver2, '{}@{}'.format(id2, ver), '',))
        assert parse_reference(ref) == expected

        ref = '/contents/{}@{}:{}'.format(id, ver2, id2)
        expected = (BINDER_REFERENCE, (id, ver2, id2, '',))
        assert parse_reference(ref) == expected

        # With a fragement...
        ref = '/contents/{}@{}:{}/{}'.format(id, ver2, id2, title)
        expected = (BINDER_REFERENCE, (id, ver2, id2, '/{}'.format(title),))
        assert parse_reference(ref) == expected

        ref = '/contents/{}@{}:{}@{}/{}'.format(id, ver2, id2, ver, title)
        expected = (BINDER_REFERENCE,
                    (id, ver2, '{}@{}'.format(id2, ver),
                     '/{}'.format(title),))
        assert parse_reference(ref) == expected

        # *** Matching resource
        ref = '../resources/{}'.format(sha1)  # ideal url syntax
        expected = (RESOURCE_REFERENCE, (sha1, '',))
        assert parse_reference(ref) == expected

        ref = '/resources/{}'.format(sha1)  # not ideal, but could happen
        expected = (RESOURCE_REFERENCE, (sha1, '',))
        assert parse_reference(ref) == expected

        # With fragments...
        ref = '../resources/{}/{}.pdf'.format(sha1, title)
        expected = (RESOURCE_REFERENCE, (sha1, '/{}.pdf'.format(title),))
        assert parse_reference(ref) == expected

        # *** Matching cnx.org
        ref = 'http://cnx.org/contents/{}'.format(id)
        expected = (DOCUMENT_REFERENCE, (id, None, ''))
        assert parse_reference(ref) == expected

        # *** Incomplete UUID
        ref = '/contents/{}'.format(id[:-8])
        assert parse_reference(ref) == (None, ())

    def test_reference_rewrites(self):
        # Case to test that a document's internal references have
        #   been rewritten to legacy's read-only API routes.
        ident = 3
        from cnxdb.triggers.transforms.converters import html_to_full_cnxml
        content_filepath = os.path.join(TEST_DATA_DIRECTORY,
                                        'm99999-1.1.html')
        with open(content_filepath, 'r') as fb:
            content = html_to_full_cnxml(fb.read())
            content = io.BytesIO(content)
            content, bad_refs = self.target(content, self.faux_plpy, ident)

        cnxml_etree = etree.parse(io.BytesIO(content))
        nsmap = cnxml_etree.getroot().nsmap.copy()
        nsmap['c'] = nsmap.pop(None)

        # Ensure the module-id has been set.
        expected_module_id = b'module-id="m42119"'
        assert expected_module_id in content

        # Read the content for the reference changes.
        # Check the links
        expected_ref = b'<link document="m41237" version="1.1">'
        assert expected_ref in content
        expected_resource_ref = b'<link resource="Figure_01_00_01.jpg">'
        assert expected_resource_ref in content

        def find_elm(xpath):
            """Find the first elmement by xpath
            and return it as an xml string

            """
            query_result = cnxml_etree.xpath(xpath, namespaces=nsmap)[0]
            return etree.tostring(query_result)

        # Check the media/image tags...
        expected_img_thumbnail_ref = b'thumbnail="Figure_01_00_01.jpg"'
        xpath = '//*[@id="image-w-thumbnail"]'
        assert expected_img_thumbnail_ref in find_elm(xpath)

        expected_img_src_ref = b'src="Figure_01_00_01.jpg"'
        xpath = '//*[@id="image-w-thumbnail"]'
        assert expected_img_src_ref in find_elm(xpath)

        # Check the media/video & media/audio tags...
        expected_ref = b'src="Figure_01_00_01.jpg"'
        xpath = '//*[@id="video-n-audio"]/c:video'
        assert expected_ref in find_elm(xpath)
        xpath = '//*[@id="video-n-audio"]/c:audio'
        assert expected_ref in find_elm(xpath)

        # Check the flash tag.
        expected_ref = b'src="Figure_01_00_01.jpg"'
        xpath = '//*[@id="object-embed"]/c:flash'
        assert expected_ref in find_elm(xpath)

        # Check the java-applet tag.
        expected_ref = b'src="Figure_01_00_01.jpg"'
        xpath = '//*[@id="java-applet"]/c:java-applet'
        assert expected_ref in find_elm(xpath)

        # Check bad reference was not transformed.
        expected_ref = b'<link>indkoeb.jpg</link>'
        assert expected_ref in content

    def test_fix_module_id_fails(self):
        from cnxdb.triggers.transforms.resolvers import ReferenceNotFound

        content = b"""\
<document xmlns="http://cnx.rice.edu/cnxml">
<content><para>hi.</para></content>
</document>"""
        # Note, no ident was given.
        resolver = self.target_cls(io.BytesIO(content),
                                   self.faux_plpy, None)
        problems = resolver.fix_module_id()
        assert len(problems) == 1
        assert type(problems[0]) == ReferenceNotFound

        # Note, an invalid ident was given.
        resolver = self.target_cls(io.BytesIO(content),
                                   self.faux_plpy, 789321)
        problems = resolver.fix_module_id()
        assert len(problems) == 1
        assert type(problems[0]) == ReferenceNotFound

    def test_reference_not_parsable(self):
        ident = 3
        from cnxdb.triggers.transforms.converters import html_to_full_cnxml
        content_filepath = os.path.join(TEST_DATA_DIRECTORY,
                                        'm99999-1.1.html')
        with open(content_filepath, 'r') as fb:
            content = html_to_full_cnxml(fb.read())
        content = io.BytesIO(content)
        content, bad_refs = self.target(content, self.faux_plpy, ident)

        expected_bad_refs = [
            ("Invalid reference value: document=3, "
             "reference=/contents/42ae45b/hello-world"),
            ("Missing resource with hash: "
             "0f3da0de61849a47f77543c383d1ac621b25e6e0: "
             "document=3, reference=None"),
            ("Unable to find a reference to "
             "'c44477a6-1278-433a-ba1e-5a21c8bab191' at version 'None'.: "
             "document=3, reference=/contents/"
             "c44477a6-1278-433a-ba1e-5a21c8bab191@12"),
        ]
        assert sorted(bad_refs) == expected_bad_refs

        # invalid ref still in the content?
        assert b'<link url="/contents/42ae45b/hello-world">' in content

    def test_get_resource_filename(self):
        from cnxdb.triggers.transforms.resolvers import (
            HtmlToCnxmlReferenceResolver as ReferenceResolver,
            ReferenceNotFound,
        )

        resolver = ReferenceResolver(io.BytesIO(b'<html></html>'),
                                     self.faux_plpy, 3)

        # Test file not found
        with pytest.raises(ReferenceNotFound):
            resolver.get_resource_filename('PhET_Icon.png')

        # Test getting a file in module 3
        file_hash = 'd47864c2ac77d80b1f2ff4c4c7f1b2059669e3e9'
        found_filename = resolver.get_resource_filename(file_hash)
        assert found_filename == 'Figure_01_00_01.jpg'

        # Test file not found outside of module 3
        with pytest.raises(ReferenceNotFound):
            resolver.get_resource_filename(
                '075500ad9f71890a85fe3f7a4137ac08e2b7907c')

        # Test getting a file in another module
        resolver.document_ident = 4
        found_filename = resolver.get_resource_filename(
            '075500ad9f71890a85fe3f7a4137ac08e2b7907c')
        assert found_filename == 'PhET_Icon.png'

        # Test getting a file without an ident.
        resolver.document_ident = None
        found_filename = resolver.get_resource_filename(
            '075500ad9f71890a85fe3f7a4137ac08e2b7907c')
        assert found_filename == 'PhET_Icon.png'
