# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta

from dbmigrator import deferred

logger = logging.getLogger('dbmigrator')


def _batcher(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


@deferred
def up(cursor):
    """Add SubCollection uuids and metadata records for all latest books"""

    anon_subcols = should_run(cursor)

    num_todo = len(anon_subcols)
    logger.info('Books to add chapter uuids: {}'.format(num_todo))

    if num_todo > 10:
        batch_size = int(num_todo / 10)
    else:
        batch_size = num_todo

    if batch_size > 100:
        batch_size = 100

    start = time.time()
    num_complete = 0
    for batch in _batcher(anon_subcols, batch_size):
        for book in batch:
            cursor.execute("SELECT subcol_uuids(%s, %s)", book)
        cursor.connection.commit()
        num_complete += len(batch)
        percent_comp = (num_complete * 100) / num_todo
        elapsed = time.time() - start
        remaining_est = elapsed * (num_todo - num_complete) / num_complete
        est_complete = start + remaining_est
        logger.info('{}% complete; '
                    'est: "{}" ({})'.format(percent_comp,
                                            time.ctime(est_complete),
                                            timedelta(0, remaining_est)))


def down(cursor):
    cursor.execute("DELETE FROM modules WHERE portal_type = 'SubCollection'")
    cursor.execute("""UPDATE trees t SET documentid = NULL
                      WHERE documentid is not NULL
                      AND NOT EXISTS (SELECT 1 FROM modules m
                            WHERE m.module_ident = t.documentid""")


def should_run(cursor):
    """Check if any latest books still have chapters without uuids."""
    cursor.execute("""WITH RECURSIVE t(node, title, path, documentid, parent,
     depth, corder, is_collated) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, NULL::integer, 1,
           ARRAY[childorder], is_collated
    FROM trees tr, latest_modules m
    WHERE
      tr.documentid = m.module_ident AND
      tr.parent_id IS NULL AND
      tr.is_collated = False
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid],
    c1.documentid, t.documentid, t.depth+1, t.corder || ARRAY[c1.childorder],
    c1.is_collated
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path) AND t.is_collated = c1.is_collated
)

SELECT DISTINCT ident_hash(m.uuid, m.major_version, m.minor_version), t.depth
           FROM t JOIN trees b ON t.path[1] = b.nodeid JOIN
           latest_modules m ON b.documentid=m.module_ident
           WHERE t.documentid is null
        ORDER by 1,2""")
    anon_subcols = [r[0].split('@') for r in cursor.fetchall()]
    return anon_subcols
