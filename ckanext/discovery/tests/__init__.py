# encoding: utf-8

'''
Helpers for testing ``ckanext.discovery``.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import contextlib
import functools
import re

from ckan.model import Package
from ckan.model.meta import Session
from ckan.tests.helpers import call_action
from ckan.logic import NotAuthorized


try:
    from ckan.tests.helpers import changed_config
except ImportError:
    from ckan.common import config

    # Copied from CKAN 2.7
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

    # Copied from CKAN 2.7
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

try:
    from ckan.tests.helpers import recorded_logs
except ImportError:
    import collections
    import logging

    # Copied from CKAN 2.7
    @contextlib.contextmanager
    def recorded_logs(logger=None, level=logging.DEBUG,
                      override_disabled=True, override_global_level=True):
        u'''
        Context manager for recording log messages.

        :param logger: The logger to record messages from. Can either be a
            :py:class:`logging.Logger` instance or a string with the
            logger's name. Defaults to the root logger.

        :param int level: Temporary log level for the target logger while
            the context manager is active. Pass ``None`` if you don't want
            the level to be changed. The level is automatically reset to its
            original value when the context manager is left.

        :param bool override_disabled: A logger can be disabled by setting
            its ``disabled`` attribute. By default, this context manager
            sets that attribute to ``False`` at the beginning of its
            execution and resets it when the context manager is left. Set
            ``override_disabled`` to ``False`` to keep the current value
            of the attribute.

        :param bool override_global_level: The ``logging.disable`` function
            allows one to install a global minimum log level that takes
            precedence over a logger's own level. By default, this context
            manager makes sure that the global limit is at most ``level``,
            and reduces it if necessary during its execution. Set
            ``override_global_level`` to ``False`` to keep the global limit.

        :returns: A recording log handler that listens to ``logger`` during
            the execution of the context manager.
        :rtype: :py:class:`RecordingLogHandler`

        Example::

            import logging

            logger = logging.getLogger(__name__)

            with recorded_logs(logger) as logs:
                logger.info(u'Hello, world!')

            logs.assert_log(u'info', u'world')
        '''
        if logger is None:
            logger = logging.getLogger()
        elif not isinstance(logger, logging.Logger):
            logger = logging.getLogger(logger)
        handler = RecordingLogHandler()
        old_level = logger.level
        manager_level = logger.manager.disable
        disabled = logger.disabled
        logger.addHandler(handler)
        try:
            if level is not None:
                logger.setLevel(level)
            if override_disabled:
                logger.disabled = False
            if override_global_level:
                if (level is None) and (manager_level > old_level):
                    logger.manager.disable = old_level
                elif (level is not None) and (manager_level > level):
                    logger.manager.disable = level
            yield handler
        finally:
            logger.handlers.remove(handler)
            logger.setLevel(old_level)
            logger.disabled = disabled
            logger.manager.disable = manager_level


    # Copied from CKAN 2.7
    class RecordingLogHandler(logging.Handler):
        u'''
        Log handler that records log messages for later inspection.

        You can inspect the recorded messages via the ``messages`` attribute
        (a dict that maps log levels to lists of messages) or by using
        ``assert_log``.

        This class is rarely useful on its own, instead use
        :py:func:`recorded_logs` to temporarily record log messages.
        '''
        def __init__(self, *args, **kwargs):
            super(RecordingLogHandler, self).__init__(*args, **kwargs)
            self.clear()

        def emit(self, record):
            self.messages[record.levelname.lower()].append(record.getMessage())

        def assert_log(self, level, pattern, msg=None):
            u'''
            Assert that a certain message has been logged.

            :param string pattern: A regex which the message has to match.
                The match is done using ``re.search``.

            :param string level: The message level (``'debug'``, ...).

            :param string msg: Optional failure message in case the expected
                log message was not logged.

            :raises AssertionError: If the expected message was not logged.
            '''
            compiled_pattern = re.compile(pattern)
            for log_msg in self.messages[level]:
                if compiled_pattern.search(log_msg):
                    return
            if not msg:
                if self.messages[level]:
                    lines = u'\n    '.join(self.messages[level])
                    msg = (u'Pattern "{}" was not found in the log messages for '
                           + u'level "{}":\n    {}').format(pattern, level, lines)
                else:
                    msg = (u'Pattern "{}" was not found in the log messages for '
                           + u'level "{}" (no messages were recorded for that '
                           + u'level).').format(pattern, level)
            raise AssertionError(msg)

        def clear(self):
            u'''
            Clear all captured log messages.
            '''
            self.messages = collections.defaultdict(list)



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


def assert_regex_search(regex, string):
    '''
    Assert that a regular expression search finds a match.
    '''
    m = re.search(regex, string, flags=re.UNICODE)
    if m is None:
        raise AssertionError('{!r} finds no match in {!r}'.format(regex,
                             string))


def purge_datasets():
    '''
    Purge all existing datasets.
    '''
    for pkg in Session.query(Package):
        call_action('dataset_purge', id=pkg.id)

