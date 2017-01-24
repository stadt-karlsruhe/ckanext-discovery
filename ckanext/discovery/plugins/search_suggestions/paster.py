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

        init: Initialize database tables.

        refilter: Re-filter the stored search terms via the current
            implementations of the ISearchHistoryFilter interface.

    """
    max_args = 1
    min_args = 0
    usage = __doc__
    summary = __doc__.strip().split('\n')[0]

    def command(self):
        self._load_config()
        if not self.args:
            _error('Missing command name. Try --help.')
        self._load_config()
        cmd = self.args[0]
        if cmd == 'init':
            self.init()
        elif cmd == 'refilter':
            self.refilter()
        else:
            _error('Uknown command "{}"'.format(cmd))

    def init(self):
        from .model import create_tables
        print('Creating database tables...')
        create_tables()
        print('Done.')

    def refilter(self):
        from . import refilter
        print('Refiltering stored search terms...')
        refilter()
        print('Done.')

