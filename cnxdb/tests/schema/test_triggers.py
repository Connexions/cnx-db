# -*- coding: utf-8 -*-
import json
import uuid

import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .. import testing


# Note, the triggers are only python 2.x compatible. It's assumed,
# at least for now, that in-database logic (i.e. triggers) are only
# run within a python2 environment. This product is to be setup in a
# production environment running within the database under python2 and
# optionally running within application code under either python2 or python3.


@pytest.mark.skipif(testing.is_py3(),
                    reason="triggers are only python2.x compat")
class TestPostPublication:

    channel = 'post_publication'

    def _make_one(self, cursor):
        """Insert the minimum necessary for creating a 'modules' entry."""
        uuid_ = str(uuid.uuid4())
        cursor.execute("INSERT INTO document_controls (uuid) VALUES (%s)",
                       (uuid_,))
        # The important bit here is `stateid = 5`
        cursor.execute("""\
        INSERT INTO modules
          (module_ident, portal_type, uuid, name, licenseid, doctype, stateid)
        VALUES
          (DEFAULT, 'Collection', %s, 'Physics: An Introduction', 11, '', 5)
        RETURNING
          module_ident,
          ident_hash(uuid, major_version, minor_version)""",
                       (uuid_,))
        module_ident, ident_hash = cursor.fetchone()
        cursor.connection.commit()
        return (module_ident, ident_hash)

    def test_payload(self, db_cursor):
        # Listen for notifications
        db_cursor.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        db_cursor.execute('LISTEN {}'.format(self.channel))
        db_cursor.connection.commit()

        module_ident, ident_hash = self._make_one(db_cursor)

        # Commit and poll to get the notifications
        db_cursor.connection.commit()
        db_cursor.connection.poll()
        notify = db_cursor.connection.notifies.pop(0)

        # Test the contents of the notification
        assert notify.channel == self.channel
        payload = json.loads(notify.payload)
        assert payload['module_ident'] == module_ident
        assert payload['ident_hash'] == ident_hash
        assert payload['timestamp']
