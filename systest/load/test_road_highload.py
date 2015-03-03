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
import sys
import time
import tempfile
import shutil
import multiprocessing

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import keeping, estating, stacking, transacting

if sys.platform == 'win32':
    TEMPDIR = 'c:/temp'
    if not os.path.exists(TEMPDIR):
        os.mkdir(TEMPDIR)
else:
    TEMPDIR = '/tmp'

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)
        self.baseDirpath=tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)
        self.stack = None
        # This has to be set to True in the only one process that would perform tearDown steps
        self.engine = False

    def tearDown(self):
        # The only engine have to tear down stacks after all workers have done
        if not self.engine:
            if self.stack:
                self.stack.server.close()
                self.stack.clearAllDir()
        else:
            if os.path.exists(self.baseDirpath):
                shutil.rmtree(self.baseDirpath)

    def createStack(self, name, port):
        dirpath = os.path.join(self.baseDirpath, 'road', 'keep', name)
        signer = nacling.Signer()
        mainSignKeyHex = signer.keyhex
        privateer = nacling.Privateer()
        mainPriKeyHex = privateer.keyhex

        keeping.clearAllKeep(dirpath)

        return stacking.RoadStack(store=self.store,
                                  name=name,
                                  main=True,
                                  auto=raeting.AutoMode.once.value,
                                  ha=("", port),
                                  sigkey=mainSignKeyHex,
                                  prikey=mainPriKeyHex,
                                  dirpath=dirpath,
                                  )

    def getStuff(self, size):
        alpha = '{0}{1}'.format(''.join([chr(n) for n in xrange(ord('A'), ord('Z') + 1)]),
                                ''.join([chr(n) for n in xrange(ord('a'), ord('z') + 1)]))
        num = size / len(alpha)
        ret = ''.join([alpha for a in xrange(num)])
        num = size - len(ret)
        ret = ''.join([ret, alpha[:num]])
        self.assertEqual(len(ret), size)
        return ret

    def createData(self, house="manor", queue="stuff", size=1024):
        stuff = self.getStuff(size)
        data = odict(house=house, queue=queue, stuff=stuff)
        return data

    def joinAll(self, initiator, correspondentAddresses, timeout=None):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        for ha in correspondentAddresses:
            remote = initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                               fuid=0, # vacuous join
                                                               sid=0, # always 0 for join
                                                               ha=ha))
            initiator.join(uid=remote.uid, timeout=timeout)
        self.serviceOne(initiator)

    def allowAll(self, initiator, timeout=None):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        for remote in initiator.remotes.values():
            initiator.allow(uid=remote.uid, timeout=timeout)
        self.serviceOne(initiator)

    def serviceAll(self, stacks, duration=100.0, timeout=0.0, step=0.1):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        empty = False
        elapsed = self.timer.getElapsed()
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAll()
            if any(stack.transactions for stack in stacks):
                empty = False  # reset nop timeout
            else:
                if empty:
                    if self.timer.getElapsed() - elapsed > timeout:
                        break
                else:
                    empty = True
                    elapsed = self.timer.getElapsed()
            self.store.advanceStamp(step)
            time.sleep(step)

    def serviceOne(self, stack, duration=100.0, timeout=0.0, step=0.1):
        self.serviceAll([stack], duration, timeout, step)

    def bidirectional(self, stack, msgs=None, duration=3.0):
        msgs = msgs or []

        console.terse("\nMessages Bidirectional *********\n")
        for msg in msgs:
            for remote in stack.remotes.values():
                stack.transmit(msg, uid=remote.uid)
                self.serviceOne(stack, duration=0.01, step=0.01)

        self.serviceOne(stack, duration=duration, timeout=1.0)

        console.terse("\nStack '{0}' uid={1}\n".format(stack.name, stack.local.uid))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(stack.rxMsgs), len(msgs) * len(stack.remotes))
        for i, duple in enumerate(stack.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(stack.local.name, duple))
            self.assertDictEqual(msgs[0], duple[0]) # TODO: make all messages differ

    def masterPeer(self, name, port, minionCount):
        # create stack
        self.stack = self.createStack(name, port)

        self.serviceOne(self.stack)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), minionCount)
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)

        self.bidirectional(self.stack, msgs=self.data, duration=self.duration)

    def minionPeer(self, name, port, remoteAddresses):
        # Create stack
        self.stack = self.createStack(name, port)

        self.joinAll(self.stack, remoteAddresses)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)

        self.allowAll(self.stack)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.allowed)

        self.bidirectional(self.stack, msgs=self.data, duration=self.duration)

    def bidirectionalMultiPeers(self,
                                masterCount=1,
                                minionCount=1,
                                msgSize=1024,
                                msgCount=10,
                                duration=10.0):
        data = self.createData(size=msgSize)
        self.data = [data for a in xrange(msgCount)]
        self.duration = duration

        port = raeting.RAET_PORT
        masterHostAddresses = []
        masterProcs = []
        for i in xrange(masterCount):
            masterHostAddresses.append(('', port))
            name = 'master{0}'.format(i)
            masterProc = multiprocessing.Process(target=self.masterPeer,
                                                 name=name,
                                                 args=(name,
                                                       port,
                                                       minionCount))
            masterProcs.append(masterProc)
            port += 1

        minionProcs = []
        for i in xrange(minionCount):
            name = 'minion{0}'.format(i)
            minionProc = multiprocessing.Process(target=self.minionPeer,
                                                 name=name,
                                                 args=(name,
                                                       port,
                                                       masterHostAddresses))
            minionProcs.append(minionProc)
            port += 1

        for masterProc in masterProcs:
            masterProc.start()
        for minionProc in minionProcs:
            minionProc.start()
        self.engine = True

        for masterProc in masterProcs:
            masterProc.join()
        for minionProc in minionProcs:
            minionProc.join()

        for masterProc in masterProcs:
            self.assertEqual(masterProc.exitcode, 0)
        for minionProc in minionProcs:
            self.assertEqual(minionProc.exitcode, 0)

    def testOneToOne(self):
        self.bidirectionalMultiPeers(masterCount=1,
                                     minionCount=1,
                                     msgSize=1024*10,
                                     msgCount=10,
                                     duration=10.0)

    def testManyToOne(self):
        self.bidirectionalMultiPeers(masterCount=1,
                                     minionCount=5,
                                     msgSize=1024*10,
                                     msgCount=10,
                                     duration=100.0)
    def testOneToMany(self):
        self.bidirectionalMultiPeers(masterCount=3,
                                     minionCount=1,
                                     msgSize=1024*10,
                                     msgCount=10,
                                     duration=100.0)
    def testManyToMany(self):
        self.bidirectionalMultiPeers(masterCount=3,
                                     minionCount=5,
                                     msgSize=1024*10,
                                     msgCount=10,
                                     duration=100.0)

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
    names = [
        'testOneToOne',
        'testManyToOne',
        'testOneToMany',
        'testManyToMany'
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

    runAll()  #run all unittests

    #runSome()  #only run some

