# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from .. import get_config


log = logging.getLogger(__name__)


def get_language():
    '''
    Get language for text search.

    Returns the value of the configuration setting
    ``ckanext.discovery.search_suggestions.language`` or ``'english'``
    if that option is not set.
    '''
    return get_config('search_suggestions.language', 'english')

