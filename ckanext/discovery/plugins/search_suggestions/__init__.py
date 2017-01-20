# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.model.meta import Session

from .action import search_suggest_action, search_suggest_auth
from .model import SearchTerm, CoOccurrence, normalize_term
from .interfaces import ISearchHistoryFilter


log = logging.getLogger(__name__)


def store_query(q):
    '''
    Store a search query in the database.

    ``q`` is a search query as a string.

    All implementations of ``ISearchHistoryFilter.filter_search_query``
    are called before the query is stored. If one of them returns a
    false value then the query is not stored.
    '''
    words = set(normalize_term(t) for t in q.split())
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
        q = search_params['q']
        fq = search_params['fq']

        # Try to figure out whether this is a user-initiated, text-based search
        # request (and not a programmatically triggered one, tag search, ...).
        # See
        # https://github.com/ckan/ckanext-searchhistory/issues/1#issue-32079108
        c = toolkit.c
        try:
            if (
                c.controller != 'package'
                or c.action != 'search'
                or (q or '').strip() in (':', '*:*')
            ):
                return search_results
        except TypeError:
            # Web context not ready. Happens, for example, in paster commands.
            return search_results

        # TODO: If a user performs a text-based search and then continuously
        # refines the result via facets then we end up with many entries for
        # basically the same search, which might screw up our scoring.

        store_query(q)

        return search_results

    #
    # IActions
    #

    def get_actions(self):
        return {
            'discovery_search_suggest': search_suggest_action,
        }


    #
    # IAuthFunctions
    #

    def get_auth_functions(self):
        return {
            'discovery_search_suggest': search_suggest_auth,
        }

