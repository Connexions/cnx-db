# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import json
import re

import psycopg2
import psycopg2.extras

from .testing import db_connection_factory

"""Helpers for the tests."""

DEFAULT_DATE_ONE = '2013-07-31 12:00:00.000000+02'
DEFAULT_DATE_TWO = '2013-10-03 21:16:20.000000+02'

MODULE_COLUMNS = ['module_ident', 'portal_type', 'moduleid', 'uuid', 'version',
                  'name', 'created', 'revised', 'abstractid', 'licenseid',
                  'doctype', 'submitter', 'submitlog', 'stateid', 'parent',
                  'language', 'authors', 'maintainers', 'licensors',
                  'parentauthors', 'google_analytics', 'buylink', 'major_version',
                  'minor_version', 'print_style', 'baked', 'recipe']


def add_module(cursor,
               portal_type="Module", moduleid="m1",
               uuid=None, version='1.1', name="Name of m1",
               created=DEFAULT_DATE_ONE, revised=DEFAULT_DATE_TWO,
               abstractid=None, licenseid=11, doctype='', submitter='',
               submitlog='', stateid=None, parent=None, language='en',
               authors=[], maintainers=[], licensors=[], parentauthors=[],
               google_analytics=None, buylink=None,
               major_version=1, minor_version=1,
               print_style=None, baked=None, recipe=None,
               returning=None):
    statement = """
    INSERT INTO modules (
        portal_type, moduleid, uuid, version, name, created,
        revised, abstractid, licenseid, doctype, submitter, submitlog, stateid,
        parent, language, authors, maintainers, licensors, parentauthors,
        google_analytics, buylink, major_version, minor_version,
        print_style, baked, recipe
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s
    ){};
    """
    if returning:
        for i in [x.strip() for x in returning.split(',')]:
            if i not in MODULE_COLUMNS:
                raise Exception
        statement = statement.format("RETURNING " + returning)
    else:
        statement = statement.format("")
    cursor.execute(
        statement,
        vars=(portal_type, moduleid, uuid, version, name, created,
             revised, abstractid, licenseid, doctype, submitter, submitlog, stateid,
             parent, language, authors, maintainers, licensors, parentauthors,
             google_analytics, buylink, major_version, minor_version,
             print_style, baked, recipe)
    )


def add_collection(cursor,
                   portal_type="Collection", moduleid="col1",
                   uuid=None, version='1.10', name="Name of col1",
                   created=DEFAULT_DATE_ONE, revised=DEFAULT_DATE_TWO,
                   abstractid=None, licenseid=11, doctype='doctype',
                   submitter='submitter', submitlog='submitlog', stateid=None,
                   parent=None, language='en', authors=['authors'],
                   maintainers=['maintainers'], licensors=['licensors'],
                   parentauthors=['parentauthors'],
                   google_analytics='analytics code', buylink='buylink',
                   major_version=7, minor_version=10,
                   print_style=None, baked=None, recipe=None,
                   returning=None):
    add_module(cursor, portal_type, moduleid, uuid, version, name, created,
               revised, abstractid, licenseid, doctype, submitter, submitlog,
               stateid, parent, language, authors, maintainers, licensors,
               parentauthors, google_analytics, buylink, major_version,
               minor_version, print_style, baked, recipe, returning)


def add_module_plpy(plpy,
                    portal_type="Module", moduleid="m1",
                    uuid=None, version='1.1', name="Name of m1",
                    created=DEFAULT_DATE_ONE, revised=DEFAULT_DATE_TWO,
                    abstractid=None, licenseid=11, doctype='', submitter='',
                    submitlog='', stateid=None, parent=None, language='en',
                    authors=[], maintainers=[], licensors=[], parentauthors=[],
                    google_analytics=None, buylink=None,
                    major_version=1, minor_version=1,
                    print_style=None, baked=None, recipe=None,
                    returning=None):
    statement = plpy.prepare("""
        INSERT INTO modules (
            portal_type, moduleid, uuid, version, name, created,
            revised, abstractid, licenseid, doctype, submitter, submitlog, stateid,
            parent, language, authors, maintainers, licensors, parentauthors,
            google_analytics, buylink, major_version, minor_version, print_style,
            baked, recipe
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9,
            $10, $11, $12, $13, $14, $15, $16, $17, $18, $19,
            $20, $21, $22, $23, $24, $25, $26
        )RETURNING module_ident;
    """,
    ("text", "text", "uuid", "text", "text", "timestamp",
     "timestamp", "int", "int", "text", "text", "text", "int",
     "int", "text", "text[]", "text[]", "text[]", "text[]",
     "text", "text", "int", "int", "text", "timestamp", "int",))
    module_ident = plpy.execute(statement,
                      (portal_type, moduleid, uuid, version, name, created,
                       revised, abstractid, licenseid, doctype, submitter,
                       submitlog, stateid, parent, language, authors, maintainers,
                       licensors, parentauthors, google_analytics, buylink,
                       major_version, minor_version, print_style, baked, recipe))
    return module_ident[0][0]


def add_sub_collection_no_vars(plpy):
    return plpy.execute("""
        INSERT INTO modules (
            portal_type, moduleid, uuid, version, name, created,
            revised, abstractid, licenseid, doctype, submitter, submitlog, stateid,
            parent, language, authors, maintainers, licensors, parentauthors,
            google_analytics, buylink, major_version, minor_version, print_style,
            baked, recipe
        ) VALUES (
            'SubCollection', 'col1', '88cd206d-66d2-48f9-86bb-75d5366582ee',
            '1.1', 'Name of col1',
            '2013-07-31 12:00:00.000000+02', '2013-10-03 21:14:11.000000+02',
            NULL, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}',
            NULL, NULL, NULL, 1, 1, NULL, NULL, NULL) RETURNING module_ident;
    """)


def remove_module(cursor, module_ident=[], moduleid=[]):
    cursor.execute("""DELETE FROM modules
                      WHERE module_ident = ANY (%s) OR moduleid = ANY (%s);""",
                   vars=(module_ident, moduleid))


def add_tree(cursor,
             parent_id=None, documentid=None, title='title', childorder=0,
             latest=None, is_collated=False, returning=None):
    statement = """
    INSERT INTO trees (
        parent_id, documentid, title, childorder, latest, is_collated
    ) VALUES (
        %s, %s, %s, %s, %s, %s
    ){};
    """
    if returning:
        statement = statement.format("RETURNING " + returning)
    else:
        statement = statement.format("")

    cursor.execute(
    statement,
    vars=(parent_id, documentid, title, childorder, latest, is_collated)
    )

def remove_tree(cursor, nodeid=[], parent_id=[]):
    cursor.execute("""DELETE FROM trees
                      WHERE nodeid = ANY (%s) OR parent_id = ANY (%s);""",
                   vars=(nodeid, parent_id))


def add_abstract(cursor, abstractid=None, abstract=None, html=None,
                 returning=None):
    statement = """
    INSERT INTO abstracts (abstractid, abstract, html)
    VALUES (%s, %s, %s){};
    """
    args=(abstractid, abstract, html)

    if abstractid == None:
        statement = """
        INSERT INTO abstracts (abstractid, abstract, html)
        VALUES (DEFAULT, %s, %s){};
        """
        args=(abstract, html)

    if returning:
        statement = statement.format("RETURNING " + returning)
    else:
        statement = statement.format("")
    cursor.execute(
    statement,
    vars=args
    )
