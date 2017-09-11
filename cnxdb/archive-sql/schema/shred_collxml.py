#!/usr/bin/env python
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""commandline tool for parsing collxml into a DB tree."""


from xml import sax
import sys
import psycopg2

# While the collxml files we process potentially contain many of these
# namespaces, I take advantage of the fact that almost none of the
# localnames (tags names) actually overlap. The one case that does (title)
# actually works in our favor, since we want to treat it the same anyway.

ns = {"cnx": "http://cnx.rice.edu/cnxml",
      "cnxorg": "http://cnx.rice.edu/system-info",
      "md": "http://cnx.rice.edu/mdml",
      "col": "http://cnx.rice.edu/collxml",
      "cnxml": "http://cnx.rice.edu/cnxml",
      "m": "http://www.w3.org/1998/Math/MathML",
      "q": "http://cnx.rice.edu/qml/1.0",
      "xhtml": "http://www.w3.org/1999/xhtml",
      "bib": "http://bibtexml.sf.net/",
      "cc": "http://web.resource.org/cc/",
      "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}

NODE_INS = "INSERT INTO trees (parent_id,documentid,childorder) "\
    "SELECT %s, module_ident, %s from modules WHERE "\
    "moduleid = %s AND version = %s RETURNING nodeid"
NODE_NODOC_INS = "INSERT INTO trees (parent_id,childorder) VALUES (%s, %s) "\
    "RETURNING nodeid"
NODE_TITLE_UPD = "UPDATE trees SET title = %s FROM modules WHERE nodeid = %s "\
    "AND (documentid IS NULL "\
    "OR (documentid = module_ident AND name != %s))"

NODE_TITLE_DOC_UPD = "UPDATE trees set title = %s, documentid = %s where nodeid = %s"
FIND_SAME_SUBCOL = "SELECT m.module_ident from modules m join modules c on m.uuid = uuid5(c.uuid, %s) where m.name = %s  and m.version = %s and c.moduleid = %s and c.version = %s"
FIND_SUBCOL_IDS="SELECT m.moduleid from modules m join modules c on m.uuid = uuid5(c.uuid, %s) where m.name = %s and c.moduleid = %s"
SUBCOL_ACL="""
INSERT INTO document_controls (uuid, licenseid)
SELECT uuid5(m.uuid, %s), dc.licenseid
FROM document_controls dc join modules m on  dc.uuid = m.uuid 
WHERE moduleid = %s and version = %s """
SUBCOL_INS="""
INSERT into modules (portal_type, moduleid, name, uuid,
    abstractid, version, created, revised,
    licenseid, submitter, submitlog, stateid,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style)
SELECT 'SubCollection', 'col'||nextval('collectionid_seq'), %s, uuid5(uuid, %s),
    abstractid, version, created, revised,
    licenseid, submitter, submitlog, stateid,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style
FROM modules WHERE moduleid = %s and version = %s  RETURNING module_ident"""

SUBCOL_NEW_VERSION="""
INSERT into modules (portal_type, moduleid, name, uuid,
    abstractid, version, created, revised,
    licenseid, submitter, submitlog, stateid,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style)
SELECT 'SubCollection', %s, %s, uuid5(uuid, %s),
    abstractid, version, created, revised,
    licenseid, submitter, submitlog, stateid,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style
FROM modules WHERE moduleid = %s and version = %s  RETURNING module_ident"""

con = psycopg2.connect('dbname=repository')
cur = con.cursor()


def _do_insert(pid, cid, oid=0, ver=0):
    if oid:
        cur.execute(NODE_INS, (pid, cid, oid, ver))
        if cur.rowcount == 0:  # no documentid found
            cur.execute(NODE_NODOC_INS, (pid, cid))
    else:
        cur.execute(NODE_NODOC_INS, (pid, cid))
    res = cur.fetchall()
    if res:
        nodeid = res[0][0]
    else:
        nodeid = None
    return nodeid


def _get_subcol(title,oid,ver):
    res = cur.execute(FIND_SAME_SUBCOL, (title, oid, ver))
    if not res.nrows():
        res = cur.execute(FIND_SUBCOL_IDS, (title, oid))
        if not res.nrows():
            cur.execute(SUBCOL_ACL, (title, oid, ver))
            res = cur.execute(SUBCOL_INS, (title, oid, ver))
        else:
            res = cur.execute(SUBCOL_NEW_VERSION,
                     (title, oid, ver, res[0]['moduleid']))
    return res[0]["module_ident"]


def _do_update(title, nid, docid):
    if docid:
        cur.execute(NODE_TITLE_DOC_UPD, (title, docid, nid))
    else:
        cur.execute(NODE_TITLE_UPD, (title,nid))


class ModuleHandler(sax.ContentHandler):
    """Handler for module link."""

    def __init__(self):
        """Create module handler with default values."""
        self.parents = [None]
        self.childorder = 0
        self.map = {}
        self.tag = u''
        self.contentid = u''
        self.version = u''
        self.title = u''
        self.nodeid = 0
        self.derivedfrom = [None]
        self.titled = [None]

    def startElementNS(self, (uri, localname), qname, attrs):
        """Handle element."""
        self.map[localname] = u''
        self.tag = localname

        if localname == 'module':
            self.titled.append(localname)
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1], self.childorder[-1],
                                attrs[(None, "document")],
                                attrs[(ns["cnxorg"],
                                      "version-at-this-collection-version")])
            if nodeid:
                self.nodeid = nodeid

        elif localname == 'subcollection':
            self.titled.append(localname)
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1], self.childorder[-1])
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'derived-from':
            self.derivedfrom.append(True)

    def characters(self, content):
        """Copy characters to tag."""
        self.map[self.tag] += content

    def endElementNS(self, (uris, localname), qname):
        """Assign local values."""
        if localname == 'content-id' and not self.derivedfrom[-1]:
            self.contentid = self.map[localname]
        elif localname == 'version' and not self.derivedfrom[-1]:
            self.version = self.map[localname]
        elif localname == 'title' and not self.derivedfrom[-1]:
            self.title = self.map[localname]
            if self.titled[-1] in ('subcollection', 'module'):
                my_title  = self.title.encode('utf-8')
                mod_id = None
                if self.titled[-1] == 'subcollection': #  we are in a subcollection
                    mod_id = _get_subcol(self.title.encode('utf-8'), self.contentid, self.version)
                _do_update(my_title, self.nodeid, mod_id)

        elif localname == 'derived-from':
            self.derivedfrom.pop()

        elif localname == 'metadata':
            # We know that at end of metadata, we've got the collection info
            self.childorder = [0]
            nodeid = _do_insert(None, self.childorder[-1],
                                self.contentid, self.version)
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'content':
            # this occurs at the end of each container class:
            # either colletion or subcollection
            self.parents.pop()
            self.childorder.pop()

        elif localname in ('module', 'subcollection'):
            self.titled.pop()


parser = sax.make_parser()
parser.setFeature(sax.handler.feature_namespaces, 1)
parser.setContentHandler(ModuleHandler())
parser.parse(open(sys.argv[1]))

con.commit()
