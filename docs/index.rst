.. Connexions Database Library documentation master file, created by
   sphinx-quickstart on Tue Mar 22 15:31:49 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Connexions Database Library
===========================

Installation
------------

Install using::

    pip install cnx-db

Development
-----------

For all things development, use the Makefile::

    make help

Usage
-----

Initialize an database::

    export DB_URL=postgresql:///repository
    cnx-db init

.. todo:: This may become part of ``dbmigrator init`` or ``dbmigrator migrate``
          in the future.

For application and scripting usage information, see :ref:`usage_chapter`.

Testing
-------

The tests require access to a blank database named ``testing``
with the user ``tester`` and password ``tester``. This can easily
be created using the following commands::

    psql -c "CREATE USER tester WITH SUPERUSER PASSWORD 'tester';"
    createdb -O tester testing

The tests can then be run using::

    make test

Or::

    pip install -r requirements/test.txt
    py.test

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2017 Rice University


Contents
========

.. toctree::
   :maxdepth: 2

   config
   usage
   triggers
   api
   changes



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

