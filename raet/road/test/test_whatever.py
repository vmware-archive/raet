# -*- coding: utf-8 -*-
''' Unit Tests

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
import os

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from ioflo.base.odicting import odict

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import packeting, estating, keeping, stacking, transacting

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class WhateverTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testBasic(self):
        pass


def testSome():
    """ Unittest runner """

    tests = []
    tests.append('testBasic')

    suite = unittest.TestSuite(map(WhateverTestCase, tests))
    unittest.TextTestRunner(verbosity=2).run(suite)

def testAll():
    """ Unittest runner """
    suite = unittest.TestLoader().loadTestsFromTestCase(WhateverTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    testAll() #run all unittests

    #testSome()#only run some

