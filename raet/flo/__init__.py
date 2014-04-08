# -*- coding: utf-8 -*-
'''
raet.flo package
modules associated with running raet with ioflo
'''

__all__ = ['behaving']

import  importlib
for m in __all__:
    importlib.import_module(".{0}".format(m), package='raet.flo')
