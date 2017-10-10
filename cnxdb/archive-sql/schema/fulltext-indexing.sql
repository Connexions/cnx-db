-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

CREATE EXTENSION IF NOT EXISTS plxslt;

DROP FUNCTION IF EXISTS xml_to_baretext(xml); -- changinging return type

CREATE OR REPLACE FUNCTION xml_to_baretext(xml) RETURNS text AS $$
<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:cnx="http://cnx.rice.edu/cnxml"
                xmlns:m="http://www.w3.org/1998/Math/MathML"
                xmlns:md4="http://cnx.rice.edu/mdml/0.4"
                xmlns:md="http://cnx.rice.edu/mdml"
                xmlns="http://www.w3.org/1999/xhtml"
                xmlns:xhtml="http://www.w3.org/1999/xhtml"
                xmlns:bib="http://bibtexml.sf.net/"
                >

  <xsl:output method="text" omit-xml-declaration="yes"/>

  <xsl:template match="/">
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="md:*"/>

  <xsl:template match="md4:*"/>

  <xsl:template match="//xhtml:cnx-pi"/>

</xsl:stylesheet>
$$ LANGUAGE xslt;

CREATE OR REPLACE FUNCTION count_lexemes(myident integer, mysearch text)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
WITH lexemes AS (SELECT word, nentry FROM ts_stat('SELECT module_idx FROM modulefti WHERE module_ident = ' || myident)),
     words AS (select regexp_split_to_table(mysearch,' ') AS qwords)
    SELECT SUM(nentry)::bigint FROM lexemes, words WHERE word @@ plainto_tsquery(qwords);
    $function$;


CREATE OR REPLACE FUNCTION count_collated_lexemes (myident int, bookident int, mysearch text) RETURNS bigint
AS $$
WITH lexemes AS (SELECT word, nentry FROM ts_stat('SELECT module_idx FROM collated_fti WHERE item = ' || myident || ' and context = ' || bookident)),
     words AS (select regexp_split_to_table(mysearch,' ') AS qwords)
    SELECT SUM(nentry)::bigint FROM lexemes, words WHERE word @@ plainto_tsquery(qwords);
$$ LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION index_fulltext_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT module_ident FROM modulefti WHERE module_ident = NEW.module_ident);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO modulefti (module_ident, fulltext, module_idx)
        VALUES ( NEW.module_ident, _baretext, _idx_vectors );
    ELSE
      UPDATE modulefti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE module_ident = NEW.module_ident;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_fulltext ON module_files;
CREATE TRIGGER index_fulltext
  AFTER INSERT OR UPDATE ON module_files
    FOR EACH row WHEN (NEW.filename = 'index.cnxml.html')
      EXECUTE PROCEDURE index_fulltext_trigger();

CREATE OR REPLACE FUNCTION index_fulltext_upsert_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
  BEGIN

    IF NEW.fulltext IS NOT NULL THEN
        RETURN NEW;
    END IF;

    has_existing_record := (SELECT module_ident FROM modulefti WHERE module_ident = NEW.module_ident);
    IF has_existing_record IS NULL THEN
        return NEW;
    ELSE
      UPDATE modulefti SET (module_idx) = ( NEW.module_idx)
        WHERE module_ident = NEW.module_ident;
      RETURN NULL;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_fulltext_upsert ON modulefti;
CREATE TRIGGER index_fulltext_upsert
  BEFORE INSERT ON modulefti
    FOR EACH row
      EXECUTE PROCEDURE index_fulltext_upsert_trigger();

CREATE OR REPLACE FUNCTION index_collated_fulltext_trigger()
  RETURNS TRIGGER AS $$
  DECLARE
    has_existing_record integer;
    _baretext text;
    _idx_vectors tsvector;
  BEGIN
    has_existing_record := (SELECT item FROM collated_fti WHERE item = NEW.item and context = NEW.context);
    _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text FROM files AS f WHERE f.fileid = NEW.fileid);
    _idx_vectors := to_tsvector(_baretext);

    IF has_existing_record IS NULL THEN
      INSERT INTO collated_fti (item, context, fulltext, module_idx)
        VALUES ( NEW.item, NEW.context,_baretext, _idx_vectors );
    ELSE
      UPDATE collated_fti SET (fulltext, module_idx) = ( _baretext, _idx_vectors )
        WHERE item = NEW.item and context = NEW.context;
    END IF;
    RETURN NEW;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_collated_fulltext ON collated_file_associations;
CREATE TRIGGER index_collated_fulltext
  AFTER INSERT OR UPDATE ON collated_file_associations
    FOR EACH row
      EXECUTE PROCEDURE index_collated_fulltext_trigger();

CREATE AGGREGATE tsvector_agg (
      BASETYPE = tsvector,
      SFUNC = tsvector_concat,
      STYPE = tsvector,
      INITCOND = ''
    );

CREATE OR REPLACE FUNCTION insert_book_fti(bookid integer)
  RETURNS void
  LANGUAGE sql
    AS $function$
    WITH RECURSIVE t(node, parent, document, path) AS (
        SELECT tr.nodeid, tr.parent_id, tr.documentid, ARRAY[tr.nodeid]
        FROM trees tr
        WHERE tr.documentid = bookid and tr.is_collated = 'False'
      UNION ALL
        SELECT c.nodeid, c.parent_id, c.documentid, path || ARRAY[c.nodeid]
        FROM trees c JOIN t ON c.parent_id = t.node
        WHERE NOT c.nodeid = ANY(t.path)
      )
    INSERT INTO modulefti (module_ident, module_idx)
      SELECT bookid, tsvector_agg(mf.module_idx)
        FROM t JOIN modulefti mf
          ON t.document = mf.module_ident JOIN modules m
          ON t.document = m.module_ident
        WHERE m.portal_type IN ('Module','CompositeModule')
    $function$;

CREATE OR REPLACE FUNCTION index_fulltext_book_trigger()
  RETURNS TRIGGER AS $$
  BEGIN
    DELETE from modulefti WHERE module_ident = NEW.module_ident;
    PERFORM insert_book_fti(NEW.module_ident);
    RETURN NULL;
  END;
  $$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS index_fullext_book ON latest_modules;
CREATE TRIGGER index_fulltext_book
  AFTER INSERT OR UPDATE ON latest_modules
    FOR EACH row WHEN (NEW.portal_type = 'Collection')
      EXECUTE PROCEDURE index_fulltext_book_trigger();
