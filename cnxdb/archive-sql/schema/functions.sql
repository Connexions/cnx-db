CREATE OR REPLACE FUNCTION uuid_generate_v4 () RETURNS uuid LANGUAGE plpythonu AS $$ import uuid; return uuid.uuid4() $$ ;
CREATE OR REPLACE FUNCTION uuid5 (namespace uuid, name text) RETURNS uuid LANGUAGE plpythonu AS $$ import uuid; return uuid.uuid5(uuid.UUID(namespace), name) $$ ;
CREATE OR REPLACE FUNCTION "comma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '','' || $2 END' LANGUAGE 'sql';

CREATE OR REPLACE FUNCTION "semicomma_cat" (text,text) RETURNS text AS 'select case WHEN $2 is NULL or $2 = '''' THEN $1 WHEN $1 is NULL or $1 = '''' THEN $2 ELSE $1 || '';--;'' || $2 END' LANGUAGE 'sql';

CREATE OR REPLACE FUNCTION sha1(file text)
 RETURNS text
 LANGUAGE plpythonu
 IMMUTABLE STRICT
AS $function$
import hashlib
return hashlib.new('sha1', file).hexdigest()
$function$;

CREATE OR REPLACE FUNCTION sha1(f bytea)
 RETURNS text
 LANGUAGE plpythonu
 IMMUTABLE STRICT
AS $function$
import hashlib
return hashlib.new('sha1',f).hexdigest()
$function$;

CREATE OR REPLACE FUNCTION title_order(text) RETURNS text AS $$
begin
if lower(substr($1, 1, 4)) = 'the ' then
 return substr($1, 5);
elsif lower(substr($1,1,3)) = 'an ' then
 return substr($1,4);
elsif lower(substr($1,1,2)) = 'a ' then
 return substr($1,3);
end if;
return $1;
end;
$$ language 'plpgsql' immutable;


CREATE OR REPLACE FUNCTION short_id (u uuid) RETURNS text as $$
select substring(replace(replace(replace(encode(uuid_send(u),'base64'),'+','-'),'/','_'),'=',''),1,8) $$
IMMUTABLE STRICT LANGUAGE SQL;


CREATE OR REPLACE FUNCTION req(text) RETURNS text AS $$
select regexp_replace($1,E'([.()?[\\]\\{}*+|])',E'\\\\\\1','g')
$$ language sql immutable;

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYELEMENT)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS $$
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION array_position (ANYARRAY, ANYARRAY)
RETURNS INTEGER
IMMUTABLE STRICT
LANGUAGE PLPGSQL
AS $$
BEGIN
  for i in array_lower($1,1) .. array_upper($1,1)
  LOOP
    IF ($1[i:i] = $2)
    THEN
      RETURN i;
    END IF;
  END LOOP;
  RETURN NULL;
END;
$$;




-- Deprecated (3-Feb-2015) Use html_abstract(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_abstract, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_abstract(abstract text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_abstract(<module_ident>')
  from cnxtransforms import transform_abstract_to_html
  html_abstract, warning_messages = transform_abstract_to_html(abstract, None, plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_abstract(module_ident int)
  RETURNS text
AS $$
  from cnxtransforms import transform_abstract_to_html
  plan = plpy.prepare("SELECT abstract FROM modules NATURAL JOIN abstracts WHERE module_ident = $1", ('integer',))
  abstract = plpy.execute(plan, (module_ident,))[0]['abstract']
  html_abstract, warning_messages = transform_abstract_to_html(abstract, module_ident, plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_abstract
$$ LANGUAGE plpythonu;

-- Deprecated (3-Feb-2015) Use html_content(module_ident int)
--            This was deprecated to align the call params with
--            synonymous function cnxml_content, which requires
--            access to the module_ident to perform reference resolution.
CREATE OR REPLACE FUNCTION html_content(cnxml text)
  RETURNS text
AS $$
  plpy.warning('This function is deprecated, please use html_content(<module_ident>')
  from cnxtransforms import transform_module_content
  html_content, warning_messages = transform_module_content(cnxml, 'cnxml2html', plpy)
  if warning_messages:
    plpy.warning(warning_messages)
  return html_content
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION html_content(module_ident int)
  RETURNS text
AS $$
  from cnxtransforms import transform_module_content
  plan = plpy.prepare("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = $1 AND (filename = 'index.cnxml' OR filename = 'index.html.cnxml')", ('integer',))
  cnxml = plpy.execute(plan, (module_ident,))[0]['convert_from']
  content, warning_messages = transform_module_content(cnxml, 'cnxml2html', plpy, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;


CREATE OR REPLACE FUNCTION cnxml_abstract(module_ident int)
  RETURNS text
AS $$
  from cnxtransforms import transform_abstract_to_cnxml
  plan = plpy.prepare("SELECT html FROM modules NATURAL JOIN abstracts WHERE module_ident = $1", ('integer',))
  abstract = plpy.execute(plan, (module_ident,))[0]['html']
  cnxml_abstract, warning_messages = transform_abstract_to_cnxml(abstract, module_ident, plpy)
  if warning_messages:
      plpy.warning(warning_messages)
  return cnxml_abstract
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION cnxml_content(module_ident int)
  RETURNS text
AS $$
  from cnxtransforms import transform_module_content
  plan = plpy.prepare("SELECT convert_from(file, 'utf-8') FROM module_files AS mf NATURAL JOIN files AS f WHERE module_ident = $1 AND filename = 'index.cnxml.html'", ('integer',))
  html = plpy.execute(plan, (module_ident,))[0]['convert_from']
  content, warning_messages = transform_module_content(html, 'html2cnxml', plpy, module_ident)
  if warning_messages:
      plpy.warning(warning_messages)
  return content
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION strip_html(html_text TEXT)
  RETURNS text
AS $$
  import re
  return re.sub('<[^>]*?>', '', html_text, re.MULTILINE)
$$ LANGUAGE plpythonu IMMUTABLE;

CREATE OR REPLACE FUNCTION module_version(major int, minor int)
  RETURNS text
  IMMUTABLE
AS $$
  SELECT concat_ws('.', major, minor) ;
$$ LANGUAGE SQL;

SET check_function_bodies = false;

CREATE OR REPLACE FUNCTION is_baked(col_uuid uuid, col_ver text)
 RETURNS boolean
 IMMUTABLE
AS $function$
SELECT bool_or(is_collated)
    FROM modules JOIN trees
        ON module_ident = documentid
    WHERE uuid = col_uuid AND module_version(major_version, minor_version) = col_ver
$function$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION ident_hash(uuid uuid, major integer, minor integer)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$ select uuid || '@' || concat_ws('.', major, minor) $function$;

CREATE OR REPLACE FUNCTION short_ident_hash(uuid uuid, major integer, minor integer)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$ select public.short_id(uuid) || '@' || concat_ws('.', major, minor) $function$;

CREATE OR REPLACE FUNCTION year(ts timestamptz)
  RETURNS DOUBLE PRECISION IMMUTABLE
  AS $$
  SELECT EXTRACT(year from ts)
  $$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION plainto_or_tsquery (TEXT) RETURNS tsquery AS $$
  SELECT to_tsquery( regexp_replace( $1, E'[\\s\'|:&()!]+','|','g') );
$$ LANGUAGE SQL STRICT IMMUTABLE;

-- Create a function that always returns the first non-NULL item
CREATE OR REPLACE FUNCTION first_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $1;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE FIRST (
        sfunc    = first_agg,
        basetype = anyelement,
        stype    = anyelement
);
 
-- Create a function that always returns the last non-NULL item
CREATE OR REPLACE FUNCTION last_agg ( anyelement, anyelement )
RETURNS anyelement LANGUAGE SQL IMMUTABLE STRICT AS $$
        SELECT $2;
$$;
 
-- And then wrap an aggregate around it
CREATE AGGREGATE LAST (
        sfunc    = last_agg,
        basetype = anyelement,
        stype    = anyelement
);

-- Find the first book containing a given uuid (candidate canonical for page)
CREATE OR REPLACE FUNCTION default_canonical_book(id uuid)
RETURNS uuid LANGUAGE SQL STRICT IMMUTABLE AS $$
WITH RECURSIVE t(node, title, parent, path, value) AS (
      SELECT nodeid, coalesce(title,name), parent_id, ARRAY[nodeid], documentid
      FROM trees tr, modules m
      WHERE m.uuid = $1
      AND tr.documentid = m.module_ident
      AND tr.parent_id IS NOT NULL
    UNION ALL
      SELECT c1.nodeid, c1.title, c1.parent_id,
             t.path || ARRAY[c1.nodeid], c1.documentid
              FROM trees c1
              JOIN t ON (c1.nodeid = t.parent)
              WHERE not nodeid = any (t.path)
        )

        SELECT uuid
        from t join modules on t.value = module_ident
        where t.parent is NULL
        ORDER BY revised, major_version, minor_version
        LIMIT 1
$$;
