# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute("""
    CREATE OR REPLACE FUNCTION index_fulltext_trigger()
      RETURNS TRIGGER AS $$
      DECLARE
        has_existing_record integer;
        _baretext text;
        _keyword text;
        _title text;
        _idx_text_vectors tsvector;
        _idx_title_vectors tsvector;
        _idx_keyword_vectors tsvector;

      BEGIN
        has_existing_record := (SELECT module_ident FROM modulefti WHERE module_ident = NEW.module_ident);
        _baretext := (SELECT xml_to_baretext(convert_from(f.file, 'UTF8')::xml)::text
                      FROM files AS f WHERE f.fileid = NEW.fileid);
        _keyword := (SELECT k.word FROM keywords k INNER JOIN modulekeywords m
                     ON k.keywordid = m.keywordid
                     AND m.module_ident = NEW.module_ident);
        _title := (SELECT modules.name FROM modules WHERE module_ident = NEW.module_ident);
        _idx_title_vectors := setweight(to_tsvector(COALESCE(_title, '')), 'A');
        _idx_keyword_vectors := setweight(to_tsvector(COALESCE(_keyword, '')), 'B');
        _idx_text_vectors := setweight(to_tsvector(COALESCE(_baretext, '')), 'C');

        IF has_existing_record IS NULL THEN
          INSERT INTO modulefti (module_ident, fulltext, module_idx)
            VALUES ( NEW.module_ident, _baretext, _idx_title_vectors || _idx_keyword_vectors || _idx_text_vectors);

        ELSE
          UPDATE modulefti
            SET (fulltext, module_idx) = (_baretext, _idx_title_vectors || _idx_keyword_vectors || _idx_text_vectors)
              WHERE module_ident = NEW.module_ident;
        END IF;
        RETURN NEW;
      END;
      $$
      LANGUAGE plpgsql;
      """)


def down(cursor):
    cursor.execute("""
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
      """)