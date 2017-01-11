# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os.path
import sys

from ckan.lib.plugins import DefaultTranslation


class Translation(DefaultTranslation):

    def i18n_directory(self):
        module = sys.modules['ckanext.discovery']
        module_dir = os.path.abspath(os.path.dirname(module.__file__))
        return os.path.join(module_dir, 'i18n')

    def i18n_domain(self):
        return 'ckanext-discovery'

