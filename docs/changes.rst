
.. Use the following to start a new version entry:

   |version|
   ----------------------

   - feature message

0.10.1
------

- Fix in-collated-book page search sql query (#68)
- Add a matching migration for the double-trigger-when-rebaking fix (#69)
- Fix derived_book_ruleset sql function by returning a value (#67 #66)

0.10.0
------

- Add query to get latest version of the content (#64)
- Use super user to replace plpythonu function in migration (#62)
- Add migration to transform cnxml->html (#59)
- Add delete cascade and indexes for foreign keys (#58)
- Add data migration to update index.cnxml (#61)
- Add trigger for duplicating rulset.css for derived copies (#56)
- Add subcollection uuid data migration (#54)
- Fix minor versions and current_modules view (#49)
- Add xpath queries (#40)

0.9.0
-----

- Add AS_VENV_IMPORTABLE env variable to the pytest db_init fixture.
- Fix load session_exec.so in init_venv before using it.
- Fix order of dependency installation to account for the current circular
  dependence with cnx-archive.
- Fix quoting within the container's initdb script
- Add docker entrypoint script to load database dump.
- Fix Dockerfile initdb.d COPY command.
- Fix requirements filename change in Dockerfile
- Fix rebake trigger to do nothing when the content is already in a bakable
  state.
- Lock latest_modules when running update_latest where two or more inserts may
  happen at the same time.
- Fix update_latest trigger to account for multiple minor versions where one or
  more may have failed during baking.
- Add sql queries for getting books containing a page.

0.8.0
-----

- Add tables and triggers to store recipes associated with print-styles.

0.7.0
-----

- Add association table for celery results to documents.

0.6.0
-----

- Share this project's pytest fixtures for use in dependent projects.
- Create the cnxdb.contrib package.
- Fix to exclude subcollections from the search query.

0.5.4
-----

- Fix to only create the moduletags index when it does not exist.

0.5.3
-----

- Add an index for moduletags to improve search.

0.5.2
-----

- Fix to speedup in-book search for baked content.

0.5.1
-----

- Include a migration for the post_publication channel payload change.

0.5.0
-----

- Add a payload to the post_publication channel notification.
- Fix tests by explicitly including cnx-archive.
- Fix tests to only run trigger tests within Python 2.7.

0.4.0
-----

- Add a Make recipe for building and serving this project/component.
- Correct styling, documentation and test running code.
- Add the Make interface for common developer tasks.
- Install versioneer for version management via git.
- Add SQL function and trigger to rebake on baking recipe insert or update.
- Update SQL manifest to add subcollection uuid SQL functions.

0.3.0
-----

- Adjust SQL functions declarations to idempotent declarations.
- Add SQL functions and indexes for the content ident-hash.

0.2.7
-----

- Fix a relative path within the sub-collection uuid migration.

0.2.6
-----

- Update SQL to include sub-collection uuid schema changes from cnx-archive.

0.2.5
-----

- Make the project db-migrator aware.

0.2.4
-----

- Update SQL to include collated schema changes from cnx-archive.

0.2.3
-----

- Remove localhost venv initialization constraint.

0.2.2
-----

- Update SQL to account for changes in the cnx-publishing project.

0.2.1
-----

- Update SQL to account for changes in the cnx-publishing
  and cnx-archive projects.
- Fix to include schema files in the distribution.

0.2.0
-----

- Add a commandline interface for initializing the database.
- Add a commandline interface for initializing or re-initializing
  the virtualenv within the database.

0.1.1
-----

- Update SQL to account for changes made in the cnx-publishing
  and cnx-archive projects.

0.1.0
-----

- Add functions for initializing the database.
- Merge database schemata from the cnx-publishing and cnx-archive projects.

