ckanext-discovery
#################


Plugins
=======

``solr_query_config``
---------------------
This plugin allows you to set Solr query parameters via entries in CKAN's
`configuration INI`_. You can either specify a default value for a parameter
(which is only used if the parameter isn't already set in the current query)
or you can force a parameter to a certain value (overriding it if it is already
set).

To specify a default value, prefix the parameter name with
``ckanext.discovery.solr.default.``::

    # By default, sort by metadata modification timestamp
    ckanext.discovery.solr.default.sort = metadata_modified asc

Similarly, a value can be forced using the prefix
``ckanext.discovery.solr.force.``::

    # Always use a custom Solr query handler
    ckanext.discovery.solr.force.defType = my_special_query_handler

.. note::

    Only those Solr parameters that are accepted by the package_search_ API
    function can be set via this plugin.

.. _configuration INI: http://docs.ckan.org/en/latest/maintaining/configuration.html#ckan-configuration-file
.. _package_search: http://docs.ckan.org/en/latest/api/index.html#ckan.logic.action.get.package_search

