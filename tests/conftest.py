# -*- coding: utf-8 -*-
"""This module contains testing fixtures.

The other testing fixtures are located in cnxdb.contrib.pytest.

The fixtures located in this module are specific to this
package's tests.

"""
import pytest

# XXX (2017-10-12) deps-on-cnx-archive: Depends on cnx-archive
from cnxarchive.config import TEST_DATA_SQL_FILE


# XXX (2017-10-13) deps-on-cnx-archive: Depends on cnx-archive
@pytest.fixture
def xxx_archive_data(db_init_and_wipe, db_cursor):
    # Load the database with example legacy data.
    with open(TEST_DATA_SQL_FILE, 'rb') as fb:
        db_cursor.execute(fb.read())
    db_cursor.connection.commit()
