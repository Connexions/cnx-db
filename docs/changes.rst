
.. Use the following to start a new version entry:

   |version|
   ----------------------

   - feature message

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

