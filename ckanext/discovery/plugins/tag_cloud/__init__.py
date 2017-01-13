# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

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
    bins based on their frequency.
    '''
    data_dict = {
        'facet.field': ['tags'],
        'facet.limit': num_tags,
    }
    result = toolkit.get_action('package_search')({}, data_dict)
    tags = sorted(result['facets']['tags'].items(), key=lambda t: (t[1], t[0]))
    return {
        t[0]: math.floor(num_bins * i / len(tags)) + 1 for i, t in enumerate(tags)
    }


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

