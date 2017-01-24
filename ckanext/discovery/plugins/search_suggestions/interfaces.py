# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ckan import plugins


class ISearchTermPreprocessor(plugins.Interface):
    '''
    Preprocess search terms.

    This interface allows you to preprocess search terms extracted from
    a user's search query before they are stored or used to generate
    search suggestions.
    '''
    def preprocess_search_term(self, term):
        '''
        Preprocess and filter a search term.

        ``term`` is a search term extracted from a user's search query.

        If this method returns a false value then the term is ignored
        w.r.t. search suggestions. This is useful for filtering stop
        words and unwelcome content.

        Otherwise the return value of the method is used instead of the
        original search term. In most cases you simply return the value
        unchanged.

        Note that all of this only affects the generation of the search
        suggestions but not the search itself.
        '''
        return term

