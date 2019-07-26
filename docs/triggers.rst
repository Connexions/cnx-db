=================
Database Triggers
=================

Here lies information about the Database Triggers.
Here be dragons and other things that will gobble you up.


The triggers (in no particular order):

- :ref:`update_latest_version`
- :ref:`delete_from_latest_version`
- :ref:`post_publication_trigger`
- :ref:`act_10_module_uuid_default`
- :ref:`act_20_module_acl_upsert`
- :ref:`act_80_legacy_module_user_upsert`
- :ref:`module_moduleid_default`
- :ref:`module_published`
- :ref:`module_version_default`
- :ref:`collection_html_abstract_trigger`
- :ref:`module_html_abstract_trigger`
- :ref:`optional_roles_user_insert`
- :ref:`update_file_md5`
- :ref:`update_files_sha1`
- :ref:`module_file_added`
- :ref:`ruleset_trigger`
- :ref:`update_default_recipes`
- :ref:`delete_from_default_recipes`
- :ref:`set_default_canonical_trigger`
- :ref:`update_users_from_legacy`
- :ref:`update_default_modules_stateid`


First acting triggers
---------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``

These ``act_##_...`` prefixed triggers are the first triggers
to run on insert to the ``modules`` table.
They are named with this prefix
to ensure they are the first
to run and in a specific numbered order.

.. _act_10_module_uuid_default:

Set the default module UUID
^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``act_10_module_uuid_default``

This trigger runs:

.. autofunction:: cnxarchive.database.assign_document_controls_default_trigger


.. _act_20_module_acl_upsert:

Update the module ACLs
^^^^^^^^^^^^^^^^^^^^^^

:name: ``act_20_module_acl_upsert``

This trigger runs:

.. autofunction:: cnxarchive.database.upsert_document_acl_trigger


.. _act_80_legacy_module_user_upsert:

Upsert users during Legacy publications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``act_80_legacy_module_user_upsert``

This trigger runs:

.. autofunction:: cnxarchive.database.upsert_users_from_legacy_publication_trigger


User shadowing
--------------

.. _optional_roles_user_insert:

Upsert users for optional roles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``optional_roles_user_insert``

This trigger runs:

.. autofunction:: cnxarchive.database.insert_users_for_optional_roles_trigger


.. _update_users_from_legacy:

Copy records from persons to users table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:defined-in: ``cnxdb/archive-sql/schema/legacy/triggers.sql``
:name: ``update_users_from_legacy``

This trigger ensures that insertions and updates to the ``persons`` table
are copied (or shadowed) over to the ``users`` table.


Set defaults
------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``


.. _module_moduleid_default:

Set the default Module ID
^^^^^^^^^^^^^^^^^^^^^^^^^

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``module_moduleid_default``

This trigger runs:

.. autofunction:: cnxarchive.database.assign_moduleid_default_trigger


.. _module_version_default:

Set the default Module version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``module_version_default``

This trigger runs:

.. autofunction:: cnxarchive.database.assign_version_default_trigger


.. _update_default_modules_stateid:

Set the default module state for legacy publications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:defined-in: ``cnxdb/archive-sql/schema/legacy/triggers.sql``
:name: ``update_default_modules_stateid``

Sets the default *state* to *post-publication* (``stateid = 5``) for insertions
into the ``modules`` table
that is classified as a Collection (i.e. ``portal_type = 'Collection'``).

Set values for computed fields
------------------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``

.. _update_file_md5:

Computer the MD5 hash
^^^^^^^^^^^^^^^^^^^^^

:name: ``update_file_md5``

Computes and sets the MD5 hash on insert or update to the ``files`` table.

.. _update_files_sha1:

Computer the SHA1 hash
^^^^^^^^^^^^^^^^^^^^^^

:name: ``update_files_sha1``

Computes and sets the SHA1 hash on insert or update to the ``files`` table.

.. _module_published:

Republish Collections sharing a published Module
------------------------------------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``module_published``

This trigger runs:

.. autofunction:: cnxarchive.database.republish_module_trigger


Transformation triggers
-----------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``

.. _collection_html_abstract_trigger:

Transform a Collection's abstract to HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``collection_html_abstract_trigger``

This triggers run on Collection insert or update
when a module does not have an HTML abstract.
The results of this trigger are
to transform the cnxml or plain text abstract to HTML.

.. _module_html_abstract_trigger:

Transform a Module's abstract to HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``module_html_abstract_trigger``

This triggers run on Module insert or update
when a module does not have an HTML abstract.
The results of this trigger are
to transform the cnxml or plain text abstract to HTML.

.. _module_file_added:

Transform a Module's document to or from CNXML to HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``module_file_added``

.. autofunction:: cnxarchive.database.add_module_file


.. _update_latest_version:

Update latest version
---------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``update_latest_version``

Copies the record from ``modules`` to ``latest_modules``
on insert or update when the highest version of a module has successfully baked.
A module is considered successfully baked
when its *state* has transitioned
to *current* (``stateid = 1``) or *fallback* (``stateid = 8``).

.. _delete_from_latest_version:

Delete latest version
---------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``delete_from_latest_version``

Copies the previous latest record from ``modules`` to ``latest_modules``
on deletion of the existing ``latest_modules`` record with the same ID.

.. note:: As of this writing, this trigger is not baking aware. (bug!)

.. _post_publication_trigger:

Post Publication Trigger
------------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``post_publication_trigger``

Notifies the ``post_publication`` channel
on insert or update to the ``modules`` table
when the module's ``state`` has been set to **post-publication**
(``stateid = 5``).

.. hint:: The ``post_publication`` channel is observed
          by cnx-publishing's *channel processing* script,
          which listens for events and places them into RabbitMQ.

Recipes Triggers
----------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``

.. _ruleset_trigger:

Rebake on recipe insertion
^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``ruleset_trigger``

When a recipe is manually inserted (or injected)
into the database this trigger "rebakes" the content.
This trigger is active on the ``module_files`` table
when a file named ``ruleset.css`` (aka recipe) is inserted or updated,
which in turn executes the procedure to "rebake" the associated content.

.. _update_default_recipes:

Set the default recipe
^^^^^^^^^^^^^^^^^^^^^^

:name: ``update_default_recipes``

When a new recipe is inserted (or old one updated)
this trigger ensures the ``default_print_style_recipes`` table updated
to with the latest revised recipe.
This also ensures that a recipe is not overwritten
if it is currently in use by one or more books (aka Collections).

.. _delete_from_default_recipes:

Prevent deletion of used recipes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:name: ``delete_from_default_recipes``

Prevents deletion of recipes in the ``print_style_recipes`` table
if the recipe is in use
(therefore is a recipe that has been used in baking book).
If the recipe being deleted is in ``default_print_style_recipes``
it will be replaced with the next newest available recipe.

.. _set_default_canonical_trigger:

Set the default canonical Collection for a Module
-------------------------------------------------

:defined-in: ``cnxdb/archive-sql/schema/triggers.sql``
:name: ``set_default_canonical_trigger``

This trigger finds the first Collection containing the Module
and sets it as the canonical value.
