# -*- coding: utf-8 -*-
import os

from contextlib import contextmanager


@contextmanager
def open_here(filepath, *args, **kwargs):
    """open a file relative to this files location"""

    here = os.path.abspath(os.path.dirname(__file__))
    fp = open(os.path.join(here, filepath), *args, **kwargs)
    yield fp
    fp.close()


def up(cursor):

    with open_here('../archive-sql/schema/shred_collxml.sql', 'rb') as f:
        cursor.execute(f.read())


def down(cursor):
    with open_here('shred_collxml_20170912134157_pre.sql', 'rb') as f:
        cursor.execute(f.read())
