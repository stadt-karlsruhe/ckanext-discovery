# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os.path
import sys

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation

from . import get_config


log = logging.getLogger(__name__)


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

