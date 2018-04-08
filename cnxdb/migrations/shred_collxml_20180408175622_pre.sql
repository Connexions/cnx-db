-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

create or replace function shred_collxml (doc text, bookid int) returns void
as $$

from xml import sax

# While the collxml files we process potentially contain many of these
# namespaces, I take advantage of the fact that almost none of the
# localnames (tags names) actually overlap. The one case that does (title)
# actually works in our favor, since we want to treat it the same anyway.

ns = { "cnx":"http://cnx.rice.edu/cnxml",
       "cnxorg":"http://cnx.rice.edu/system-info",
       "md":"http://cnx.rice.edu/mdml",
       "col":"http://cnx.rice.edu/collxml",
       "cnxml":"http://cnx.rice.edu/cnxml",
       "m":"http://www.w3.org/1998/Math/MathML",
       "q":"http://cnx.rice.edu/qml/1.0",
       "xhtml":"http://www.w3.org/1999/xhtml",
       "bib":"http://bibtexml.sf.net/",
       "cc":"http://web.resource.org/cc/",
       "rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#"
}

FIND_BOOK_META=plpy.prepare("""
    SELECT * FROM modules WHERE module_ident = $1""", ("int",))
NODE_INS=plpy.prepare("""
INSERT INTO trees (parent_id, documentid, childorder)
    SELECT $1, module_ident, $2
    FROM modules WHERE moduleid = $3 AND version = $4
    RETURNING nodeid""", ("int","int","text","text"))
NODE_DOC_INS=plpy.prepare("INSERT INTO trees"
    " (parent_id, documentid, childorder)"
        " VALUES (NULL, $1, 0) returning nodeid", ("int",))
NODE_NODOC_INS=plpy.prepare("INSERT INTO trees (parent_id, childorder)"
    " VALUES ($1, $2) returning nodeid", ("int","int"))
NODE_TITLE_UPD=plpy.prepare("UPDATE trees SET title = $1"
    " FROM modules WHERE nodeid = $2 AND"
    " (documentid IS NULL OR"
        " (documentid = module_ident AND NAME != $1))", ("text","int"))
NODE_TITLE_DOC_UPD=plpy.prepare("UPDATE trees set title = $1, documentid = $2"
    " WHERE nodeid = $3", ("text", "int", "int"))
FIND_SAME_SUBCOL=plpy.prepare("SELECT m.module_ident FROM"
    " modules m JOIN modules c ON m.uuid = uuid5(c.uuid, $1)"
    " JOIN trees t on c.module_ident = t.documentid"
        " WHERE m.name = $1"
            " AND m.major_version = $2"
            " AND m.minor_version = $3"
            " AND t.nodeid = $4", ("text","int", "int", "int"))
FIND_SUBCOL_IDS=plpy.prepare("SELECT m.moduleid FROM"
    " modules m JOIN modules c ON m.uuid = uuid5(c.uuid, $1)"
    " JOIN trees t on c.module_ident = t.documentid"
        " WHERE m.name = $1"
            " AND t.nodeid = $2", ("text","int"))
SUBCOL_ACL=plpy.prepare("""
INSERT INTO document_controls (uuid, licenseid)
SELECT uuid5(m.uuid, $1), dc.licenseid
FROM document_controls dc join modules m on  dc.uuid = m.uuid 
JOIN trees t on m.module_ident = t.documentid
WHERE nodeid = $2""", ("text","int"))
SUBCOL_INS=plpy.prepare("""
INSERT into modules (portal_type, moduleid, name, uuid,
    abstractid, version, created, revised,
    licenseid, submitter, submitlog,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style)
SELECT 'SubCollection', 'col'||nextval('collectionid_seq'), $1, uuid5(uuid, $1),
    abstractid, version, created, revised,
    licenseid, submitter, submitlog,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style
FROM modules JOIN trees on module_ident = documentid
WHERE nodeid = $2  RETURNING module_ident""", ("text","int"))

SUBCOL_NEW_VERSION=plpy.prepare("""
INSERT into modules (portal_type, moduleid, name, uuid,
    abstractid, version, created, revised,
    licenseid, submitter, submitlog,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style)
SELECT 'SubCollection', $3, $1, uuid5(uuid, $1),
    abstractid, version, created, revised,
    licenseid, submitter, submitlog,
    parent, language, doctype,
    authors, maintainers, licensors, parentauthors,
    major_version, minor_version, print_style
FROM modules JOIN trees on module_ident = documentid
WHERE nodeid = $2 RETURNING module_ident""", ("text","int","text"))

def _do_insert(pid,cid,oid=0,ver=0):
    if pid is None:
        res = plpy.execute(NODE_DOC_INS,(bookid,))
    elif oid:
        res = plpy.execute(NODE_INS,(pid,cid,oid,ver))
        if res.nrows() == 0: # no documentid found
            plpy.execute(NODE_NODOC_INS,(pid,cid))
    else:
        res = plpy.execute(NODE_NODOC_INS,(pid,cid))
    if res.nrows():
        nodeid=res[0]["nodeid"]
    else:
        nodeid = None
    return nodeid

def _get_subcol(title, maj_ver, min_ver, parent_nodeid):
    res = plpy.execute(FIND_SAME_SUBCOL, (title, maj_ver, min_ver, parent_nodeid))
    if not res.nrows():
        res = plpy.execute(FIND_SUBCOL_IDS, (title, parent_nodeid))
        if not res.nrows():
            plpy.execute(SUBCOL_ACL, (title, parent_nodeid))
            res = plpy.execute(SUBCOL_INS, (title, parent_nodeid))
        else:
            res = plpy.execute(SUBCOL_NEW_VERSION,
                     (title, parent_nodeid, res[0]["moduleid"]))
    return res[0]["module_ident"]

def _do_update(title,nid, docid):
    if docid:
        plpy.execute(NODE_TITLE_DOC_UPD, (title, docid, nid))
    else:
        plpy.execute(NODE_TITLE_UPD, (title, nid))

class ModuleHandler(sax.ContentHandler):
    def __init__(self, bookid):
        res = plpy.execute(FIND_BOOK_META, (bookid,))
        self.parents = [None]
        self.childorder = 0
        self.map = {}
        self.tag = u''
        self.contentid = res[0]["moduleid"]
        self.version = res[0]["version"]
        self.major_version = res[0]["major_version"]
        self.minor_version = res[0]["minor_version"]
        self.title = res[0]["name"]
        self.nodeid = 0
        self.derivedfrom = [None]
        self.titled = [None]

    def startElementNS(self, (uri, localname), qname, attrs):
        self.map[localname] = u''
        self.tag = localname

        if localname == 'module':
            self.titled.append(localname)
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1],attrs[(None,"document")],attrs[(ns["cnxorg"],"version-at-this-collection-version")])
            if nodeid:
                self.nodeid = nodeid

        elif localname == 'subcollection':
            self.titled.append(localname)
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1])
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'derived-from':
            self.derivedfrom.append(True)

    def characters(self,content):
        self.map[self.tag] += content

    def endElementNS(self, (uris, localname), qname):
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
                    # Our parent is up two, since we pushed our nodeid on the parents stack at startElement
                    mod_id = _get_subcol(self.title.encode('utf-8'), self.major_version, self.minor_version, self.parents[-2])
                _do_update(my_title, self.nodeid, mod_id)

        elif localname == 'derived-from':
            self.derivedfrom.pop()

        elif localname == 'metadata':
            # We know that at end of metadata, we have got the collection info
            self.childorder = [0]
            nodeid = _do_insert(None, 0)
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'content':
            #  this occurs at the end of each container class: collection or subcol.
            self.parents.pop()
            self.childorder.pop()

        elif localname in ('module', 'subcollection'):
            self.titled.pop()

parser = sax.make_parser()
parser.setFeature(sax.handler.feature_namespaces, 1)
parser.setContentHandler(ModuleHandler(bookid))

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

parser.parse(StringIO(doc))
$$
language plpythonu;

create or replace function shred_collxml (fid int, docid int, force bool default False) returns void as
$$
select shred_collxml(convert_from(file,'UTF8'), docid) from files where fileid = fid
    and (force or not exists (
       select 1 from trees where documentid = docid and parent_id is null))
$$ language sql;

create or replace function shred_collxml_trigger () returns trigger as $$
BEGIN
PERFORM shred_collxml(NEW.fileid, NEW.module_ident);
RETURN NEW;
END;
$$
LANGUAGE plpgsql;

drop trigger if exists shred_collxml on module_files;

create trigger shred_collxml BEFORE INSERT on module_files
for each row when (NEW.filename = 'collection.xml') execute procedure shred_collxml_trigger ();
