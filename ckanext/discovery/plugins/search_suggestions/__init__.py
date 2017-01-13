# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from .action import search_suggest_action, search_suggest_auth
from .model import SearchQuery


log = logging.getLogger(__name__)


class SearchSuggestionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

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

        log.debug('Remembering user search query "{}"'.format(q))
        SearchQuery.create(q)

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

