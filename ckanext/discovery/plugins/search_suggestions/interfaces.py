# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ckan import plugins


class ISearchHistoryFilter(plugins.Interface):
    '''
    Filter search queries before they are stored.

    Search suggestions are based on previously stored search queries.
    They therefore carry the risk that a user is presented with
    displeasing content originally provided by a different user. To
    minimize that risk, this interface can be used to filter search
    queries before they are stored.
    '''
    def filter_search_query(self, query):
        '''
        Decide whether a search query should be stored.

        ``query`` is a set of normalized search terms extracted from a
        user's search query.

        If this method returns a true value then the query terms are
        stored and may be presented to other users as part of future
        search suggestions. If this method returns a false value then
        the query is not stored. The search itself has already taken
        place when this method is called and is not affected by it.
        '''
        return True

