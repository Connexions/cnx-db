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
    cursor.execute("CREATE TABLE languages (language text NOT NULL, config text);")
    with open_here('../archive-sql/schema/constants/languages.sql', 'rb') as f:
        cursor.execute(f.read())


def down(cursor):
    cursor.execute('DROP TABLE languages')
