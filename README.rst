ckanext-discovery
#################

Installation
============
FIXME


Plugins
=======
This extension provides multiple plugins:

* search_suggestions_: Provides real-time search suggestions in a drop-down
  box
* similar_datasets_: Adds a list of similar datasets to the dataset detail view
* solr_query_config_: Allows you to easily override the parameters that CKAN
  passes to Solr
* tag_cloud_: Replaces the list of frequent tags on the home page with a tag
  cloud that shows the most popular tags scaled according to their popularity

In addition there is the discovery_ plugin which doesn't provide additional
functionality on its own but contains shared utilities required by the other
plugins.

``discovery``
+++++++++++++
This plugin doesn't provide any direct functionallity on its own but contains
utilities required by the other plugins. It is therefore required that you
activate it in CKAN's `configuration INI`_ if you want to use any other plugin
of this extension::

    plugins = ... discovery


``search_suggestions``
++++++++++++++++++++++
This plugin provides real-time search suggestions while the user is entering
text into a search field:

.. image:: doc/search_suggestions.png
    :alt: Screenshot of the search_suggestions plugin

Installation
------------
First add ``discovery`` and ``search_suggestions`` to the list of plugins in
CKAN's `configuration INI`_::

    plugins = ... discovery search_suggestions

Then create the necessary database tables::

    . /usr/lib/ckan/default/bin/activate
    paster --plugin=ckanext-discovery search_suggestions init -c /etc/ckan/default/production.ini

Finally, restart CKAN::

    sudo service apache2 restart

Usage
-----
The suggestions are generated from previous searches by other users. The plugin
therefore combines two functionalities:

1. Automatic collection of statistics about the users' search queries
2. Generation and display of search suggestions

Regarding the first point it is important to point out that search queries are
stored in a post-processed form and without any reference to the corresponding
user.

Search suggestions are automatically enabled on all search fields that CKAN
provides in its base templates, namely the search box on the home page, the
search field in the header, and the search box at ``/dataset``. In addition,
any HTML element with the class ``search`` will also automatically display
search suggestions.

Obviously suggestions are only provided once some search queries have been
recorded.

Configuration
-------------
The plugin offers multiple settings that can be configured via CKAN's
`configuration INI`_::

    # Maximum number of search suggestions to display in the drop-down
    # box. Defaults to 4. Note that fewer suggestions may be listed if not
    # enough related queries have been stored before.
    ckanext.discovery.search_suggestions.limit = 4

    # Whether data about search queries should be stored. Defaults to true.
    ckanext.discovery.search_suggestions.store_queries = True

    # Whether search suggestions should be displayed. Defaults to true.
    ckanext.discovery.search_suggestions.provide_suggestions = True

Query Filtering
---------------
Since this plugin displays texts input by one user to other users there is a
certain risk that unwelcome content may find its way into the suggestions. The
plugin provides the interface ``ISearchHistoryFilter`` whose
``filter_search_query`` method can be used to decide whether a given query
should be stored. You can implement this interface in another plugin and apply
a custom filter::

    import ckan.plugins as plugins
    from ckanext.discovery.plugins.search_suggestions import ISearchHistoryFilter

    # We don't want people to talk about dogs here!
    BAD_WORDS = {'dog', 'puppy'}

    class MyPlugin(plugins.SingletonPlugin):
        plugins.implements(ISearchHistoryFilter)


        def filter_search_query(self, query):
            '''
            Decide whether a search query should be stored.

            ``query`` is a set of normalized search terms extracted from a
            user's search query.

            If this method returns a true value then the query terms are
            stored and may be presented to other users as part of future
            search suggestions. If this method returns a false value then
            the query is not stored. The search itself has already taken
            place when this method is called and is not affected by it.
            '''
            if query.intersection(BAD_WORDS):
                # Ugh, dog talk! Don't store the query.
                return False

            # No one mentioned dogs, so we can safely store this query.
            return True


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

Now add ``discovery`` and ``similar_datasets`` to your list of plugins in
CKAN's `configuration INI`_::

    plugins = ... discovery similar_datasets

After restarting CKAN the list of similar datasets should be displayed on the
detailed view of each dataset::

    sudo service apache2 restart

Configuration
-------------
The plugin offers two settings that can be configured in CKAN's
`configuration INI`_::

    # Maximum number of similar datasets to list. Defaults to 5. Note that less
    # datasets may be shown if Solr doesn't find enough similar datasets.
    ckanext.discovery.similar_datasets.max_num = 5

    # Minimum similarity score. Similar datasets for which Solr reports a lower
    # similarity score are not shown. Defaults to 0, which means that all
    # documents returned by Solr are shown.
    ckanext.discovery.similar_datasets.min_score = 0


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

Then restart CKAN::

    sudo service apache2 restart

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


``tag_cloud``
+++++++++++++
This plugin shows links for the most frequent tags scaled according to their
frequency:

.. image:: doc/tag_cloud.png
    :alt: Screenshot of the tag_cloud plugin

Installation
------------
Simply add ``discovery`` and ``tag_cloud`` to the list of plugins in CKAN's
`configuration INI`_::

    plugins = ... discovery tag_cloud

Then restart CKAN::

    sudo service apache2 restart

Usage
-----
The plugin automatically replaces the list of the most frequent tags on CKAN's
default front page with a tag cloud.

If you want to use the tag cloud in a different part of the site you can use
the following `template snippet`_::

    {% snippet 'ckanext-discovery/snippets/tag_cloud.html', num_tags=10 %}

The ``num_tags`` specifies the number of tags in the tag cloud. It is optional
and defaults to the setting of the ``ckanext.discovery.tag_cloud.num_tags``
option (see below).

Configuration
-------------
The plugin offers one setting that can be configured via CKAN's
`configuration INI`_::

    # Number of tags to show in the tag cloud. Defaults to 20 and can be
    # overriden by passing a ``num_tags`` parameter to the tag cloud template
    # snippet.
    ckanext.discovery.tag_cloud.num_tags = 20


.. _configuration INI: http://docs.ckan.org/en/latest/maintaining/configuration.html#ckan-configuration-file
.. _package_search: http://docs.ckan.org/en/latest/api/index.html#ckan.logic.action.get.package_search
.. _More Like This: https://cwiki.apache.org/confluence/display/solr/MoreLikeThis
.. _MoreLikeThisHandler: https://cwiki.apache.org/confluence/display/solr/MoreLikeThis#MoreLikeThis-ParametersfortheMoreLikeThisHandler
.. _term vector storage: https://cwiki.apache.org/confluence/display/solr/Field+Type+Definitions+and+Properties#FieldTypeDefinitionsandProperties-FieldDefaultProperties
.. _template snippet: http://docs.ckan.org/en/latest/theming/templates.html#snippets

