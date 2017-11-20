.. _usage_chapter:

=====
Usage
=====

Some facts about this library:

  - setup from a CRUD (Create Read Update Delete) perspective
  - lightly setup as a pyramid extension / add-on
  - minimally uses the component architecture (`zope.interface <https://pypi.python.org/pypi/zope.interface>`_)

.. _scripting_usage:

Scripting Usage
===============

Occasionally, a script or application will need to utilize the database in
a one off way. The :func:`cnxdb.scripting.prepare` function has been created
to prepare an environment for work with the database. It pulls from the same
configuration as the application would. The resulting dictionary contains
the discovered settings, a dict of database engines
(`sqlalchemy.engine.Engine` instances) and a closer function.

The settings information comes from the documented means of configuration.
See :ref:`configuration_chapter` for details.

The engines are created using the settings. The dictionary is keyed
by the purpose of the needed connection.
For example, the use of ``engines['super']`` will give you
a superuser connection.

The closer function is used to safely close the process without leaving
hanging connections and/or communications.

This design of this feature is modeled after `pyramid.scripting.prepare`.

Script Example
--------------

.. code-block:: python
   :linenos:
   :emphasize-lines: 4-6,12

   from cnxdb.scripting import prepare

   def print_latest_publication():
      env = prepare()
      print("working with the following settings: {}".format(env['settings']))
      conn = env['engines']['common'].raw_connection()
      with conn:
          with conn.cursor() as cursor:
              cursor.execute("select uuid from latest_modules "
                             "order by revised desc")
              print(cursor.fetchone()[0])
      env['closer']()

   if __name__ == '__main__':
       print_latest_publication()

This script prints the UUID of the latest publication. It utilizes all three
of the ``env`` values: ``settings``, ``engines`` and ``closer``.

For other examples, have a look at :mod:`cnxdb.cli.subcommands`.

.. _pyramid_usage:

Pyramid Application Usage
=========================

This package can be integrated with a `Pyramid Web Framework
<http://docs.pylonsproject.org/projects/pyramid/en/latest/>`_
based application.
For exmaple, the following includes this package
using the imperative configuration style:

.. code-block:: python
   :linenos:
   :emphasize-lines: 6

   from pyramid.config import Configurator

   def app():
       config = Configurator()
       # ...
       config.include('cnxdb.contrib.pyramid')
       # ...
       return config.make_wsgi_app()

This will give you access to the ``engines`` and ``tables`` attributes
on the registry.
The ``engines`` attribute is a dictionary of SQLAlchemy Engine objects.
The ``tables`` object contains references SQLAlchemy Table objects
that have been created from the database through inspection.
