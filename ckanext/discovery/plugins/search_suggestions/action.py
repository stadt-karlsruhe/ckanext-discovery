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

from .model import SearchTerm, CoOccurrence, normalize_term
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


# Maximum number of words to take into account when computing suggestions
_MAX_CONTEXT_WORDS = 4


def _get_score(terms, weights=None):
    '''
    Compute similarity score for a set of terms.

    ``terms`` is an iterable of ``SearchTerm`` instances.

    ``weights`` is an optional list of weights of the same length as
    ``terms``. If it is not given every term has the same weight.
    '''
    weights = weights or ([1] * len(terms))
    weighted_terms = sorted(zip(terms, weights), key=lambda x: x[0].term)
    score = 0
    for i, (term1, weight1) in enumerate(weighted_terms[:-1]):
        for term2, weight2 in weighted_terms[i + 1:]:
            try:
                coocc = CoOccurrence.one(term1=term1, term2=term2)
                score += (weight1 + weight2) * coocc.similarity
            except NoResultFound:
                pass
    try:
        return score / (sum(weights) * (len(terms) - 1))
    except ZeroDivisionError:
        # Either only one term or all weights are zero
        return 0


@toolkit.side_effect_free
@validate(search_suggest_schema)
def search_suggest_action(context, data_dict):
    '''
    Get suggested search queries.

    Statistics show that almost all search queries contain 3 terms or
    less. Hence this function only takes the last 4 terms into account
    when computing similarity scores.

    The maximum number of suggestions offered can be set via the config
    option ``ckanext.discovery.search_suggestions.limit``, it defaults
    to 4.
    '''
    log.debug('discovery_search_suggest {!r}'.format(data_dict['q']))
    toolkit.check_access('discovery_search_suggest', context, data_dict)

    # In the following, a "term" is always an instance of ``SearchTerm``, and
    # a "word" is a normalized search token.

    q = data_dict['q']
    query = q.split()
    if not query:
        return []
    words = [normalize_term(t) for t in query]
    word_set = set(words)
    limit = int(get_config('search_suggestions.limit', 4))

    # If the query ends with a space then we assume the user considers the last
    # word complete. In that case we won't offer any auto-completions for it.
    # If the last word is a complete in the sense that there's a corresponding
    # search term in the DB but it's not followed by a space then we do suggest
    # completions, but only if they actually extend the word. For example, the
    # query `play ` (with a trailing space) will not get auto-complete
    # suggestions, but `play` will get (for example) `playground`.
    last_word_complete = q[-1].isspace()

    if last_word_complete:
        context_words = words[-_MAX_CONTEXT_WORDS:]
    else:
        context_words = words[-(_MAX_CONTEXT_WORDS + 1):-1]
    if context_words:
        context_terms = set(SearchTerm.filter(SearchTerm.term.in_(context_words)))
    else:
        context_terms = set()

    log.debug('words = {}'.format(words))
    log.debug('last_word_complete = {}'.format(last_word_complete))
    log.debug('context_words = {}'.format(context_words))
    log.debug(b'context_terms = {}'.format(context_terms))

    # Maps tuples of terms to scores
    scores = {}

    #
    # Step 1: Auto-complete the last word
    #

    if last_word_complete:
        # Do not provide auto-completion suggestions. However, we need to check
        # whether the last word is a known term because in that case we take it
        # into account during context similarity scoring.
        try:
            ac_terms = [SearchTerm.one(term==words[-1])]
        except NoResultsFound:
            ac_terms = []
    else:
        ac_terms = SearchTerm.filter(SearchTerm.term.like(words[-1] + '%'))
        ac_terms = [t for t in ac_terms if t.term not in words[:-1]]

        # Score auto-completions
        total_count = sum(t.count for t in ac_terms)
        num_context = len(context_terms)
        factor = 1 / (1 + num_context)
        for t in ac_terms:
            if t.term == words[-1]:
                continue
            term_score = t.count / total_count
            context_score = _get_score(context_terms.union((t,)))
            scores[(t,)] = factor * (term_score + num_context * context_score)

    log.debug(b'ac_terms = {}'.format(ac_terms))

    #
    # Step 2: Suggest an additional search term
    #

    # Get extension candidates
    ext_terms = set()
    for term in context_terms.union(ac_terms):
        cooccs = CoOccurrence.for_term(term) \
                             .order_by(CoOccurrence.count) \
                             .limit(limit)
        for coocc in cooccs:
            other = coocc.term2 if coocc.term1 == term else coocc.term1
            ext_terms.add(other)
    ext_terms = [t for t in ext_terms if t.term not in word_set]
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
    weights.update((w, 1) for w in words)

    # Score extension candidates
    for ac_ext_terms in ac_ext_candidates:
        terms = list(context_terms.union(ac_ext_terms))
        score = _get_score(terms, [weights[t.term] for t in terms])
        if score > 0:
            scores[ac_ext_terms] = score

    log.debug(b'scores = {}'.format(scores))

    # Format suggestions for output
    suggestions = sorted(scores.iterkeys(), key=scores.get, reverse=True)
    suggestions = list(suggestions)[:limit]
    suggestions = [' '.join([t.term for t in terms]) for terms in suggestions]
    if not ac_terms:
        prefix = ' '.join(query) + ' '
    else:
        prefix = ' '.join(query[:-1]) + ' '
    return ['{} {}'.format(prefix, s) for s in suggestions]

    # FIXME: Add markup to distinguish existing text and suggestions

