# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ckan.common import config


def get_config(key, default=None):
    '''
    Get a configuration value.

    The key is automatically prefixed with ``ckanext.discovery.``.
    '''
    return config.get('ckanext.discovery.' + key, default)

