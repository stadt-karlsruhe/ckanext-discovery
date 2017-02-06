# encoding: utf-8

'''
Tests for ``ckanext.discovery.plugins.search_suggestions``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import mock
from nose.tools import raises, eq_, ok_

from ckan.model.meta import Session
import ckan.plugins.toolkit as toolkit
import ckan.tests.helpers as helpers
from ckan.plugins import implements, SingletonPlugin

from ...plugins.search_suggestions.model import SearchTerm, CoOccurrence
from ...plugins.search_suggestions import (SearchQuery, preprocess_search_term,
                                           reprocess)
from ...plugins.search_suggestions.interfaces import ISearchTermPreprocessor
from .. import (changed_config, assert_anonymous_access, with_plugin,
                temporarily_enabled_plugin, paster)


def search_history(s):
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
    for string in s.splitlines():
        SearchQuery(string).store()


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

        # Earlier terms are not re-suggested even if they are ignored
        # when generating suggestions
        assert_suggestions('sheep wolf unknown1 unknown2 unknown4 ', [])

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


class TestSearchQuery(object):
    '''
    Tests for ``SearchQuery``.
    '''
    def test_conversion_to_lowercase(self):
        '''
        Search queries are converted to lower-case.
        '''
        eq_(SearchQuery('FOO! bar?').string, 'foo! bar?')

    def test_query_splitting(self):
        '''
        Query strings are correctly split into words.
        '''
        cases = [
            ['single-word-with-hyphens', 'single-word-with-hyphens'],
            ['-- trailing- -leading - -- ---', 'trailing leading'],
            ['1-2 3--4 -5 6- 7', '1-2 3 4 5 6 7'],
            ['\n \t some\twhite\nspace  \t \n', 'some white space'],
            ['Ünïçödè çháraċtèrs', 'ünïçödè çháraċtèrs'],
            ['!ä_b?c=d<è>f:g#h(i)j[k]', 'ä b c d è f g h i j k'],
        ]
        for string, expected in cases:
            eq_(SearchQuery(string).words, expected.split())

    @mock.patch('ckanext.discovery.plugins.search_suggestions.preprocess_search_term',
                return_value='dog')
    def test_preprocessing(self, preprocess_search_term):
        '''
        Query words are preprocessed via ``preprocess_search_term``.
        '''
        SearchQuery('fox dog chicken')
        eq_(preprocess_search_term.mock_calls,
            [mock.call('fox'), mock.call('dog'), mock.call('chicken')])

    def test_is_last_word_complete(self):
        '''
        Completion status of last word is computed correctly.
        '''
        cases = [
            ['', True],
            [' ', True],
            ['dog fox ', True],
            ['dog fox', False],
        ]
        for string, expected in cases:
            eq_(SearchQuery(string).is_last_word_complete, expected)

    def test_last_word(self):
        '''
        Last word is computed correctly.
        '''
        cases = [
            ['dog', 'dog'],
            ['dog fox', 'fox'],
            ['dog fox wolf', 'wolf'],
            ['dog ', 'dog'],
            ['dog\t', 'dog'],
            ['dog\n', 'dog'],
            ['fox dog ', 'dog'],
            ['fox dog\t', 'dog'],
            ['fox dog\n', 'dog'],
        ]
        for string, expected in cases:
            eq_(SearchQuery(string).last_word, expected)

    @raises(IndexError)
    def test_last_word_for_empty_query(self):
        '''
        Can't get the last word of an empty query
        '''
        SearchQuery('  \t \n  ').last_word

    def test_store(self):
        '''
        Queries are stored correctly.
        '''
        search_history('')
        SearchQuery('dog cat').store()
        SearchQuery('wolf dog fox').store()
        SearchQuery('chicken').store()
        SearchQuery('dog cat chicken').store()
        eq_(SearchTerm.get_or_create(term='dog').count, 3)
        eq_(SearchTerm.get_or_create(term='cat').count, 2)
        eq_(SearchTerm.get_or_create(term='wolf').count, 1)
        eq_(SearchTerm.get_or_create(term='fox').count, 1)
        eq_(SearchTerm.get_or_create(term='chicken').count, 2)
        eq_(CoOccurrence.for_words('dog', 'cat').count, 2)
        eq_(CoOccurrence.for_words('wolf', 'dog').count, 1)
        eq_(CoOccurrence.for_words('wolf', 'fox').count, 1)
        eq_(CoOccurrence.for_words('dog', 'fox').count, 1)
        eq_(CoOccurrence.for_words('dog', 'chicken').count, 1)
        eq_(CoOccurrence.for_words('cat', 'chicken').count, 1)
        eq_(CoOccurrence.for_words('cat', 'chicken').count, 1)
        eq_(CoOccurrence.for_words('wolf', 'chicken').count, 0)
        eq_(CoOccurrence.for_words('fox', 'chicken').count, 0)
        eq_(CoOccurrence.for_words('fox', 'cat').count, 0)
        eq_(CoOccurrence.for_words('wolf', 'cat').count, 0)


class MockSearchTermPreprocessor(SingletonPlugin):
    '''
    Helper for ``TestPreprocessSearchTerm`` and ``TestReprocess``.
    '''
    implements(ISearchTermPreprocessor)

    def preprocess_search_term(self, term):
        if term == 'stopword':
            return False
        if term == 'bad-word':
            return ''
        if term == 'replace':
            return '-Ä_b-c$z2*3 f-'
        return term


class TestPreprocessSearchTerm(object):
    '''
    Test ``preprocess_search_term``.
    '''
    @with_plugin(MockSearchTermPreprocessor)
    def test_preprocess_search_term(self, plugin):
        cases = [
            ['stopword', False],
            ['bad-word', False],
            ['replace', 'äb-cz23f'],
            ['-Ä_b-c$z2*3 f-', 'äb-cz23f'],
        ]
        for term, expected in cases:
            eq_(preprocess_search_term(term), expected)


class TestReprocess(object):
    '''
    Test ``reprocess``.
    '''
    def test_reprocess(self):
        search_history('stopword bad-word replace other')
        with temporarily_enabled_plugin(MockSearchTermPreprocessor):
            reprocess()
        terms = set(t.term for t in SearchTerm.query())
        eq_(terms, {'äb-cz23f', 'other'})
        cooccs = set((c.term1.term, c.term2.term)
                     for c in CoOccurrence.query())
        eq_(cooccs, {('other', 'äb-cz23f')})


class TestPaster(object):
    '''
    Test paster CLI commands.
    '''
    def test_list(self):
        search_history('cat dog wolf')
        stdout = paster('search_suggestions', 'list')[1]
        words = set(stdout.strip().splitlines())
        eq_(words, {'cat', 'dog', 'wolf'})

    @mock.patch('ckanext.discovery.plugins.search_suggestions.reprocess')
    def test_reprocess(self, reprocess):
        paster('search_suggestions', 'reprocess')
        reprocess.assert_called()

    @mock.patch('ckanext.discovery.plugins.search_suggestions.model.create_tables')
    def test_init(self, create_tables):
        paster('search_suggestions', 'init')
        create_tables.assert_called()


# TODO: Test UI
# TODO: Test automatic search query storage

