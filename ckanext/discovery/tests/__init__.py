# encoding: utf-8

'''
Helpers for testing ``ckanext.discovery``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import contextlib
import functools

from ckan.tests.helpers import call_action


try:
    from ckan.tests.helpers import changed_config
except ImportError:
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


try:
    from ckan.tests.lib.test_cli import paster
except ImportError:
    import sys
    from io import StringIO
    from paste.script.command import run
    from ckan.common import config

    # Copied from CKAN 2.7 to allow testing on 2.6
    def paster(*args, **kwargs):
        '''
        Call a paster command.

        All arguments are parsed and passed on to the command. The
        ``--config`` option is automatically appended.

        By default, an ``AssertionError`` is raised if the command exits
        with a non-zero return code or if anything is written to STDERR.
        Pass ``fail_on_error=False`` to disable this behavior.

        Example::

            code, stdout, stderr = paster(u'jobs', u'list')
            assert u'My Job Title' in stdout

            code, stdout, stderr = paster(u'jobs', u'foobar',
                                         fail_on_error=False)
            assert code == 1
            assert u'Unknown command' in stderr

        Any ``SystemExit`` raised by the command is swallowed.

        :returns: A tuple containing the return code, the content of
            STDOUT, and the content of STDERR.
        '''
        fail_on_error = kwargs.pop(u'fail_on_error', True)
        args = list(args) + [u'--config=' + config[u'__file__']]
        sys.stdout, sys.stderr = StringIO(u''), StringIO(u'')
        code = 0
        try:
            run(args)
        except SystemExit as e:
            code = e.code
        finally:
            stdout, stderr = sys.stdout.getvalue(), sys.stderr.getvalue()
            sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        if code != 0 and fail_on_error:
            raise AssertionError(u'Paster command exited with non-zero return code {}: {}'.format(code, stderr))
        if stderr.strip() and fail_on_error:
            raise AssertionError(u'Paster command wrote to STDERR: {}'.format(stderr))
        return code, stdout, stderr


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


# Adapted from ckanext-extractor
def with_plugin(cls):
    '''
    Activate a plugin during a function's execution.

    The plugin instance is passed to the function as an additional
    parameter.
    '''
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with temporarily_enabled_plugin(cls) as plugin:
                args = list(args) + [plugin]
                return f(*args, **kwargs)
        return wrapped
    return decorator


@contextlib.contextmanager
def temporarily_enabled_plugin(cls):
    '''
    Context manager for temporarily enabling a plugin.

    Returns the plugin instance.
    '''
    plugin = cls()
    plugin.activate()
    try:
        plugin.enable()
        yield plugin
    finally:
        plugin.disable()

