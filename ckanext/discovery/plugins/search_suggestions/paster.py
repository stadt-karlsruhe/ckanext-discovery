# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from ckan.lib.cli import CkanCommand

# Do not import modules for CKAN or ckanext-extractor here (unless you know
# what you're doing), since their loggers won't work if imported before the
# CKAN configuration has been loaded.


def _error(msg):
    sys.exit('ERROR: ' + msg)


class SearchSuggestionsCommand(CkanCommand):
    """
    Utilities for the search_suggestions plugin.

    Sub-commands:

        init:
            Initialize database tables. Deletes all stored search terms.

        list:
            List all currently stored search terms.

        reprocess:
            Re-process the stored search terms via the current implementations
            of the ISearchTermPreprocessor interface.

    """
    max_args = 1
    min_args = 0
    usage = __doc__
    summary = __doc__.strip().split('\n')[0]

    def command(self):
        if not self.args:
            _error('Missing command name. Try --help.')
        self._load_config()
        cmd = self.args[0]
        try:
            method = getattr(self, 'cmd_' + cmd)
        except AttributeError:
            _error('Unknown command "{}". Try --help.'.format(cmd))
        method()

    def cmd_init(self):
        from .model import create_tables
        print('Creating database tables...')
        create_tables()
        print('Done.')

    def cmd_reprocess(self):
        from . import reprocess
        print('Re-processing stored search terms...')
        reprocess()
        print('Done.')

    def cmd_list(self):
        from ckan.model.meta import Session
        from .model import SearchTerm
        for term in Session.query(SearchTerm).yield_per(100):
            print(term.term)

