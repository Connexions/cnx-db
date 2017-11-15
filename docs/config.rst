.. _configuration_chapter:

=============
Configuration
=============

The application is configured via environment variables.
The following application settings are mapped to environment variables.

===============================  ======================  =============
Setting                          Env Variable            Required?
===============================  ======================  =============
``db.common.url``                ``DB_URL``              yes
``db.readonly.url``              ``DB_READONLY_URL``     no
``db.super.url``                 ``DB_SUPER_URL``        no
===============================  ======================  =============

The settings are programattically obtained via
:func:`cnxdb.config.discover_settings`.
