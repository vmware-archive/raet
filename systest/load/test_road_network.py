# -*- coding: utf-8 -*-
'''
Load test for Raet Road Stack with network issues

'''
from __future__ import print_function
# pylint: skip-file
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os

from ioflo.base.consoling import getConsole
console = getConsole()

from systest.lib import netem
import testing

if sys.platform == 'win32':
    TEMPDIR = 'c:/temp'
    if not os.path.exists(TEMPDIR):
        os.mkdir(TEMPDIR)
else:
    TEMPDIR = '/tmp'


def setUpModule():
    console.reinit(verbosity=console.Wordage.terse)
    # console.reinit(verbosity=console.Wordage.concise)


def tearDownModule():
    pass


class NetworkLoadTestCase(testing.BasicLoadTestCase):
    """"""

    def __init__(self, *args, **kwargs):
        super(NetworkLoadTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        super(NetworkLoadTestCase, self).setUp()
        netem.clear()  # clear network emulation rules

    def tearDown(self):
        super(NetworkLoadTestCase, self).tearDown()
        # The only engine have to tear down stacks after all workers have done
        if self.engine:
            console.terse("Clearing netem rules\n")
            netem.clear()  # clear network emulation rules
            if netem.check() != 0:
                console.terse("Error removing netem rules! Check it manually!")

    def testNetemWorks(self):
        '''
        Check if system configured to run sudo tc without password
        If this test fail add the following in visudo:
        username ALL=NOPASSWD: /usr/sbin/tc
        This allow user 'username' to run 'sudo tc' without password prompt that is needed for netem module
        '''
        console.terse("{0}\n".format(self.testNetemWorks.__doc__))
        self.assertTrue(netem.delay())
        self.assertEqual(netem.check(), 1)

    def testDelayOneToOneToMaster(self):
        '''
        One slave sends messages to one master with network delays
        '''
        console.terse("{0}\n".format(self.testDelayOneToOneToMaster.__doc__))
        self.assertTrue(netem.delay(time=200, jitter=100, correlation=30))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testLossOneToOneToMaster(self):
        '''
        One slave sends messages to one master with packet loss
        '''
        console.terse("{0}\n".format(self.testLossOneToOneToMaster.__doc__))
        self.assertTrue(netem.loss(percent=30, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testDuplicateOneToOneToMaster(self):
        '''
        One slave sends messages to one master with packet duplication
        '''
        console.terse("{0}\n".format(self.testDuplicateOneToOneToMaster.__doc__))
        self.assertTrue(netem.duplicate(percent=50, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testReorderOneToOneToMaster(self):
        '''
        One slave sends messages to one master with packet reordering
        '''
        console.terse("{0}\n".format(self.testReorderOneToOneToMaster.__doc__))
        self.assertTrue(netem.reorder(time=200, percent=30, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testCorruptOneToOneToMaster(self):
        '''
        One slave sends messages to one master with packet corruption
        '''
        console.terse("{0}\n".format(self.testCorruptOneToOneToMaster.__doc__))
        self.assertTrue(netem.corrupt(percent=20, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testDelayManyToManyBidirectional(self):
        '''
        Bidirectional messaging between many masters and many slaves with network delay
        '''
        console.terse("{0}\n".format(self.testDelayManyToManyBidirectional.__doc__))
        self.assertTrue(netem.delay(time=200, jitter=100, correlation=30))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testLossManyToManyBidirectional(self):
        '''
        Bidirectional messaging between many masters and many slaves with packet loss
        '''
        console.terse("{0}\n".format(self.testLossManyToManyBidirectional.__doc__))
        self.assertTrue(netem.loss(percent=30, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testDuplicateManyToManyBidirectional(self):
        '''
        Bidirectional messaging between many masters and many slaves with packet duplication
        '''
        console.terse("{0}\n".format(self.testDuplicateManyToManyBidirectional.__doc__))
        self.assertTrue(netem.duplicate(percent=50, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testReorderManyToManyBidirectional(self):
        '''
        Bidirectional messaging between many masters and many slaves with packet reordering
        '''
        console.terse("{0}\n".format(self.testReorderManyToManyBidirectional.__doc__))
        self.assertTrue(netem.reorder(time=200, percent=30, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testCorruptManyToManyBidirectional(self):
        '''
        Bidirectional messaging between many masters and many slaves with packet corruption
        '''
        console.terse("{0}\n".format(self.testCorruptManyToManyBidirectional.__doc__))
        self.assertTrue(netem.corrupt(percent=20, correlation=25))
        self.assertEqual(netem.check(), 1)
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)


def runOne(test):
    '''
    Unittest Runner
    '''
    test = NetworkLoadTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)


def runSome():
    """ Unittest runner """
    tests = []
    names = [
        'testNetemWorks',
        'testDelayOneToOneToMaster',
        'testLossOneToOneToMaster',
        'testDuplicateOneToOneToMaster',
        'testReorderOneToOneToMaster',
        'testCorruptOneToOneToMaster',
        'testDelayManyToManyBidirectional',
        'testLossManyToManyBidirectional',
        'testDuplicateManyToManyBidirectional',
        'testReorderManyToManyBidirectional',
        'testCorruptManyToManyBidirectional',
        ]
    tests.extend(map(NetworkLoadTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(NetworkLoadTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__' and __package__ is None:

    # console.reinit(verbosity=console.Wordage.concise)

    runAll()  # run all unittests

    # runSome()  #only run some
