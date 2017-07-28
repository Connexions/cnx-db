# -*- coding: utf-8 -*-
import os


here = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(here, 'data')


def test_get_schema():
    example_schema_dir = os.path.join(DATA_DIR, 'example_schema')

    file_series = (
        'file_xyz.sql',
        'sub/subfile_123-xyz.sql',
        'sub/subsub/subsubfile_123-abc-456.sql',
        'sub/subsub/subsubfile_123-abc-123.sql',
        'sub/subfile_123-efg.sql',
        'file_abc.sql',
    )
    from cnxdb.init.manifest import get_schema
    for i, file in enumerate(get_schema(example_schema_dir)):
        abs_filepath = os.path.abspath(os.path.join(example_schema_dir,
                                                    file_series[i]))
        assert '-- FILE: {0}'.format(abs_filepath).encode('utf-8') in file
