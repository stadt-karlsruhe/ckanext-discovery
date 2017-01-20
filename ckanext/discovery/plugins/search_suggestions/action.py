# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from sqlalchemy.orm.exc import NoResultFound

from ckan.logic import validate
import ckan.plugins.toolkit as toolkit
from ckan.lib.navl.validators import not_missing, not_empty

from .model import SearchTerm, CoOccurrence, normalize_term


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
    score = score / (sum(weights) * (len(terms) - 1))
    return score


@toolkit.side_effect_free
@validate(search_suggest_schema)
def search_suggest_action(context, data_dict):
    '''
    Get suggested search queries.

    Statistics show that almost all search queries contain 3 terms or
    less. Hence this function only takes the last 4 terms into account
    when computing similarity scores.
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

    # TODO: Limit results by minimum score

    #
    # Step 1: Auto-complete the last word
    #

    if last_word_complete:
        # Do not provide auto-completion suggestions
        ac_terms = []
        ac_scored = []
    else:
        # Find completions of the last word. If the last word is already a
        # complete word then the corresponding term will be included.
        ac_terms = SearchTerm.filter(SearchTerm.term.like(words[-1] + '%'))
        ac_terms = [t for t in ac_terms if t.term not in set(words[:-1])]

        # Score completions by their relative frequency. ``ac_scored`` ends up
        # as part of the actual suggestions, so if the last word is complete it
        # is excluded.
        total_count = sum(t.count for t in ac_terms)
        ac_scored = [(t.count / total_count, (t,))
                     for t in ac_terms if t.term != query[-1]]

        # If there's more than one word in the query then we also take the
        # their similarity to the auto-completed terms into account.
        if context_terms:
            ac_scored = [(0.5 * (score + _get_score(context_terms.union(terms))),
                          terms) for score, terms in ac_scored]

    log.debug(b'ac_terms = {}'.format(ac_terms))
    log.debug(b'ac_scored = {}'.format(ac_scored))

    #
    # Step 2: Suggest an additional search term
    #

    # Get extension candidates
    ext_terms = set()
    for term in context_terms.union(ac_terms):
        # FIXME: Add a limit to this query
        criteria = (CoOccurrence.term1 == term) | (CoOccurrence.term2 == term)
        cooccs = CoOccurrence.filter(criteria).order_by(CoOccurrence.count)
        for coocc in cooccs:
            other = coocc.term2 if coocc.term1 == term else coocc.term1
            ext_terms.add(other)
    ext_terms = [t for t in ext_terms if t.term not in words]
    log.debug(b'ext_terms = {}'.format(ext_terms))

    # Combine extension candidates with auto-completion suggestions
    if ac_terms:
        ac_ext_candidates = [(ac_term, ext_term)
                             for ext_term in ext_terms
                             for ac_term in ac_terms
                             if ac_term != ext_term]
    else:
        ac_ext_candidates = [(t,) for t in ext_terms]
    log.debug(b'ac_ext_candidates = {}'.format(ac_ext_candidates))


    # When ranking extensions, their relation to tokens the user has
    # already finished is more important than to an auto-completion
    # we're suggesting.
    weights = {terms[0].term: score for score, terms in ac_scored}
    weights.update({word: 1 for word in words})

    # Score extension candidates
    ac_ext_scored = []
    for ac_ext_terms in ac_ext_candidates:
        terms = list(context_terms.union(ac_ext_terms))
        score = _get_score(terms, [weights.get(t.term, 0) for t in terms])
        ac_ext_scored.append((score, ac_ext_terms))

    all_scored = sorted(ac_scored + ac_ext_scored, reverse=True)
    log.debug(b'All: {}'.format(all_scored))

    # FIXME: Add markup to distinguish existing text and suggestions

    # FIXME: Limit number of results

    if not ac_terms:
        prefix = ' '.join(query) + ' '
    else:
        prefix = ' '.join(query[:-1]) + ' '
    return [prefix + ' '.join([t.term for t in terms])
            for score, terms in all_scored]

