# encoding: utf-8

'''
Tests for ``ckanext.discovery.plugins.solr_query_config``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import mock
from nose.tools import eq_

import ckan.tests.helpers as helpers

from .. import changed_config


CONFIG_PREFIX = 'ckanext.discovery.solr_query_config.'


class TestSolrQueryConfig(helpers.FunctionalTestBase):
    @mock.patch('pysolr.Solr.search')
    def check(self, type, expected, search_mock, **kwargs):
        with changed_config(CONFIG_PREFIX + type + '.defType', 'my_def_type'):
            helpers.call_action('package_search', **kwargs)
        eq_(search_mock.call_args[1]['defType'], expected)

    def test_default_given(self):
        '''
        Default values can be overwritten.
        '''
        self.check('default', 'another_def_type', defType='another_def_type')

    def test_default_not_given(self):
        '''
        Default values are used when not overwritten.
        '''
        self.check('default', 'my_def_type')

    def test_force_given(self):
        '''
        Forced values cannot be overwritten.
        '''
        self.check('force', 'my_def_type', defType='another_def_type')

    def test_force_not_given(self):
        '''
        Forced values are used when not overwritten.
        '''
        self.check('force', 'my_def_type')

