.. Connexions Database Library documentation master file, created by
   sphinx-quickstart on Tue Mar 22 15:31:49 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Connexions Database Library
===========================

.. image:: https://travis-ci.org/Connexions/cnx-db.svg
   :target: https://travis-ci.org/Connexions/cnx-db

.. image:: https://coveralls.io/repos/Connexions/cnx-db/badge.png?branch=master
   :target: https://coveralls.io/r/Connexions/cnx-db?branch=master

.. image:: https://badge.fury.io/py/cnx-db.svg
   :target: http://badge.fury.io/py/cnx-db

Contents:

.. toctree::
   :maxdepth: 2

   usage
   api


Installation
------------

Install using one of the following methods (run within the project root)::

    python setup.py install

Or::

    pip install .

Usage
-----

Initialize an database::

    cnx-db init [-h host] [-p port] -d dbname -U user

.. todo:: Deprecate ``cnx-archive-initdb`` in favor of ``cnx-db init ...``.

.. todo:: This may become part of ``dbmigrator init`` or ``dbmigrator migrate``
          in the future.

Testing
-------

The tests require access to a blank database named ``testing``
with the user ``tester`` and password ``tester``. This can easily
be created using the following commands::

    psql -c "CREATE USER tester WITH SUPERUSER PASSWORD 'tester';"
    createdb -O tester testing

The tests can then be run using::

    python setup.py test

Or::

    pip install pytest  # only run once to install dependency
    py.test

Or, to run multiple versions of python::

    pip install tox  # only run once to install dependency
    tox

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2016 Rice University


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

