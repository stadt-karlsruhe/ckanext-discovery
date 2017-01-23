# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import re

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.model.meta import Session

from .model import SearchTerm, CoOccurrence
from .interfaces import ISearchHistoryFilter
from .. import get_config


log = logging.getLogger(__name__)


def split_query(q):
    '''
    Split a search query into normalized words.

    ``q`` is a search query as a string.

    Returns a list of strings.

    During normalization, the query is converted to lower-case and all
    characters that are neither letters, digits, or intra-word hyphens
    are replaced by spaces. The resulting string is split on whitespace.
    '''
    q = q.lower()
    q = re.sub(r'[^\w-]', ' ', q, flags=re.UNICODE)
    q = q.replace('_', ' ')  # Because _ is in \w
    q = re.sub(r'(?<!\w)-', ' ', q, flags=re.UNICODE)
    q = re.sub(r'-(?!\w)', ' ', q, flags=re.UNICODE)
    return q.split()


def store_query(q):
    '''
    Store a search query in the database.

    ``q`` is a search query as a string.

    All implementations of ``ISearchHistoryFilter.filter_search_query``
    are called before the query is stored. If one of them returns a
    false value then the query is not stored.
    '''
    words = set(split_query(q))
    for plugin in plugins.PluginImplementations(ISearchHistoryFilter):
        if not plugin.filter_search_query(words):
            log.debug(('The search query "{}" was rejected by a '
                      + 'filter.').format(q))
            return
    log.debug('Remembering user search query "{}"'.format(q))
    terms = sorted(SearchTerm.get_or_create(term=t) for t in words)
    for i, term1 in enumerate(terms):
        term1.count += 1
        for term2 in terms[i + 1:]:
            CoOccurrence.get_or_create(term1=term1, term2=term2).count += 1
    Session.commit()


def _is_user_text_search(context, query):
    '''
    Decide if a search query is a user-initiated text search.
    '''
    # See https://github.com/ckan/ckanext-searchhistory/issues/1#issue-32079108
    try:
        if (
            context.controller != 'package'
            or context.action != 'search'
            or (query or '').strip() in (':', '*:*')
        ):
            return False
    except TypeError:
        # Web context not ready. Happens, for example, in paster commands.
        return False
    return True


class SearchSuggestionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    #
    # IConfigurer
    #

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        # See https://github.com/ckan/ckan/issues/3397 for `b` prefixes
        toolkit.add_resource(b'fanstatic', b'discovery_search_suggestions')

    #
    # IPackageController
    #

    def after_search(self, search_results, search_params):
        if not toolkit.asbool(get_config('search_suggestions.store_queries',
                              True)):
            return search_results
        try:
            q = search_params['q']
            if not _is_user_text_search(toolkit.c, q):
                return search_results
            # TODO: If a user performs a text-based search and then
            # continuously refines the result via facets then we end up with
            # many entries for basically the same search, which might screw up
            # our scoring.
            store_query(q)
        except Exception:
            # Log exception but don't cause search request to fail
            log.exception('An exception occurred while storing a search query')
        return search_results

    #
    # IActions
    #

    def get_actions(self):
        from .action import search_suggest_action
        return {
            'discovery_search_suggest': search_suggest_action,
        }


    #
    # IAuthFunctions
    #

    def get_auth_functions(self):
        from .action import search_suggest_auth
        return {
            'discovery_search_suggest': search_suggest_auth,
        }

