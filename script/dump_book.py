#!/var/cnx/venvs/archive/bin/python
"""
This script attempts to dump a book from the server and load it into a
development database.

1. You need to download this script onto the server, e.g. staging08.cnx.org,
   that runs archive.

2. Use `./dump_book.py dump_book caa57dab-41c7-455e-bd6f-f443cda5519c@19.3` to
   dump the prealgebra book.

   2.1 If you are not using this on a cnx-deploy'd server, you can either
       specify the path to the archive config file using `CONFIG_INI` or the
       database connection string using `DB_URL` environment variables.

   2.2 If you want to dump multiple books, just add more book ident hashes to
       the end of the command line.

3. Transfer the output file
   `book_dump.prealgebra@19.3.tar` to the
   development machine.

4. Run `./dump_book.py load_book book_dump.prealgebra@19.3.tar`
   to load the book into a development database.

   4.1 If you are not using this on a cnx-deploy'd server, you can either
       specify the path to the archive config file using `CONFIG_INI` or the
       database connection string using `DB_URL` environment variables.

   4.2 If you want to load multiple files, just add the filenames to the end of
       the command line.

**Note**: strictly for development use only.
"""

import base64
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import contextlib
import json
import logging
import os
import re
import shutil
import socket
import sys
import tarfile
import tempfile

import psycopg2.extras
from psycopg2.sql import SQL, Identifier, Placeholder


DB_URL = os.getenv('DB_URL')
CONFIG_INI = os.getenv('CONFIG_INI', '/etc/cnx/archive/app.ini')
if not DB_URL:
    if not os.path.exists(CONFIG_INI):
        sys.stderr.write('DB_URL or CONFIG_INI must be set\n')
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(CONFIG_INI)
    DB_URL = config.get('app:main', 'db-connection-string')


@contextlib.contextmanager
def db_cursor(db_conn_str=DB_URL,
              cursor_factory=psycopg2.extras.RealDictCursor):
    with psycopg2.connect(db_conn_str) as db_conn:
        with db_conn.cursor(cursor_factory=cursor_factory) as cursor:
            yield cursor


def execute_sql(sql, params=(), **kwargs):
    with db_cursor(**kwargs) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def get_latest_version(book_uuid):
    return execute_sql("""
    SELECT module_version(major_version, minor_version)
    FROM latest_modules
    WHERE uuid::text = %s""", (book_uuid,), cursor_factory=None)


def get_module_idents_tree_nodes(book_uuid, book_version):
    get_module_idents_sql = """
    WITH RECURSIVE t(node, path, value, parent) AS (
        SELECT nodeid, ARRAY[nodeid], documentid, parent_id
        FROM trees tr, modules m
        WHERE m.uuid::text = %s AND
              module_version(m.major_version, m.minor_version) = %s AND
              tr.documentid = m.module_ident AND
              tr.parent_id IS NULL
    UNION ALL
        SELECT c1.nodeid, t.path || ARRAY[c1.nodeid], c1.documentid,
               c1.parent_id
        FROM trees c1 JOIN t ON (c1.parent_id = t.node)
        WHERE NOT nodeid = ANY(t.path)
    )
    SELECT DISTINCT value, node, parent
    FROM t ORDER BY parent DESC"""
    return execute_sql(get_module_idents_sql, (book_uuid, book_version),
                       cursor_factory=None)


def get_abstracts(module_idents):
    print('dumping data from abstracts')
    return execute_sql("""
    SELECT * FROM abstracts
    WHERE EXISTS (
        SELECT 1 FROM modules
        WHERE modules.abstractid = abstracts.abstractid
          AND modules.module_ident IN %s
    )""", (tuple(module_idents),))


def get_collated_file_associations(book_module_ident):
    print('dumping data from collated_file_associations')
    return execute_sql("""
    SELECT * FROM collated_file_associations
    WHERE context = %s
    """, (book_module_ident,))


def get_document_acl(module_idents):
    print('dumping data from document_acls')
    return execute_sql("""
    SELECT * FROM document_acl WHERE EXISTS(
        SELECT 1 FROM modules
        WHERE modules.uuid = document_acl.uuid
          AND modules.module_ident IN %s
    )""", (tuple(module_idents),))


def get_document_controls(module_idents):
    print('dumping data from document_controls')
    return execute_sql("""
    SELECT * FROM document_controls WHERE EXISTS (
        SELECT 1 FROM modules
        WHERE modules.uuid = document_controls.uuid
          AND modules.module_ident IN %s
    )""", (tuple(module_idents),))


def get_files(fileids):
    print('dumping data from files')
    for f in execute_sql("""
    SELECT fileid, md5, encode(file, 'base64') AS file, sha1, media_type
    FROM files WHERE fileid IN %s
    """, (tuple(fileids),)):
        f['file'] = f['file'][:]
        yield f


def get_licenses():
    print('dumping data from licenses')
    return execute_sql('SELECT * FROM licenses')


def get_module_files(module_idents):
    print('dumping data from module_files')
    return execute_sql("""
    SELECT * FROM module_files WHERE module_ident IN %s
    """, (tuple(module_idents),))


def get_modules(module_idents):
    print('dumping data from modules')
    for f in execute_sql("""
    SELECT * FROM modules WHERE module_ident IN %s
    """, (tuple(module_idents),)):
        f['created'] = f['created'].isoformat()
        f['revised'] = f['revised'].isoformat()
        f['baked'] = f['baked'] and f['baked'].isoformat()
        yield f


def get_modulestates():
    print('dumping data from modulestates')
    return execute_sql('SELECT * FROM modulestates')


def get_moduletags(module_idents):
    print('dumping data from moduletags')
    return execute_sql("""
    SELECT * FROM moduletags WHERE module_ident IN %s
    """, (tuple(module_idents),))


def get_tags(module_idents):
    print('dumping data from tags')
    return execute_sql("""
    SELECT * FROM tags WHERE EXISTS (
        SELECT 1 FROM moduletags
        WHERE module_ident IN %s AND moduletags.tagid = tags.tagid
    )""", (tuple(module_idents),))


def get_trees(tree_nodes):
    print('dumping data from tree')
    return execute_sql("""
    SELECT * FROM trees WHERE nodeid IN %s
    """, (tuple(tree_nodes),))


def get_users(usernames):
    print('dumping data from users')
    for u in execute_sql("""
    SELECT * FROM users WHERE username IN %s
    """, (tuple(usernames),)):
        u['created'] = u['created'].isoformat()
        u['updated'] = u['updated'].isoformat()
        yield u


def dump_book(book_ident_hash):
    if '@' in book_ident_hash:
        book_uuid, book_version = book_ident_hash.split('@', 1)
    else:
        book_uuid = book_ident_hash
        try:
            book_version = get_latest_version(book_uuid)[0][0]
        except IndexError:
            raise Exception('Unable to find book {}'.format(book_ident_hash))
    module_idents_tree_nodes = get_module_idents_tree_nodes(
        book_uuid, book_version)
    if not module_idents_tree_nodes:
        raise Exception('Unable to find book {}'.format(book_ident_hash))
    module_idents = [i[0] for i in module_idents_tree_nodes]
    tree_nodes = [i[1] for i in module_idents_tree_nodes]
    book_data = {}
    book_data['abstracts'] = get_abstracts(module_idents)
    book_data['collated_file_associations'] = get_collated_file_associations(
        module_idents[0])
    book_data['document_acl'] = get_document_acl(module_idents)
    book_data['document_controls'] = get_document_controls(module_idents)
    book_data['licenses'] = get_licenses()
    book_data['module_files'] = get_module_files(module_idents)
    book_data['modules'] = list(get_modules(module_idents))
    book_data['modulestates'] = get_modulestates()
    book_data['moduletags'] = get_moduletags(module_idents)
    book_data['tags'] = get_tags(module_idents)
    book_data['trees'] = get_trees(tree_nodes)

    fileids = [a['fileid'] for a in book_data['collated_file_associations']] \
        + [a['recipe'] for a in book_data['modules']] \
        + [a['fileid'] for a in book_data['module_files']]
    book_data['files'] = get_files(set(fileids))

    usernames = [a['submitter'] for a in book_data['modules']]
    for a in book_data['modules']:
        usernames += a['authors'] + a['maintainers'] + a['licensors']
    book_data['users'] = list(get_users(set(usernames)))

    book_title = [m['name'] for m in book_data['modules']
                  if m['portal_type'] == 'Collection'][0]
    slug = re.sub('[^a-z0-9]+', '-', book_title.lower())
    if len(slug) <= 5:
        slug = book_uuid
    output_filename = 'book_dump.{}@{}.tar'.format(slug, book_version)
    tmpdir = tempfile.mkdtemp()
    with tarfile.open(os.path.join(tmpdir, output_filename), 'w') as out:
        # create one json file per file
        for i, file_entry in enumerate(book_data.pop('files')):
            filename = 'files-{:04d}.json'.format(i)
            with open(os.path.join(tmpdir, filename), 'w') as f:
                json.dump(file_entry, f)
            out.add(os.path.join(tmpdir, filename), filename)
        # create files for other tables
        for tablename in book_data:
            filename = '{}.json'.format(tablename)
            with open(os.path.join(tmpdir, filename), 'w') as f:
                json.dump(book_data[tablename], f)
            out.add(os.path.join(tmpdir, filename), filename)
    if os.path.exists(output_filename):
        os.remove(output_filename)
    shutil.move(os.path.join(tmpdir, output_filename), '.')
    shutil.rmtree(tmpdir)
    print('Output in {}'.format(output_filename))


def load_table(cursor, tablename, columns, data, unique_key=None):
    unique_key = unique_key or (get_pkey_column(cursor, tablename),)

    # FIXME: Most of the branching here can be replaced
    #        by an upsert in postgres >9.4
    if unique_key == (None,):
        sql = SQL("""
        INSERT INTO {} ({})
        VALUES({})
        """).format(Identifier(tablename),
                    SQL(', ').join(map(Identifier, columns)),
                    SQL(', ').join(Placeholder() for c in columns))
    else:
        unique_as_idents = list(map(Identifier, unique_key))
        unique_as_placeholders = [Placeholder() for c in unique_key]
        unique_matches_condition = SQL(' AND ').join(
            map(lambda ident_ph_tup: SQL('{} = {}').format(ident_ph_tup[0],
                                                           ident_ph_tup[1]),
                zip(unique_as_idents, unique_as_placeholders)))

        sql = SQL("""
        INSERT INTO {0} ({1})
        SELECT {2}
        WHERE NOT EXISTS (
            SELECT * FROM {0} WHERE {3}
        )""").format(Identifier(tablename),
                     SQL(', ').join(map(Identifier, columns)),
                     SQL(', ').join(Placeholder() for c in columns),
                     unique_matches_condition)

    for row in data:
        if unique_key == (None,):
            params = row
        else:
            row_data = dict(zip(columns, row))
            unique_values = tuple(map(lambda column: row_data[column],
                                      unique_key))
            params = row + unique_values
        try:
            cursor.execute(sql, params)
        except psycopg2.errors.UniqueViolation as e:
            logging.error(e)


def get_pkey_column(cursor, tablename):
    sql = """
    SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid
        AND a.attnum = ANY(i.indkey)
    WHERE i.indrelid = %s::regclass
    AND i.indisprimary;
    """
    result = None
    try:
        cursor.execute(sql, (tablename,))
    except psycopg2.errors.UniqueViolation as e:
        logging.error(e)
    try:
        result = cursor.fetchone()[0]
    except TypeError:
        print('info: could not find pkey column for table: {}'.format(
            tablename))
    return result


def load_data(tablename, data, unique_key=None):
    print('loading data into {}'.format(tablename))
    if not data:
        return
    columns = list(data[0].keys())
    with db_cursor(cursor_factory=None) as cursor:
        load_table(cursor, tablename, columns,
                   (tuple(d[c] for c in columns) for d in data),
                   unique_key)


def confirm_load():
    module_count = execute_sql('SELECT count(*) FROM modules')[0]['count']
    if module_count == 0:
        return True
    hostname = socket.gethostname()
    sys.stdout.write('The modules table is not empty. You are on {}. '
                     'Confirm load. (yes/No) '.format(hostname))
    if sys.version_info.major == 2:
        # raw_input is not defined in python 3
        confirmation = raw_input()  # noqa
    else:
        confirmation = input()
    return confirmation.lower() == 'yes'


def bump_sequence(sequence, table, id_column):
    print('updating sequence {} from {}:{}'.format(sequence, table, id_column))
    sql = SQL('SELECT setval(%s, (SELECT max({}) + 1 FROM {}))').format(
        Identifier(id_column), Identifier(table))
    with db_cursor(cursor_factory=None) as cursor:
        try:
            cursor.execute(sql, (sequence,))
        except psycopg2.errors.UniqueViolation as e:
            logging.error(e)


def load_book(filename):
    infile = tarfile.open(filename, 'r')

    def get_data(field):
        return json.loads(infile.extractfile('{}.json'.format(field)).read()
                          .decode('utf-8'))

    # Disable all the triggers except ...
    with db_cursor() as cursor:
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER ALL')
        cursor.execute('ALTER TABLE module_files DISABLE TRIGGER ALL')
        cursor.execute('ALTER TABLE module_files ENABLE TRIGGER '
                       'index_fulltext')
        cursor.execute('ALTER TABLE modules ENABLE TRIGGER '
                       'delete_from_latest_version')
        cursor.execute('ALTER TABLE modules ENABLE TRIGGER '
                       'update_latest_version')

    # first load everything that has nothing to do with modules
    load_data('licenses', get_data('licenses'))
    load_data('modulestates', get_data('modulestates'))
    load_data('tags', get_data('tags'))
    # files are divided into one json file per file
    for f in sorted(infile.getnames()):
        if f.startswith('files-'):
            data = get_data(f.rsplit('.', 1)[0])  # remove .json
            data['file'] = memoryview(base64.b64decode(data['file']))
            load_data('files', [data])
    # the "users" schema on staging is different from development
    users = get_data('users')
    for u in users:
        for field in ('website', 'surname', 'firstname', 'id', 'fullname',
                      'email'):
            if field in u:
                u.pop(field)
    load_data('users', users)
    load_data('document_controls', get_data('document_controls'))
    load_data('document_acl', get_data('document_acl'))
    load_data('abstracts', get_data('abstracts'))

    # then load everything that depends on modules
    # remove parents from modules, can't deal with them atm
    modules = get_data('modules')
    for m in modules:
        m['parent'] = None
        m['parentauthors'] = []
    load_data('modules', modules)
    load_data('collated_file_associations',
              get_data('collated_file_associations'))
    load_data('module_files',
              get_data('module_files'),
              ('module_ident', 'filename'))
    load_data('moduletags', get_data('moduletags'), ('module_ident',))
    load_data('trees', get_data('trees'))

    bump_sequence('abstracts_abstractid_seq', 'abstracts', 'abstractid')
    bump_sequence('files_fileid_seq', 'files', 'fileid')
    bump_sequence('licenses_licenseid_seq', 'licenses', 'licenseid')
    bump_sequence('modules_module_ident_seq', 'modules', 'module_ident')
    bump_sequence('tags_tagid_seq', 'tags', 'tagid')

    # Enable the triggers again
    with db_cursor() as cursor:
        cursor.execute('ALTER TABLE modules ENABLE TRIGGER ALL')
        cursor.execute('ALTER TABLE module_files ENABLE TRIGGER ALL')

    infile.close()


__all__ = ('dump_book', 'load_book')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in __all__:
        sys.stderr.write(
            'Usage: {name} dump_book book_ident_hash [book_ident_hash ...]\n'
            '   or  {name} load_book filename [filename ...]\n'
            .format(name=sys.argv[0]))
        sys.exit(1)

    if sys.argv[1] == 'load_book':
        if not confirm_load():
            sys.stderr.write('load_book aborted.\n')
            sys.exit(1)

    for arg in sys.argv[2:]:
        print('Running: {} {}'.format(sys.argv[1], arg))

        globals()[sys.argv[1]](arg)
