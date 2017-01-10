# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config


log = logging.getLogger(__name__)


class SolrQueryConfigPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)

    CONFIG_PREFIX = 'ckanext.discovery.solr.'
    DEFAULT_PREFIX = CONFIG_PREFIX + 'default.'
    FORCE_PREFIX = CONFIG_PREFIX + 'force.'

    def before_search(self, params):
        for key, value in config.iteritems():
            if key.startswith(self.DEFAULT_PREFIX):
                key = key[len(self.DEFAULT_PREFIX):]
                try:
                    log.debug(('Search parameter "{}" is already set to '
                              + '"{}"').format(key, params[key]))
                except KeyError:
                    log.debug(('Setting search parameter "{}" to default '
                              + 'value "{}" (previously not set)').format(key,
                              value))
                    params[key] = value
            elif key.startswith(self.FORCE_PREFIX):
                key = key[len(self.FORCE_PREFIX):]
                log.debug(('Setting search parameter "{}" to "{}" (previous '
                          + 'value "{}")').format(key, value, params.get(key,
                          '')))
                params[key] = value
        return params

