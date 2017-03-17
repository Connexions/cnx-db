# -*- coding: utf-8 -*-
import os


here = os.path.abspath(os.path.dirname(__file__))
migrations = os.path.join(here, 'migrations')

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
