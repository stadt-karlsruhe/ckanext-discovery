# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from ckan.logic import validate
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.validators import not_missing, not_empty

from .model import SearchQuery
from .. import get_config


log = logging.getLogger(__name__)


def search_suggest_schema():
    return {
        'q': [not_missing, not_empty, unicode]
    }


@toolkit.auth_allow_anonymous_access
def search_suggest_auth(context, data_dict):
    # Allow access by everybody
    return {'success': True}


@toolkit.side_effect_free
@validate(search_suggest_schema)
def search_suggest_action(context, data_dict):
    '''
    Get suggested search queries.
    '''
    log.debug('discovery_search_suggest {!r}'.format(data_dict['q']))
    toolkit.check_access('discovery_search_suggest', context, data_dict)
    limit = get_config('search_suggest.max_suggestions', 5)
    min_score = get_config('search_suggest.min_score', 0)
    terms = data_dict['q'].split()
    return SearchQuery.suggest(terms, limit=limit, min_score=min_score)

