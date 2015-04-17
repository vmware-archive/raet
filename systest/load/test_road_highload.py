# -*- coding: utf-8 -*-
'''
Load test for Raet Road Stack

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


class LoadTestCase(testing.BasicLoadTestCase):
    """"""

    def __init__(self, *args, **kwargs):
        super(LoadTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        super(LoadTestCase, self).setUp()

    def tearDown(self):
        super(LoadTestCase, self).tearDown()

    def testOneToOneToMaster(self):
        console.terse("{0}\n".format(self.testOneToOneToMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testManyToOneToMaster(self):
        console.terse("{0}\n".format(self.testManyToOneToMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testOneToManyToMaster(self):
        console.terse("{0}\n".format(self.testOneToManyToMaster.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testManyToManyToMaster(self):
        console.terse("{0}\n".format(self.testManyToManyToMaster.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)

    def testOneToOneFromMaster(self):
        console.terse("{0}\n".format(self.testOneToOneFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_FROM_MASTER)

    def testManyToOneFromMaster(self):
        console.terse("{0}\n".format(self.testManyToOneFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_FROM_MASTER)

    def testOneToManyFromMaster(self):
        console.terse("{0}\n".format(self.testOneToManyFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_FROM_MASTER)

    def testManyToManyFromMaster(self):
        console.terse("{0}\n".format(self.testManyToManyFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_FROM_MASTER)

    def testOneToOneBidirectional(self):
        console.terse("{0}\n".format(self.testOneToOneBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testManyToOneBidirectional(self):
        console.terse("{0}\n".format(self.testManyToOneBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testOneToManyBidirectional(self):
        console.terse("{0}\n".format(self.testOneToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testManyToManyBidirectional(self):
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=testing.MULTI_MASTER_COUNT,
                                 minionCount=testing.MULTI_MINION_COUNT,
                                 msgSize=testing.MSG_SIZE_MED,
                                 msgCount=testing.MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)

    def testManyToManyBidirectional1(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024,
                                 msgCount=100,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}\n'.format(e-s))

    def testManyToManyBidirectional2(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024*10,
                                 msgCount=100,
                                 duration=100.0,
                                 direction=testing.DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}\n'.format(e-s))

    def testManyToManyBidirectional3(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024*100,
                                 msgCount=100,
                                 duration=1000.0,
                                 direction=testing.DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}\n'.format(e-s))

    def testOneToOneUnidirectional3(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testOneToOneUnidirectional3.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=1024*1024,
                                 msgCount=100,
                                 duration=1000.0,
                                 direction=testing.DIR_TO_MASTER)
        e = dt.now()
        console.terse('Test time: {0}\n'.format(e-s))

    def testOneToOneToMasterBig(self):
        console.terse("{0}\n".format(self.testOneToOneToMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=1024*1024*10,
                                 msgCount=1,
                                 duration=100.0,
                                 direction=testing.DIR_TO_MASTER)


def runOne(test):
    '''
    Unittest Runner
    '''
    test = LoadTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)


def runSome():
    """ Unittest runner """
    tests = []
    names = [
        'testOneToOneToMaster',
        'testManyToOneToMaster',
        'testOneToManyToMaster',
        'testManyToManyToMaster',
        'testOneToOneFromMaster',
        'testManyToOneFromMaster',
        'testOneToManyFromMaster',
        'testManyToManyFromMaster',
        'testOneToOneBidirectional',
        'testManyToOneBidirectional',
        'testOneToManyBidirectional',
        'testManyToManyBidirectional',
        'testManyToManyBidirectional1',
        'testManyToManyBidirectional2',
        'testManyToManyBidirectional3',
        'testOneToOneUnidirectional3',
        'testOneToOneToMasterBig',
        ]
    tests.extend(map(LoadTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(LoadTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__' and __package__ is None:

    # console.reinit(verbosity=console.Wordage.concise)

    runAll()  # run all unittests

    # runSome()  #only run some
