ckanext-discovery
#################

Installation
============
FIXME


Plugins
=======

``solr_query_config``
+++++++++++++++++++++
This plugin allows you to set Solr query parameters via entries in CKAN's
`configuration INI`_. You can either specify a default value for a parameter
(which is only used if the parameter isn't already set in the current query)
or you can force a parameter to a certain value (overriding it if it is already
set).

Installation
------------
Simply add ``solr_query_config`` to the list of plugins in CKAN's
`configuration INI`_::

    plugins = ... solr_query_config

Configuration
-------------
To specify a default value, prefix the parameter name with
``ckanext.discovery.solr.default.``::

    # By default, sort by metadata modification timestamp
    ckanext.discovery.solr.default.sort = metadata_modified asc

Similarly, a value can be forced using the prefix
``ckanext.discovery.solr.force.``::

    # Always use a custom Solr query handler
    ckanext.discovery.solr.force.defType = my_special_query_handler

Note that only those Solr parameters that are accepted by the package_search_
API function can be set via this plugin.


``similar_datasets``
++++++++++++++++++++
This plugin displays a list of similar datasets in the sidebar of the dataset
view:

.. image:: doc/similar_datasets.png
    :alt: Screenshot of the similar_datasets plugin

Installation
------------
The plugin relies on Solr's `More Like This`_ feature and requires that you
configure your Solr instance appropriately. In particular, you need to set up a
MoreLikeThisHandler_ in your ``/etc/solr/conf/solrconfig.xml``. To do this, add
the following code block directly before the ``</config>`` tag at the end of
the file::

    <requestHandler name="/mlt" class="solr.MoreLikeThisHandler">
        <lst name="defaults">
            <int name="mlt.mintf">3</int>
            <int name="mlt.mindf">1</int>
            <int name="mlt.minwl">3</int>
        </lst>
    </requestHandler>

Please refer to the documentation of the MoreLikeThisHandler_ for details on
its configuration.

In addition, you need to enable `term vector storage`_ for the ``text`` field
in your ``/etc/solr/conf/schema.xml``. To do this, locate the following field
definition::

    <field name="text" type="text" indexed="true" stored="false" multiValued="true" />

Then add ``termVectors="true"`` to the list of attributes so that the full
definition looks like this::

    <field name="text" type="text" indexed="true" stored="false" multiValued="true" termVectors="true" />

Please note that term vectors can substantially increase the size of your
Solr index.

Once you have updated your ``solrconfig.xml`` and ``schema.xml`` files as
described above you need to restart Solr. Assuming you're using Jetty, this
is done via

::

    sudo service jetty restart

Finally you need to re-index your datasets once, so that the term vectors of
the existing datasets are stored (for datasets that are added or updated in the
future this is done automatically)::

    . /usr/lib/ckan/default/bin/activate
    paster --plugin=ckan search-index rebuild -c /etc/ckan/default/production.ini

You can now add ``similar_datasets`` to your list of plugins in CKAN's
`configuration INI`_::

    plugins = ... similar_datasets

After restarting CKAN the list of similar datasets should be displayed on the
detailed view of each dataset::

    sudo service apache2 restart


Configuration
-------------
The plugin offers two settings that can be configured in CKAN's
`configuration INI`_::

    # Maximum number of similar datasets to list. Defaults to 5. Note that less
    # datasets may be shown if Solr doesn't find enough similar datasets.
    ckanext.discovery.similar_datasets.max_num = 3

    # Minimum similarity score. Similar datasets for which Solr reports a lower
    # similarity score are not shown. Defaults to 0, which means that all
    # documents returned by Solr are shown.
    ckanext.discovery.similar_datasets.min_score = 0.6


.. _configuration INI: http://docs.ckan.org/en/latest/maintaining/configuration.html#ckan-configuration-file
.. _package_search: http://docs.ckan.org/en/latest/api/index.html#ckan.logic.action.get.package_search
.. _More Like This: https://cwiki.apache.org/confluence/display/solr/MoreLikeThis
.. _MoreLikeThisHandler: https://cwiki.apache.org/confluence/display/solr/MoreLikeThis#MoreLikeThis-ParametersfortheMoreLikeThisHandler
.. _term vector storage: https://cwiki.apache.org/confluence/display/solr/Field+Type+Definitions+and+Properties#FieldTypeDefinitionsandProperties-FieldDefaultProperties

