# -*- coding: utf-8 -*-
"""
Raet Ioflo Behavior Unittests
"""

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from collections import deque

from ioflo.test import testing
from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet.road import stacking
from raet.flo import behaving

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)


def tearDownModule():
    pass


class BasicTestCase(testing.FrameIofloTestCase):
    """
    Example TestCase
    """

    def setUp(self):
        """
        Call super if override so House Framer and Frame are setup correctly
        """
        super(BasicTestCase, self).setUp()

    def tearDown(self):
        """
        Call super if override so House Framer and Frame are torn down correctly
        """
        super(BasicTestCase, self).tearDown()

    def testRaetRoadStack(self):
        """
        Test RaetRoadStack Behavior
        """
        console.terse("{0}\n".format(self.testRaetRoadStack.__doc__))
        act = self.addEnterDeed("RaetRoadStack")
        self.assertIn(act, self.frame.enacts)
        self.assertEqual(act.actor, "RaetRoadStack")

        self.resolve()  # resolve House, Framer, Frame, Acts, Actors
        self.assertDictEqual(act.actor.Ioinits,
                             {
                                'txmsgs': {'ipath': 'txmsgs', 'ival': deque([])},
                                'local': {'ipath': 'local', 'ival': {'uid': None,
                                        'auto': 1, 'basedirpath': '/tmp/raet/keep',
                                        'host': '0.0.0.0', 'sigkey': None,
                                        'mutable': True, 'prikey': None,
                                        'main': False, 'port': 7530, 'name': 'master'}},
                                'rxmsgs': {'ipath': 'rxmsgs', 'ival': deque([])},
                                'inode': 'raet.road.stack.',
                                'stack': 'stack'})

        self.assertTrue(hasattr(act.actor, 'local'))
        self.assertTrue(hasattr(act.actor, 'txmsgs'))
        self.assertTrue(hasattr(act.actor, 'rxmsgs'))
        self.assertTrue(hasattr(act.actor, 'inode'))
        self.assertTrue(hasattr(act.actor, 'stack'))
        self.assertEqual(act.actor.inode.name, 'raet.road.stack')
        self.assertIsInstance(act.actor.stack.value, stacking.RoadStack)

        self.frame.enter()  # run in frame
        self.assertIs(len(act.actor.txmsgs.value), 0)
        act.actor.stack.value.server.close()


def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)


def runSome():
    """ Unittest runner """
    tests = []
    names = ['testRaetRoadStack', ]
    tests.extend(map(BasicTestCase, names))  # pylint: disable=bad-builtin
    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    runAll()  # run all unittests

    #runSome() # only run some

    #runOne('testBasic')
