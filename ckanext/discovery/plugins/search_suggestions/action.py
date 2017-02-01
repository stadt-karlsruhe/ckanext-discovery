# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import itertools
import logging

from sqlalchemy.orm.exc import NoResultFound

from ckan.logic import validate
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.validators import not_missing, not_empty

from .model import SearchTerm, CoOccurrence
from . import SearchQuery
from .. import get_config


log = logging.getLogger(__name__)


def search_suggest_schema():
    return {
        'q': [not_missing, unicode]
    }


@toolkit.auth_allow_anonymous_access
def search_suggest_auth(context, data_dict):
    # Allow access by everybody
    return {'success': True}


def _get_score(terms, weights=None):
    '''
    Compute similarity score for a set of terms.

    ``terms`` is an iterable of ``SearchTerm`` instances.

    ``weights`` is an optional list of weights of the same length as
    ``terms``. If it is not given every term has the same weight.
    '''
    log.debug('Scoring {}'.format(terms))
    weights = weights or ([1] * len(terms))
    weighted_terms = sorted(zip(terms, weights), key=lambda x: x[0].term)
    score = 0
    for i, (term1, weight1) in enumerate(weighted_terms[:-1]):
        for term2, weight2 in weighted_terms[i + 1:]:
            try:
                coocc = CoOccurrence.one(term1=term1, term2=term2)
                score += (weight1 + weight2) * coocc.similarity
            except NoResultFound:
                log.debug('  {} and {} have no co-occurrences'.format(
                         term1.term, term2.term))
                pass
    log.debug('  Non-normalized score is {}'.format(score))
    try:
        score = score / (sum(weights) * (len(terms) - 1))
    except ZeroDivisionError:
        # Either only one term or all weights are zero
        score = 0

    log.debug('  Final score is {}'.format(score))
    return score


@toolkit.side_effect_free
@validate(search_suggest_schema)
def search_suggest_action(context, data_dict):
    '''
    Search query auto-completion and suggestions.

    Takes a single string parameter ``q`` which contains the search
    query.

    Returns a list of dictionaries, sorted decreasingly by relevance.
    Each dictionary contains two keys ``label`` and ``value``, which
    contain an HTML string and a plain-text value for the suggestion.

    Statistics show that almost all search queries contain 3 terms or
    less. Hence this function only takes the last 4 terms into account
    when computing similarity scores.

    The maximum number of suggestions offered can be set via the config
    option ``ckanext.discovery.search_suggestions.limit``, it defaults
    to 4.
    '''
    log.debug('discovery_search_suggest {!r}'.format(data_dict['q']))
    toolkit.check_access('discovery_search_suggest', context, data_dict)

    # In the following, a "term" is always an instance of ``SearchTerm``,
    # and a "word" is a normalized search token.

    query = SearchQuery(data_dict['q'])
    if not query.words:
        return []
    limit = int(get_config('search_suggestions.limit', 4))

    log.debug('words = {}'.format(query.words))
    log.debug('is_last_word_complete = {}'.format(query.is_last_word_complete))
    log.debug(b'context_terms = {}'.format(query.context_terms))

    # Maps tuples of terms to scores
    scores = {}

    #
    # Step 1: Auto-complete the last word
    #

    ac_terms = []
    if not query.is_last_word_complete:
        ac_terms = SearchTerm.by_prefix(query.last_word)
        ac_terms = [t for t in ac_terms if t.term not in query.words[:-1]]

        # Score auto-completions
        total_count = sum(t.count for t in ac_terms)
        num_context = len(query.context_terms)
        factor = 1 / (1 + num_context)
        for t in ac_terms:
            if t.term == query.last_word:
                continue
            term_score = t.count / total_count
            context_score = _get_score(query.context_terms.union((t,)))
            scores[(t,)] = factor * (term_score + num_context * context_score)
    log.debug(b'ac_terms = {}'.format(ac_terms))

    #
    # Step 2: Suggest an additional search term
    #

    # Get extension candidates
    ext_terms = set()
    for term in query.context_terms.union(ac_terms):
        cooccs = CoOccurrence.for_term(term) \
                             .order_by(CoOccurrence.count) \
                             .limit(limit)
        for coocc in cooccs:
            other = coocc.term2 if coocc.term1 == term else coocc.term1
            ext_terms.add(other)
    ext_terms = [t for t in ext_terms if t.term not in query.words]
    log.debug(b'ext_terms = {}'.format(ext_terms))

    # Combine extension candidates with auto-completion suggestions
    if ac_terms:
        ac_ext_candidates = [x for x in itertools.product(ac_terms, ext_terms)
                             if x[0] != x[1]]
    else:
        ac_ext_candidates = [(t,) for t in ext_terms]
    log.debug(b'ac_ext_candidates = {}'.format(ac_ext_candidates))

    # When ranking extensions, their relation to tokens the user has
    # already finished is more important than to an auto-completion
    # we're suggesting.
    weights = collections.defaultdict(int)
    weights.update((t[0].term, s) for t, s in scores.iteritems())
    weights.update((w, 1) for w in query.words)

    # Score extension candidates
    for ac_ext_terms in ac_ext_candidates:
        terms = list(query.context_terms.union(ac_ext_terms))
        score = _get_score(terms, [weights[t.term] for t in terms])
        if score > 0:
            scores[ac_ext_terms] = score
    log.debug(b'scores = {}'.format(scores))

    #
    # Step 3: Format suggestions for output
    #

    suggestions = sorted(scores.iterkeys(), key=scores.get, reverse=True)
    suggestions = list(suggestions)[:limit]
    suggestions = [' '.join([t.term for t in terms]) for terms in suggestions]
    log.debug('suggestions = {}'.format(suggestions))
    if ac_terms:
        prefix = query.string

        # If the query ends with characters that are removed by the
        # normalization then we need to strip them from the suggestions,
        # too.
        i = prefix.rindex(query.last_word)
        prefix = (prefix[:i].strip() + ' ' + query.last_word).lstrip()

        suggestions = [s[len(query.last_word):] for s in suggestions]
    else:
        prefix = query.string.strip() + ' '
    return [
        {
            'label': '{}<strong>{}</strong>'.format(prefix, s),
            'value': prefix + s,
        }
        for s in suggestions
    ]

