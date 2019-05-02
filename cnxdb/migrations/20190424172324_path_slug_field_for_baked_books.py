# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta
from functools import wraps

from dbmigrator import deferred
from dbmigrator import logger
from dbmigrator import super_user
from cnxcommon.urlslug import generate_slug


BATCH_SIZE = 1000
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

# https://wiki.postgresql.org/wiki/Unnest_multidimensional_array
CREATE_REDUCE_DIM = """\
CREATE OR REPLACE FUNCTION public.reduce_dim(anyarray)
RETURNS SETOF anyarray AS
$function$
DECLARE
    s $1%TYPE;
BEGIN
    FOREACH s SLICE 1  IN ARRAY $1 LOOP
        RETURN NEXT s;
    END LOOP;
    RETURN;
END;
$function$
LANGUAGE plpgsql IMMUTABLE;
"""

DROP_REDUCE_DIM = """\
DROP FUNCTION public.reduce_dim(anyarray);
"""

UPDATE_STMT = """\
UPDATE trees SET slug = q.slug
from (
  SELECT yyy[1] AS id, yyy[2] AS slug FROM reduce_dim(%s) AS yyy
) AS q
WHERE nodeid = q.id::int
;
"""


def _batcher(seq, size):
    for pos in range(0, len(seq), size):
        yield seq[pos:pos + size]


def generate_update_values(nodeid, title):
    """Returns a sequence of trees.nodeid and trees.slug
    to be used to update the trees slug table value.

    """
    logger.info("processing... {} - {}".format(nodeid, title))
    try:
        slug = generate_slug(*title)
    except:
        logger.exception(
            "failed to create slug for '{}'".format(title)
        )
        raise
    logger.info("... using {}".format(slug))
    # must return an array of a single type for postgresql
    return [str(nodeid), slug]


def on_fail_rollback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            logger.info(
                "Running 'down' to rollback the changes due to error"
            )
            down(*args, **kwargs)
            raise
    return wrapper


@on_fail_rollback
def up(cursor):
    # This could be two migrations, the column entry would be non-deferred
    # while the data migration could be deferred.

    # Add the new column to the trees table
    with super_user() as super_cursor:
        super_cursor.execute("ALTER TABLE trees ADD COLUMN slug text")

    # Create sql function for reducing the dimension of an array
    cursor.execute(CREATE_REDUCE_DIM)

    # Roll over all collated tree records.
    # Cannot iterate over the results, because we need the cursor for
    # updating the records we are rolling over.
    logger.info("starting query of entire trees table... *tick tock*")
    cursor.execute(TREE_QUERY)
    records = cursor.fetchall()



    num_todo = len(records)
    logger.info('Items to update: {}'.format(num_todo))
    logger.info('Batch size: {}'.format(BATCH_SIZE))

    start = time.time()
    guesstimate = 0.01 * num_todo
    guess_complete = guesstimate + start
    logger.info(
        'Completion guess: "{}" ({})'
        .format(
            time.ctime(guess_complete),
            timedelta(0, guesstimate),
        )
    )

    num_complete = 0
    for batch in _batcher(records, BATCH_SIZE):
        updates = [
            generate_update_values(nodeid, title)
            for nodeid, title in batch
        ]
        cursor.execute(UPDATE_STMT, (updates,))

        cursor.connection.commit()
        num_complete += len(batch)
        percent_comp = num_complete * 100.0 / num_todo
        elapsed = time.time() - start
        remaining_est = elapsed * (num_todo - num_complete) / num_complete
        est_complete = start + elapsed + remaining_est
        logger.info('{:.1f}% complete '
                    'est: "{}" ({})'.format(percent_comp,
                                            time.ctime(est_complete),
                                            timedelta(0, remaining_est)))

    logger.info('Total runtime: {}'.format(timedelta(0, elapsed)))

    cursor.execute(DROP_REDUCE_DIM)


def down(cursor):
    # Drop the new column to the trees table
    with super_user() as super_cursor:
        super_cursor.execute("ALTER TABLE trees DROP COLUMN slug")
