# encoding: utf-8

'''
Tests for ``ckanext.discovery.plugins.tag_cloud``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re

import mock
from nose.tools import assert_in, eq_

import ckan.tests.helpers as helpers
from ckan.model import Package
from ckan.model.meta import Session
import ckan.tests.factories as factories

from ...plugins.tag_cloud import bin_tags
from .. import assert_regex_search, changed_config


def set_tags(**kwargs):
    '''
    Populate dataset tables with specific tags.

    Any keyword argument is interpreted as a tag, the corresponding
    value is the tag's intended frequency.

    Before new datasets are created all existing datasets are purged.
    '''
    for pkg in Session.query(Package):
        helpers.call_action('dataset_purge', id=pkg.id)
    for tag, count in kwargs.iteritems():
        for i in range(count):
            factories.Dataset(tags=[{'name': tag}])


def assert_bins(expected, **kwargs):
    '''
    Assert that tags are binned as expected.
    '''
    bins = bin_tags(**kwargs)
    eq_(bins, expected)


class TestBinTags(object):
    '''
    Tests for ``bin_tags``.
    '''
    def test_single_tag(self):
        '''
        A single tag is assigned to the lowest bin.
        '''
        set_tags(cat=1)
        assert_bins({'cat': 1})

    def test_multiple_equally_frequent_tags(self):
        '''
        Multiple equally frequent tags are assigned to the same bin.
        '''
        set_tags(cat=1, dog=1, fox=1)
        assert_bins({'cat': 1, 'dog': 1, 'fox': 1})
        set_tags(cat=2, dog=2, fox=2, wolf=1, hamster=1, chicken=3, goose=3)
        assert_bins({'cat': 2, 'dog': 2, 'fox': 2, 'wolf': 1, 'hamster': 1,
                     'chicken': 3, 'goose': 3}, num_bins=3)

    def test_only_order_matters(self):
        '''
        Tags are binned by the order of their frequencies, not by the
        absolute frequencies.
        '''
        set_tags(cat=1, dog=2, fox=3, wolf=4, chicken=10)
        assert_bins({'cat':1, 'dog': 2, 'fox': 3, 'wolf': 4, 'chicken': 5})

    def test_num_bins(self):
        '''
        The number of bins can be specified.
        '''
        set_tags(cat=1, dog=2, fox=3, wolf=4, chicken=5, rabbit=6)
        assert_bins({'cat':1, 'dog': 1, 'fox': 2, 'wolf': 3, 'chicken': 4,
                     'rabbit': 5})  # Default is 5 bins
        assert_bins({'cat':1, 'dog': 2, 'fox': 3, 'wolf': 4, 'chicken': 5,
                     'rabbit': 6}, num_bins=6)
        assert_bins({'cat':1, 'dog': 2, 'fox': 3, 'wolf': 4, 'chicken': 5,
                     'rabbit': 6}, num_bins=7)
        assert_bins({'cat':1, 'dog': 1, 'fox': 2, 'wolf': 3, 'chicken': 3,
                     'rabbit': 4}, num_bins=4)
        assert_bins({'cat':1, 'dog': 1, 'fox': 2, 'wolf': 2, 'chicken': 3,
                     'rabbit': 3}, num_bins=3)
        assert_bins({'cat':1, 'dog': 1, 'fox': 1, 'wolf': 2, 'chicken': 2,
                     'rabbit': 2}, num_bins=2)
        assert_bins({'cat':1, 'dog': 1, 'fox': 1, 'wolf': 1, 'chicken': 1,
                     'rabbit': 1}, num_bins=1)

    def test_num_tags(self):
        '''
        The number of tags can be specified.
        '''
        max_num = 30
        tags = {'tag{}'.format(i): 1 for i in range(max_num)}
        set_tags(**tags)
        eq_(len(bin_tags()), 20)  # Default value is 20
        for num_tags in [0, 1, 2, 3, 10, 30, 40]:
            eq_(len(bin_tags(num_tags=num_tags)), min(num_tags, max_num))


class TestUI(helpers.FunctionalTestBase):
    '''
    Test web UI.
    '''
    def test_css_classes(self):
        '''
        The correct CSS classes are used.
        '''
        tags = {'cat': 1, 'dog': 2, 'fox': 3, 'wolf': 4, 'chicken': 5}
        set_tags(**tags)
        app = self._get_test_app()
        response = app.get('/')
        body = response.body.decode('utf-8')
        regex = r'<a\s+class="level-{}"\s+href="[^"]*"\s*>{}</a>'
        for tag, count in tags.iteritems():
            assert_regex_search(regex.format(count, tag), body)

    def test_resources(self):
        '''
        Resources are included correctly.
        '''
        app = self._get_test_app()
        response = app.get('/')
        body = response.body.decode('utf-8')
        assert_in('tag_cloud.css', body)

    def test_num_tags(self):
        '''
        The number of tags is configurable via
        ``ckanext.discovery.tag_cloud.num_tags``.
        '''
        max_num = 30
        tags = {'tag{}'.format(i): 1 for i in range(max_num)}
        set_tags(**tags)
        for num_tags in [0, 1, 2, 3, 10, 30, 40]:
            with changed_config('ckanext.discovery.tag_cloud.num_tags',
                                num_tags):
                app = self._get_test_app()
                response = app.get('/')
                body = response.body.decode('utf-8')
                tag_cloud_links = re.findall(
                    r'<a\s+class="level-\d"\s+href="[^"]*"\s*>', body)
                eq_(len(tag_cloud_links), min(num_tags, max_num))

