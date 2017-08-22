# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta

from dbmigrator import deferred

logger = logging.getLogger('migration')


def _batcher(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def up(cursor):
    """Add SubCollection uuids and metadata records for all latest books"""

    cursor.execute("""SELECT DISTINCT ident_hash(uuid, major_version, minor_version)
            FROM trees t
              JOIN trees p ON t.parent_id = p.nodeid
              JOIN latest_modules m ON p.documentid=m.module_ident
            WHERE t.documentid is null""")
    anon_subcols = [r[0].split('@') for r in cursor.fetchall()]

    num_todo = len(anon_subcols)
    logger.debug('Books to add chapter uuids: {}'.format(num_todo))

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
        logger.debug('{}% complete; '
                     'est: "{}" ({})'.format(percent_comp,
                                             time.ctime(est_complete),
                                             timedelta(0, remaining_est)))


def down(cursor):
    cursor.execute("DELETE FROM modules WHERE portal_type = 'SubCollection'")
    cursor.execute("""UPDATE trees t SET documentid = NULL WHERE NOT EXISTS
            (SELECT 1 FROM modules m WHERE m.module_ident = t.documentid""")


def should_run(cursor):
    """Check if any latest books still have chapters without uuids."""
    cursor.execute("""SELECT ident_hash(uuid,major_version,minor_version) FROM trees t
              JOIN trees p ON t.parent_id = p.nodeid
              JOIN latest_modules m ON p.documentid=m.module_ident
            WHERE t.documentid IS NULL""")
    anon_subcols = cursor.fetchone()[0]
    return anon_subcols
