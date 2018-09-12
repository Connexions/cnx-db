==========
Change Log
==========

.. Use the following to start a new version entry:

   |version|
   ----------------------

   - feature message

2.3.4
-----

- Fixup function ownership on production DBs (production and synced from there)

2.3.3
-----

- Move html abstract trigger to later event
- make schema restorable
  (cf. https://bucardo.org/postgres_all_versions.html#version_9.3.22
  re: search_path settings)

2.3.2
-----

- Correct trigger to transform abstracts to html from cnxml.
  See https://github.com/Connexions/cnx-db/issues/138

2.3.1
-----

- Add trigger to transform abstracts to html from cnxml.
  See https://github.com/Connexions/cnx-db/issues/138

2.3.0
-----

- Add database indices and modify the fulltext trigger to set different
  weights to tsvectors based on whether they are generated on titles, keywords
  or text.

2.2.1
-----

- Add an index to dramatically speed up `/contents/<book-id>@ver:<pageid>@ver`

2.2.0
-----

- Add a SQL query to obtain the 'head' version of content. The head
  is the last publication made for that content regardless of whether
  it is in a publicly viewable state.

2.1.0
-----

- Adds fulltext search fixes and speedups.

2.0.1
-----

- Fix the documentation for Pyramid integration properties.
- Fix the HTML reference resolver for cases where the moduleid is found
  in the resource filename.

2.0.0
-----

- Transition the following Pyramid integration properties:
  ``registry.engines`` and ``registry.tables``. These are now moved to
  ``request.get_db_engine()`` and ``request.db_tables``.
  This favors the recommended pattern of using request methods and attributes
  for hooking into the current thread local variable space.

1.6.1
-----

- Fix shred_collxml code to insert the ``trees.latest`` value.
  The fix includes a migration to ensure all ``trees.latest`` values are
  set to true, which should be the casee for all legacy content.
  See https://github.com/Connexions/cnx-db/issues/120 for issue details.

1.6.0
-----

- Pin to a specific version of sesssion_exec when testing.
- Allow the Google Analytics (GA) code column to stay the same type,
  but contain multiple GA codes. Adjustments to queries make this
  an array of GA codes based on space separated list of codes.
- Adjust the books containing this page query to:
  - Provide a sorted list of authors and the detailed person info
  - Provide the shortid

1.5.1
-----

- Remove the ``DB_NAME`` environment variable from the container definition.
  This appears to have become redundant with the ``POSTGRES_DB`` variable.
- Fix .dockerfiles/initdb.d/00_initdb.sh to look for ``*.sql``
  and ``*.sql.gz`` files in the docker entrypoint directory rather than
  the current working directory.

1.5.0
-----

- Simplify slim dump import into docker container

  - Rename .dockerfiles/initdb.d/initdb.sh to 00_initdb.sh
  - Don't run cnx-db init if ``*.sql`` or ``*.sql.gz`` exist
  - Remove .dockerfiles/initdb.d/load_database_dump.sh
  - Set POSTGRES_DB to the same as DB_NAME

- Add the baked and print-style columns to the module metadata query.

1.4.0
-----

- Massage testing fixtures to better facilitate testing in packages using
  this package.

  - Provide additional init and wipe fixtures scoped at the module level.
  - Remove custom function for table name lookup. Replaced by sqlalchemy
    Inspector methods.
  - Add a ``db_tables`` pytest fixture that supplies sqlalchemy table objects.

1.3.0
-----

- Add a new baking state, known as 'fallback', that allows content
  to remain in a success state even when the latest print-style
  won't work with the content.
- Fix the primary key on the ``print_style_recipes`` table.
- Provide docs for using the Pyramid Web Framework with this package.
- Add a database tables definition to the pyramid integration.
  This places a ``tables`` attribute on the registry.
  The attribute contains sqlalchemy table definitions that are reflected
  from the existing database schema.

1.2.0
-----

- Fix settings discovery to use the given settings value for 'db.common.url'
  when the ``DB_URL`` environment variable is undefined.
- Add a read-only database setting to allow for read-only database
  connections. The setting is available through the ``DB_READONLY_URL``
  environment variable.

1.1.0
-----

- Touchup the docstrings for database init funcs (#99)
- Add an integration point for the pyramid web framework (#98)
- Update documentation headers and contrib module api docs (#97)

1.0.0
-----

- Migrate transform triggers logic to this package from cnx-archive (#86)
- Ignore artifacts of running ci_test_migrations.sh
- Run non-continous integration runs of ci_test_migration.sh quietly
- Fix docker-compose to use env vars

0.12.0
------

- Change pg_dump to use $DB_URL in ci_test_migrations
- Change dbmigrator commands to use $DB_URL in ci_test_migrations
- Use $DB_URL in ci_test_migrations.sh
- Fix triggers test to use raw connection string
- Remove all connection string uses in favor of URL
- Move to using a URL rather than connection string
- Add prepare function for scripting env preparation
- Add a function to discover environment settings
- a view of all most recent content, regardless of baked state
- Correct code coverage configuration (#94)
- Ignore linting of build and dist directories (#89)
- Wrap lines in docs/changes.rst (#90)

0.11.0
------

- In book search to provide query_type parameterization for AND vs OR queries
  (#87)
- Fix number of migrations to rollback in ci_test_migrations.sh
- get only the highest version for each book a page is in, return full
  ident_hash, as well as authors. Put same-as-page-authors first, since this is
  likely to be the orginal book the page was published in.  Returned as list of
  hashes in page content-extras
- Correct project testing requirements to also use main.txt (#85)
- Fix update latest trigger not adding new modules
- make in book search OR terms, rather than AND them
- do not use timestamps to determine latest content (#75)
- Add migration for print_style_recipes (#80)
- Make lexeme removal migration idempotent (#82)
- Fix print_style_recipe trigger definition to align with the migration (#81)
- Provide book full text search (#78)

0.10.4
------

- Revert changes to triggers for derived content

  - Remove fix for derived_book_ruleset sql function by returning
    a value (#67)
  - Remove addition of trigger for duplicating rulset.css for derived
    copies (#56)

0.10.3
------

- Fix to ignore stateid when copying subcollections to avoid adding
  subcollections to the post-publication queue (#73)

0.10.2
------

- Use postgres super user in migrations that require it (#71)
- Correct errors in subcol uuid migration associated with an empty batch (#70)

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
