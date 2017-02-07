# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import math
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config


log = logging.getLogger(__name__)


def bin_tags(num_tags=20, num_bins=5):
    '''
    Distribute tags into bins according to their frequency.

    Returns a dict with top ``num_tags`` tags, assigned to ``num_bins``
    bins based on their frequency. Each tag is mapped to a value between
    ``1`` and ``num_bins`` (inclusively).
    '''
    data_dict = {
        'facet.field': ['tags'],
        'facet.limit': num_tags,
    }
    result = toolkit.get_action('package_search')({}, data_dict)

    tags_by_count = collections.defaultdict(list)
    for tag, count in result['facets']['tags'].iteritems():
        tags_by_count[count].append(tag)
    tags_by_count = sorted(tags_by_count.iteritems(), key=lambda t: t[0])
    log.debug('tags_by_count: {}'.format(tags_by_count))

    bins = {}
    for i, (count, tags) in enumerate(tags_by_count):
        bin = int(math.floor(num_bins * i / len(tags_by_count))) + 1
        for tag in tags:
            bins[tag] = bin
    return bins


class TagCloudPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    #
    # IConfigurer
    #

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        # See https://github.com/ckan/ckan/issues/3397 for `b` prefixes
        toolkit.add_resource(b'fanstatic', b'discovery_tag_cloud')

    #
    # ITemplateHelpers
    #

    def get_helpers(self):
        return {
            'discovery_bin_tags': bin_tags,
        }

