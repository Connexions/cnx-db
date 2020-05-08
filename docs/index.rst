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

Testing with Docker and Docker Compose (recommended)
----------------------------------------------------

Requirements:

- Install `Docker <https://docs.docker.com/install/>`_
- Install `docker-compose <https://docs.docker.com/compose/install/>`_

To help with installation of packages this project also comes with a
``Dockerfile`` and ``docker-compose.yml`` file.

To run the tests in the test suite execute the following script:

.. code-block:: bash

   $ ./script/tests.local.sh

This should build and run the tests within your local docker container
environment.

The commands being executed are named explicitly so the developer can tell what
is happening.

.. note::
   The script uses ``Makefile.docker`` located in the root of the project. This
   file was created to separate concerns from the main Makefile. The main
   Makefile creates virtualenvs and manages a ``.state`` directory which are
   not things to be concerned about when operating within the docker container.
   To not break any of that functionality it was decided to separate actions
   needed to be taken within the container.

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

