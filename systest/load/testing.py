# -*- coding: utf-8 -*-
'''
Load test for Raet Road Stack

'''
from __future__ import print_function
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import multiprocessing
import os
import shutil
import tempfile
import time

from ioflo.base import storing
from ioflo.base.aiding import StoreTimer

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet import raeting, nacling
from raet.road import keeping, estating, stacking, transacting

from systest.lib import data, mp_helper

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

MULTI_MASTER_COUNT = 3
MULTI_MINION_COUNT = 5
MSG_SIZE_MED = 1024
MSG_COUNT_MED = 100
DIR_BIDIRECTIONAL = 'bidirectional'
DIR_TO_MASTER = 'to_master'
DIR_FROM_MASTER = 'from_master'
MAX_TRANSACTIONS = 10


class BasicLoadTestCase(unittest.TestCase):
    """"""

    def __init__(self, *args, **kwargs):
        super(BasicLoadTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)
        self.baseDirpath = tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)
        self.stack = None
        # This has to be set to True in the only one process that would perform tearDown steps
        self.engine = True
        stacking.RoadStack.BurstSize = 100

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

    def joinAll(self, initiator, correspondentAddresses, timeout=None):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        for ha in correspondentAddresses:
            remote = initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                               fuid=0,  # vacuous join
                                                               sid=0,  # always 0 for join
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

    def serviceAll(self, stacks, duration=100.0, timeout=0.0, step=0.1, exitCase=None):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        empty = False
        elapsed = self.timer.getElapsed()
        retReason = 'duration'
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAll()
            if any(stack.transactions for stack in stacks):
                empty = False  # reset nop timeout
            else:
                if exitCase and exitCase():
                    retReason = 'exitCase'
                    break
                if empty:
                    if self.timer.getElapsed() - elapsed > timeout:
                        retReason = 'timeout'
                        break
                else:
                    empty = True
                    elapsed = self.timer.getElapsed()
            self.store.advanceStamp(step)
            time.sleep(step)
        return retReason

    def serviceOne(self, stack, duration=100.0, timeout=0.0, step=0.1, exitCase=None):
        return self.serviceAll([stack], duration, timeout, step, exitCase)

    def bidirectional(self, stack, duration=3.0):
        console.terse("\nMessages Bidirectional {0} *********\n".format(stack.name))
        verifier = data.MessageVerifier(size=self.msgSize, msgCount=self.msgCount, remoteCount=len(stack.remotes),
                                        house='manor', queue='stuff')
        received = 0
        expected = len(stack.remotes) * self.msgCount
        for msg in data.generateMessages(name=self.stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                # send message
                stack.transmit(msg, uid=remote.uid)
                while True:
                    self.serviceOne(stack, duration=0.01, step=0.01)
                    # check received
                    if stack.rxMsgs:
                        received += len(stack.rxMsgs)
                        while stack.rxMsgs:
                            verifier.verifyMessage(stack.rxMsgs.popleft())
                    # keep servicing if there are a lot of transactions
                    if len(stack.transactions) <= MAX_TRANSACTIONS:
                        break

        while received < expected:
            self.serviceOne(stack, duration=duration, timeout=duration,
                            exitCase=lambda: stack.rxMsgs)
            # if received nothing during timeout, assume we're done
            if not stack.rxMsgs:
                break
            received += len(stack.rxMsgs)
            while stack.rxMsgs:
                verifier.verifyMessage(stack.rxMsgs.popleft())

        # wait remaining messenger transactions if any to be closed
        if stack.transactions:
            self.serviceOne(stack, duration=duration)

        # Done. Wait others
        self.doneCounter.inc()
        elapsed = 0.0  # be safe from engine unexpected stop
        step = 1.0
        while not self.stopFlag.get() and elapsed < duration * 2:
            self.serviceOne(stack, duration=step, timeout=step)
            elapsed += step

        console.terse("\nStack '{0}' uid={1}\n\tTransactions: {2}\n\trcv/exp: {3}/{4}\n\tStats: {5}\n"
                      .format(stack.name, stack.local.uid, stack.transactions, received, expected, stack.stats))
        rcvErrors = verifier.checkAllDone()
        if rcvErrors:
            console.terse("{0} received message with the following errors:\n".format(stack.name))
            for s in rcvErrors:
                console.terse("\t{0} from {1}\n".format(stack.name, s))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(rcvErrors), 0)
        self.assertEqual(received, expected)

    def send(self, stack, duration=3.0):
        console.terse("\nMessages Sender {0} *********\n".format(stack.name))
        for msg in data.generateMessages(name=stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                stack.transmit(msg, uid=remote.uid)
                while True:
                    self.serviceOne(stack, duration=0.01, step=0.01)
                    if len(stack.transactions) <= MAX_TRANSACTIONS:
                        break

        self.serviceOne(stack, duration=duration, timeout=3.0)

        # Done. Wait others
        self.doneCounter.inc()
        elapsed = 0.0  # be safe from engine unexpected stop
        step = 1.0
        while not self.stopFlag.get() and elapsed < duration * 2:
            self.serviceOne(stack, duration=step, timeout=step)
            elapsed += step

        console.terse("\nStack '{0}' uid={1}\n\tTransactions: {2}\n\tStats: {3}\n"
                      .format(stack.name, stack.local.uid, stack.transactions, stack.stats))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(stack.rxMsgs), 0)

    def receive(self, stack, duration=3.0):
        console.terse("\nMessages Receiver {0} *********\n".format(stack.name))
        verifier = data.MessageVerifier(size=self.msgSize, msgCount=self.msgCount, remoteCount=len(stack.remotes),
                                        house='manor', queue='stuff')

        # Receive messages
        received = 0
        expected = len(stack.remotes) * self.msgCount
        while received < expected:
            reason = self.serviceOne(stack, duration=duration, timeout=duration,
                                     exitCase=lambda: stack.rxMsgs)
            console.terse("{0} service exit reason: {1}, transactions: {2}\n".format(
                stack.name, reason, stack.transactions))
            # received nothing during timeout, assume there is nothing to receive
            if not stack.rxMsgs:
                break
            received += len(stack.rxMsgs)
            while stack.rxMsgs:
                verifier.verifyMessage(stack.rxMsgs.popleft())

        # Done. Wait others
        self.doneCounter.inc()
        elapsed = 0.0  # be safe from engine unexpected stop
        step = 1.0
        while not self.stopFlag.get() and elapsed < duration * 2:
            self.serviceOne(stack, duration=step, timeout=step)
            elapsed += step

        # Verify results
        console.terse("\nStack '{0}' uid={1}\n\tTransactions: {2}\n\trcv/exp: {3}/{4}\n\tStats: {5}\n"
                      .format(stack.name, stack.local.uid, stack.transactions, received, expected, stack.stats))
        for t in stack.transactions:
            if isinstance(t, transacting.Messengent):
                print("Tray lost segments: {0}\n".format([i for i, x in enumerate(t.tray.segments) if x is None]))
        rcvErrors = verifier.checkAllDone()
        if rcvErrors:
            console.terse("{0} received message with the following errors:\n".format(stack.name))
            for s in rcvErrors:
                console.terse("\t{0} from {1}\n".format(stack.name, s))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(rcvErrors), 0)
        self.assertEqual(received, expected)

    def masterPeer(self, name, port, minionCount, action):
        self.engine = False
        # create stack
        self.stack = self.createStack(name, port)

        console.terse("\nCreated {0} at {1} *********\n".format(name, self.stack.ha))

        console.terse("\n{0} Waiting For Minions *********\n".format(name))

        def isBootstrapDone():
            if not self.stack.remotes:
                return False
            if len(self.stack.remotes) != minionCount:
                return False
            for rmt in self.stack.remotes.values():
                if not rmt.allowed:
                    return False
            return True

        serviceCode = self.serviceOne(self.stack, timeout=100.0, exitCase=isBootstrapDone)

        console.terse("\n{0} bootstrap done with code {1}".format(name, serviceCode))

        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), minionCount)
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)

        console.terse("\n{0} Bootstrap Done ({1}) *********\n".format(name, serviceCode))

        action(self.stack, duration=self.duration)

    def minionPeer(self, name, port, remoteAddresses, action):
        self.engine = False
        # Create stack
        self.stack = self.createStack(name, port)

        console.terse("\nCreated {0} at {1} *********\n".format(name, self.stack.ha))

        console.terse("\n{0} Joining Remotes *********\n".format(name))

        self.joinAll(self.stack, remoteAddresses)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined, "{0}: remote '{1}' at {2} is not joined".format(
                name, remote.name, remote.ha))

        console.terse("\n{0} Allowing Remotes *********\n".format(name))

        self.allowAll(self.stack)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.allowed, "{0}: remote '{1}' at {2} is not allowed".format(
                name, remote.name, remote.ha))

        console.terse("\n{0} Bootstrap Done *********\n".format(name))

        action(self.stack, duration=self.duration)

    def messagingMultiPeers(self,
                            masterCount,
                            minionCount,
                            msgSize,
                            msgCount,
                            duration,
                            direction):
        self.masterCount = masterCount
        self.minionCount = minionCount
        self.msgSize = msgSize
        self.msgCount = msgCount
        self.duration = duration
        masterDir = {DIR_BIDIRECTIONAL: self.bidirectional,
                     DIR_TO_MASTER:     self.receive,
                     DIR_FROM_MASTER:   self.send}
        minionDir = {DIR_BIDIRECTIONAL: self.bidirectional,
                     DIR_TO_MASTER:     self.send,
                     DIR_FROM_MASTER:   self.receive}

        port = raeting.RAET_PORT
        masterHostAddresses = []
        masterProcs = []
        self.doneCounter = mp_helper.Counter()
        self.stopFlag = mp_helper.Counter()
        for i in xrange(masterCount):
            masterHostAddresses.append(('', port))
            name = 'master{0}'.format(i)
            masterProc = multiprocessing.Process(target=self.masterPeer,
                                                 name=name,
                                                 args=(name,
                                                       port,
                                                       minionCount,
                                                       masterDir[direction]))
            masterProcs.append(masterProc)
            port += 1

        minionProcs = []
        for i in xrange(minionCount):
            name = 'minion{0}'.format(i)
            minionProc = multiprocessing.Process(target=self.minionPeer,
                                                 name=name,
                                                 args=(name,
                                                       port,
                                                       masterHostAddresses,
                                                       minionDir[direction]))
            minionProcs.append(minionProc)
            port += 1

        for proc in masterProcs:
            proc.start()
        time.sleep(1.0)  # let masters start
        for proc in minionProcs:
            proc.start()

        # Wait all workers done their job
        elapsed = 0.0  # be safe from worker unexpected stop
        step = 1.0
        while self.doneCounter.get() < masterCount + minionCount and elapsed < duration * 2:
            time.sleep(step)
            elapsed += step
        # Set stop flag
        self.stopFlag.inc()

        for procs in (masterProcs, minionProcs):
            for proc in procs:
                proc.join()

        for procs in (masterProcs, minionProcs):
            for proc in procs:
                self.assertEqual(proc.exitcode, 0, "'{0}' returned {1}".format(proc.name, proc.exitcode))
