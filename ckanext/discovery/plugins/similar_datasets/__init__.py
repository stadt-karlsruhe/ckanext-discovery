# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import json

from ckan.common import config
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.search.common import make_connection

from .. import Translation


log = logging.getLogger(__name__)


def get_similar_datasets(id, max_num=5, min_score=0):
    '''
    Get similar datasets for a dataset.

    :param string id: ID of the target dataset. This must be the actual
        ID, passing the name is not supported.

    :param int max_num: Maximum number of datasets to return.

    :param float min_score: Minimum required score. Similar datasets
        returned by Solr that have a lower score will be ignored.

    :return: A list of similar dataset dicts sorted by decreasing score.
    '''
    solr = make_connection()
    query = 'id:"{}"'.format(id)
    fields_to_compare = 'text'
    fields_to_return = 'id validated_data_dict score'
    results = solr.more_like_this(q=query,
                                  mltfl=fields_to_compare,
                                  fl=fields_to_return,
                                  rows=max_num)
    log.debug('Similar datasets for {}:'.format(id))
    for doc in results.docs:
        log.debug('  {} (score {})'.format(doc['id'], doc['score']))
    docs = [doc for doc in results.docs if doc['score'] >= min_score]
    return [json.loads(doc['validated_data_dict']) for doc in docs]


def get_config(key, default=None):
    '''
    Get a configuration value.

    The key is automatically prefixed with ``ckanext.discovery.``.
    '''
    return config.get('ckanext.discovery.' + key, default)


class SimilarDatasetsPlugin(plugins.SingletonPlugin, Translation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

    #
    # IConfigurer
    #

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')

    #
    # ITemplateHelpers
    #

    def get_helpers(self):
        return {
            'discovery_similar_datasets': get_similar_datasets,
            'discovery_get_config': get_config,
        }

