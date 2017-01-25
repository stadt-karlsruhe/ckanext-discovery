# encoding: utf-8

'''
Helpers for testing ``ckanext.discovery``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ckan.tests.helpers import call_action


try:
    from ckan.tests.helpers import changed_config
except ImportError:
    import contextlib
    from ckan.common import config

    # Copied from CKAN 2.7 to allow testing on 2.6
    @contextlib.contextmanager
    def changed_config(key, value):
        _original_config = config.copy()
        config[key] = value
        try:
            yield
        finally:
            config.clear()
            config.update(_original_config)


# Copied from ckanext-extractor
def call_action_with_auth(action, context=None, **kwargs):
    """
    Call an action with authorization checks.

    Like ``ckan.tests.helpers.call_action``, but authorization are not
    bypassed.
    """
    if context is None:
        context = {}
    context['ignore_auth'] = False
    return call_action(action, context, **kwargs)


# Copied from ckanext-extractor
def assert_anonymous_access(action, **kwargs):
    """
    Assert that an action can be called anonymously.
    """
    context = {'user': ''}
    try:
        call_action_with_auth(action, context, **kwargs)
    except NotAuthorized:
        raise AssertionError('"{}" cannot be called anonymously.'.format(
                             action))

