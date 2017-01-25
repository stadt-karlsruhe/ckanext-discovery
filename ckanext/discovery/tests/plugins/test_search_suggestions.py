# encoding: utf-8

'''
Tests for ``ckanext.discovery.plugins.search_suggestions``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from nose.tools import raises, eq_, ok_

from ckan.model.meta import Session
import ckan.plugins.toolkit as toolkit
import ckan.tests.helpers as helpers

from ...plugins.search_suggestions.model import SearchTerm, CoOccurrence
from ...plugins.search_suggestions import split_query
from .. import changed_config, assert_anonymous_access


def search_history(s, preprocess=False):
    '''
    Set the search history.

    The previous search history is cleared and replaced by the search
    queries given in the string ``s``. Each line of ``s`` contains a
    single search query. If ``preprocess`` is False then each line is
    simply split at whitespace. Otherwise the usual query splitting and
    term-postprocessing is used.
    '''
    Session.query(SearchTerm).delete()
    Session.commit()
    eq_(len(list(Session.query(SearchTerm))), 0)
    eq_(len(list(Session.query(CoOccurrence))), 0)
    for query in s.splitlines():
        if preprocess:
            words = split_query(query)
        else:
            words = query.split()
        terms = sorted((SearchTerm.get_or_create(term=t) for t in words),
                       key=lambda t: t.term)
        for i, term1 in enumerate(terms):
            term1.count += 1
            for term2 in terms[i + 1:]:
                CoOccurrence.get_or_create(term1=term1, term2=term2).count += 1
    Session.commit()


def suggest(q):
    '''
    Shortcut for discovery_search_suggest.
    '''
    return helpers.call_action('discovery_search_suggest', q=q)


def assert_suggestions(query, suggestions):
    '''
    Assert that a certain query gets the expected suggestions.
    '''
    results = suggest(query)
    eq_([d['value'] for d in results], suggestions)


class TestDiscoverySearchSuggest(helpers.FunctionalTestBase):
    '''
    Tests for discovery_search_suggest action function.
    '''

    @raises(toolkit.ValidationError)
    def test_no_query(self):
        helpers.call_action('discovery_search_suggest')

    def test_max_content_words(self):
        '''
        Only the last 4 complete query terms are taken into account.
        '''
        search_history('''
            fox chicken
            wolf sheep
        ''')
        # Last word incomplete
        q = 'wolf fox unknown1 unknown2 unknown3 unknown4'
        assert_suggestions(q, [q + ' chicken'])

        # Last word complete
        q = 'wolf unknown1 unknown2 unknown3 fox '
        assert_suggestions(q, [q + 'chicken'])

    def test_last_word_complete(self):
        '''
        Extensions but no auto-completion if the last word is complete.
        '''
        search_history('''
            caterpillar
            cat dog
        ''')
        assert_suggestions('cat ', ['cat dog'])

    def test_completed_terms_more_important_than_autocomplete(self):
        '''
        When ranking extensions, complete context words are more
        important than auto-complete suggestions.
        '''
        search_history('''
            dog wolf
            cat chicken
        ''')
        q = 'dog ca'
        assert_suggestions('dog ca', ['dog cat', 'dog cat wolf',
                           'dog cat chicken'])

    def test_limit(self):
        '''
        The maximum number of suggestions is configurable.
        '''
        search_history('''
            badger
            baboon
            bat
            bee
            bear
            beaver
            bison
        ''')
        KEY = 'ckanext.discovery.search_suggestions.limit'
        # Default is 4
        eq_(len(suggest('b')), 4)

        # Explicit limit
        for limit in range(8):
            with changed_config(KEY, limit):
                eq_(len(suggest('b')), limit)

        # Make sure a too high limit doesn't break things
        with changed_config(KEY, 10):
            eq_(len(suggest('b')), 7)

    def test_markup(self):
        '''
        Suggestions contain both markup and plaintext.
        '''
        search_history('''
            bee baboon
            bear badger
        ''')
        q = 'be'
        results = suggest(q)
        for item in results:
            value = item['value']
            label = item['label']
            ok_(value.startswith(q))
            ok_(label.startswith(q))
            n = len(q)
            eq_('<strong>{}</strong>'.format(value[n:]), label[n:])

    def test_anonymous_access(self):
        '''
        discovery_search_suggest can be used anonymously.
        '''
        assert_anonymous_access('discovery_search_suggest', q='dummy')

    def test_empty_query(self):
        '''
        An empty query returns no suggestions.
        '''
        eq_(suggest(''), [])

    def test_no_automcompletion_for_pseudo_complete_term(self):
        '''
        If the last word matches a term but is not followed by a space
        then that term is not suggested as an auto-completion.
        '''
        search_history('''
            cat
            caterpillar
        ''')
        assert_suggestions('cat', ['caterpillar'])

    def test_stripped_characters(self):
        '''
        If the query ends with characters that are removed by the
        normalization then they are removed from the suggestions, too.
        '''
        search_history('''
            cat mouse
        ''')
        assert_suggestions('cat mo!', ['cat mouse'])


