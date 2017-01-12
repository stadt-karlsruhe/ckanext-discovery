# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os.path
import sys

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
from ckan.lib.plugins import DefaultTranslation


log = logging.getLogger(__name__)


def get_config(key, default=None):
    '''
    Get a configuration value.

    The key is automatically prefixed with ``ckanext.discovery.``.
    '''
    return config.get('ckanext.discovery.' + key, default)


class DiscoveryPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.ITranslation)

    #
    # ITemplateHelpers
    #

    def get_helpers(self):
        return {
            'discovery_get_config': get_config,
        }

    #
    # ITranslation
    #

    def i18n_directory(self):
        module = sys.modules['ckanext.discovery']
        module_dir = os.path.abspath(os.path.dirname(module.__file__))
        return os.path.join(module_dir, 'i18n')

    def i18n_domain(self):
        return 'ckanext-discovery'

