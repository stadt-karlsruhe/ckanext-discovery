# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import re

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.model.meta import Session

from .model import SearchTerm, CoOccurrence
from .interfaces import ISearchTermPreprocessor
from .. import get_config


log = logging.getLogger(__name__)


def preprocess_search_term(term):
    '''
    Preprocess a search term.

    Passes the term to all implementations of the
    ``ISearchTermPreprocessor`` interface.

    Returns the preprocessed term or ``False`` if one of the
    preprocessors rejected the term.
    '''
    for plugin in plugins.PluginImplementations(ISearchTermPreprocessor):
        term = (plugin.preprocess_search_term(term) or '').strip()
        if not term:
            return False

    # Make sure that the term is still normalized
    term = term.lower()
    term = re.sub(r'[^\w-]', '', term, flags=re.UNICODE)
    term = term.replace('_', '')  # Because _ is in \w
    term = re.sub(r'(?<!\w)-', '*', term, flags=re.UNICODE)
    term = re.sub(r'-(?!\w)', '*', term, flags=re.UNICODE)
    term = term.replace('*', '')

    return term


def split_query(q):
    '''
    Split a search query into normalized words.

    ``q`` is a search query as a string.

    Returns a list of strings.

    During normalization, the query is converted to lower-case and all
    characters that are neither letters, digits, or intra-word hyphens
    are replaced by spaces. The resulting string is split on whitespace.
    Each of the resulting words is then passed to all implementations of
    the ``ISearchTermPreprocessor`` interface.

    The final result is a list of all normalized and preprocessed search
    terms that were not filtered out by a preprocessor.
    '''
    q = q.lower()
    q = re.sub(r'[^\w-]', ' ', q, flags=re.UNICODE)
    q = q.replace('_', ' ')  # Because _ is in \w
    q = re.sub(r'(?<!\w)-', ' ', q, flags=re.UNICODE)
    q = re.sub(r'-(?!\w)', ' ', q, flags=re.UNICODE)
    preprocessed = (preprocess_search_term(w) for w in q.split())
    return [w for w in preprocessed if w]


def store_query(q):
    '''
    Store a search query in the database.

    ``q`` is a search query as a string.

    All implementations of ``ISearchHistoryFilter.filter_search_query``
    are called before the query is stored. If one of them returns a
    false value then the query is not stored.
    '''
    words = set(split_query(q))
    log.debug('Remembering the search terms "{}"'.format(' '.join(words)))
    terms = sorted(SearchTerm.get_or_create(term=t) for t in words)
    for i, term1 in enumerate(terms):
        term1.count += 1
        for term2 in terms[i + 1:]:
            CoOccurrence.get_or_create(term1=term1, term2=term2).count += 1
    Session.commit()


def reprocess():
    '''
    Re-process the stored search terms.

    Passes all stored search terms to all implementations of the
    ``ISearchTermPreprocessor`` interface. Terms that are rejected are
    deleted from the database, changed terms are stored.

    Useful after changing a preprocessor.
    '''
    log.debug('Reprocessing stored search terms')
    for term in Session.query(SearchTerm).yield_per(100):
        preprocessed = preprocess_search_term(term.term)
        if not preprocessed:
            log.debug('Deleting {}'.format(term))
            Session.delete(term)
        else:
            term.term = preprocessed
    Session.commit()
    log.debug('Reprocessing complete')


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

