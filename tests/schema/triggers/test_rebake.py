# -*- coding: utf-8 -*-
import uuid

import pytest

from cnxdb.contrib import testing


def test_rebake_triggered_from_ruleset_css(db_init_and_wipe, db_engines, db_tables):
    uuid_ = str(uuid.uuid4())
    engine = db_engines['common']

    # Create a dummy collection
    stmt = db_tables.modules.insert().values(
        uuid=uuid_,
        portal_type='Collection',
        name='Book A',
        licenseid=11,
        doctype='',
        stateid=1,
    ).returning(
        db_tables.modules.c.module_ident,
        db_tables.modules.c.stateid,
    )
    module_ident, stateid = engine.execute(stmt).fetchone()

    # The important bit of this test is `stateid = 1` (aka 'current')
    # Another trigger sets the `stateid = 5`, so we force it to 1
    assert stateid == 5
    engine.execute(
        db_tables.modules.update().values(
            stateid=1,
        ).where(db_tables.modules.c.module_ident == module_ident)
    )

    # Create the 'ruleset.css' file that the trigger functions on
    stmt = db_tables.files.insert().values(
        file='css file',
        media_type='text/css',
    ).returning(db_tables.files.c.fileid)
    fileid = engine.execute(stmt).fetchone()[0]
    stmt = db_tables.module_files.insert().values(
        module_ident=module_ident,
        fileid=fileid,
        filename='ruleset.css',
    )
    engine.execute(stmt)

    # Verify the state has changed
    result = engine.execute(
        db_tables.modules
        .select()
        .where(db_tables.modules.c.module_ident == module_ident)
    )
    record = result.fetchone()
    assert record.stateid == 5
