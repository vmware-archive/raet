# -*- coding: utf-8 -*-
'''
Basic test of estating

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import sys
import time
import tempfile
import shutil

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.base.storing import Store

from ioflo.base.consoling import getConsole
console = getConsole()

if sys.platform == 'win32':
    TEMPDIR = 'c:/temp'
    if not os.path.exists(TEMPDIR):
        os.mkdir(TEMPDIR)
else:
    TEMPDIR = '/tmp'

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import estating, stacking

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass


class BasicTestCase(unittest.TestCase):
    '''
    Basic pack and parse
    '''

    def setUp(self):
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

    def tearDown(self):
        pass

    def testNormalizeHost(self):
        '''
        Test normalizeHost method
        '''
        console.terse("{0}\n".format(self.testNormalizeHost.__doc__))
        stack = stacking.RoadStack()
        estate = estating.Estate(stack, ha=("", 7540), iha=("", 7540))
        self.assertEqual(estate.ha, ('127.0.0.1', 7540))
        self.assertEqual(estate.iha, ('127.0.0.1', 7540))

        estate = estating.Estate(stack, ha=("::", 7540), iha=("::", 7540))
        self.assertEqual(estate.ha, ('::1', 7540))
        self.assertEqual(estate.iha, ('::1', 7540))

        host = estate.normalizeHost("216.58.193.78")
        self.assertEqual(host, "216.58.193.78")
        host = estate.normalizeHost("2607:f8b0:400a:809::200e")
        self.assertEqual(host, '2607:f8b0:400a:809::200e')

        stack.server.close()


def runOneBasic(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    """ Unittest runner """
    tests =  []
    names = [
                'testNormalizeHost',
            ]
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

    #runAll() #run all unittests

    runSome()#only run some

    #runOneBasic('testSign')

