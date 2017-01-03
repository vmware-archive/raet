# -*- coding: utf-8 -*-
'''
raet unit test package

To run all the unittests:

from raet import test
test.run()

'''

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
import os


from ioflo.base.consoling import getConsole
console = getConsole()
console.reinit(verbosity=console.Wordage.concise)

import raet

def run(start=None,  failfast=False):
    '''
    Run unittests starting at directory given by start
    Default start is the location of the raet package
    '''
    top = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(
               sys.modules.get(__name__).__file__))))

    if not start:
        start = 'raet' # top

    console.terse("\nRunning all RAET tests in '{0}', starting at '{1}'\n".format(top, start))
    loader = unittest.TestLoader()
    suite = loader.discover(start, 'test_*.py', top)
    unittest.TextTestRunner(verbosity=2, failfast=failfast).run(suite)

if __name__ == "__main__":
    run()
