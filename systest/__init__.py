# -*- coding: utf-8 -*-
'''
systest package
'''

__all__ = ['lib']

import importlib
for m in __all__:
    importlib.import_module(".{0}".format(m), package='systest')
