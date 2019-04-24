# -*- coding: utf-8 -*-
import logging

from dbmigrator import deferred
from dbmigrator import super_user
from cnxcommon.urlslug import generate_slug


logger = logging.getLogger('dbmigrator')


# Uncomment should_run if this is a repeat migration
# def should_run(cursor):
#     # TODO return True if migration should run


TREE_QUERY = """\
WITH RECURSIVE t(node, title, path, value, depth, corder, is_collated) AS (
    SELECT nodeid, ARRAY[title], ARRAY[nodeid], documentid, 1, ARRAY[childorder],
           is_collated
    FROM trees tr, modules m
    WHERE tr.documentid = m.module_ident
          AND
          tr.parent_id IS NULL
          AND
          tr.is_collated = TRUE
UNION ALL
    /* Recursion */
    SELECT c1.nodeid,
           /* concat the new record to the hierarchy of titles */
           t.title || ARRAY[c1.title],
           /* concat the new record to the path */
           t.path || ARRAY[c1.nodeid],
           c1.documentid,
           t.depth+1,
           t.corder || ARRAY[c1.childorder],
           c1.is_collated
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE NOT nodeid = ANY (t.path)
          AND
          t.is_collated = c1.is_collated
)
SELECT node, title
FROM t LEFT JOIN modules m ON t.value = m.module_ident
WINDOW w AS (ORDER BY corder)
ORDER BY corder
;
"""

@deferred
def up(cursor):
    # This could be two migrations, the column entry would be non-deferred
    # while the data migration could be deferred.

    # Add the new column to the trees table
    with super_user() as super_cursor:
        super_cursor.execute("ALTER TABLE trees ADD COLUMN slug text")

    # Roll over all collated tree records.
    # Use the super_cursor to iterate through records
    # and the supplied cursor to update them.
    with super_user() as super_cursor:
        logger.info("starting query of entire trees table... *tick tock*")
        super_cursor.execute(TREE_QUERY)

        update_stmt = "UPDATE trees SET slug = %s WHERE nodeid = %s"
        for nodeid, title in super_cursor:
            logger.info("processing... {} - {}".format(nodeid, title))
            try:
                slug = generate_slug(*title)
            except:
                logger.exception(
                    "failed to create slug for '{}'".format(title)
                )
                raise
        try:
            cursor.execute(update_stmt, (slug, nodeid))
        except Exception:
            logger.exception("slug, nodeid: {}, {}".format(slug, nodeid))
            raise

def down(cursor):
    # Drop the new column to the trees table
    with super_user() as super_cursor:
        super_cursor.execute("ALTER TABLE trees DROP COLUMN slug")
