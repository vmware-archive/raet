# -*- coding: utf-8 -*-
''' Unit Tests

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.base.storing import Store
from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import packeting, estating, keeping, stacking, transacting

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

    def tearDown(self):
        pass

    def testBasic(self):
        '''
        Basic unit tests
        '''
        console.terse("{0}\n".format(self.testBasic.__doc__))

def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    """ Unittest runner """
    tests =  []
    names = ['testBasic']
    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    runAll() #run all unittests

    #runSome()#only run some

    #runOne('testBasic')
