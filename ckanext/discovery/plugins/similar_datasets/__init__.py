# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import json

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.search.common import make_connection
from ckan.common import config


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
    site_id = config.get('ckan.site_id')
    filter_query = '+site_id:"{}" +dataset_type:dataset'.format(site_id)
    results = solr.more_like_this(q=query,
                                  mltfl=fields_to_compare,
                                  fl=fields_to_return,
                                  fq=filter_query,
                                  rows=max_num)
    log.debug('Similar datasets for {}:'.format(id))
    print('Similar datasets for {}:'.format(id))
    for doc in results.docs:
        log.debug('  {id} (score {score})'.format(**doc))
        print('  {id} (score {score})'.format(**doc))
    docs = [doc for doc in results.docs if doc['score'] >= min_score]
    return [json.loads(doc['validated_data_dict']) for doc in docs]


class SimilarDatasetsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

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
        }

