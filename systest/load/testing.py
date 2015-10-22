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

from ioflo.base.storing import Store
from ioflo.aid.timing import StoreTimer

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

# Test constants. Can be used for tune the test.
MULTI_MASTER_COUNT = 3
MULTI_MINION_COUNT = 5
MSG_SIZE_MED = 1024
MSG_SIZE_BIG = 1024*1024
MSG_COUNT_MED = 100
DIR_BIDIRECTIONAL = 'bidirectional'
DIR_TO_MASTER = 'to_master'
DIR_FROM_MASTER = 'from_master'
MAX_TRANSACTIONS = 10


class BasicLoadTestCase(unittest.TestCase):
    '''
    Base class for load tests. Provides generic master/slave runners with flooding and checking logic.
    '''

    def __init__(self, *args, **kwargs):
        super(BasicLoadTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        self.store = Store(stamp=0.0)
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
        '''
        Create a RoadStack object bound to the specified port on localhost.

        :param name: stack name
        :param port: port to bind to
        :return: the stack
        '''
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

    def joinAll(self, initiator, correspondentAddresses, timeout=None, retryCount=1):
        '''
        Utility method to do join.

        :param initiator: join initiator stack
        :param correspondentAddresses: an iterable object containing ha tuples
        :param timeout: join timeout, will be passed to stack
        :param retryCount: retry join max the specified count of times until success
        '''
        console.terse("\nJoin Transaction **************\n")
        addresses = list(correspondentAddresses)
        for ha in addresses:
            initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                      fuid=0,  # vacuous join
                                                      sid=0,  # always 0 for join
                                                      ha=ha))
        while retryCount > 0:
            done = True
            for remote in initiator.remotes.values():
                if not remote.joined:
                    done = False
                    initiator.join(uid=remote.uid, timeout=timeout)
            self.serviceOne(initiator)
            if done:
                break
            retryCount -= 1

    def allowAll(self, initiator, timeout=None, retryCount=1):
        '''
        Utility method to do allow.

        :param initiator: allow initiator stack
        :param timeout: allow timeout, will be passed to stack
        :param retryCount: retry allow max the specified count of times until success
        '''
        console.terse("\nAllow Transaction **************\n")
        while retryCount > 0:
            done = True
            for remote in initiator.remotes.values():
                if not remote.allowed:
                    done = False
                    initiator.allow(uid=remote.uid, timeout=timeout)
            self.serviceOne(initiator)
            if done:
                break
            retryCount -= 1

    def serviceAll(self, stacks, duration=100.0, timeout=0.0, step=0.1, exitCase=None):
        '''
        Utility method to service queues.

        :param stacks: iterable containing stacks to service
        :param duration: max service duration, actually could finish earlier if there still no transactions to service
        :param timeout: time to continue service even if there are no transactions
        :param step: timer step
        :param exitCase: stop immediately if this function return true
        :return: actual exit reason, could be one of 'duration', 'exitCase' or 'timeout'
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
        '''
        Utility method to service one stack. See :func:`serviceStacks`.
        '''
        return self.serviceAll([stack], duration, timeout, step, exitCase)

    def bidirectional(self, stack, duration=3.0):
        '''
        Simultaneously sends and receives test messages.
            - self.msgSize: message size
            - self.msgCount: per remote message count

        :param stack: the stack to service
        :param duration: service duration to prevent hang
        '''
        console.terse("\nMessages Bidirectional {0} *********\n".format(stack.name))
        verifier = data.MessageVerifier(size=self.msgSize, msgCount=self.msgCount, remoteCount=len(stack.remotes),
                                        house='manor', queue='stuff')
        received = 0
        expected = len(stack.remotes) * self.msgCount
        maxTransactions = MAX_TRANSACTIONS * len(stack.remotes)
        for msg in data.generateMessages(name=stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                # send message
                stack.transmit(msg, uid=remote.uid)
                # service while there are too much transactions (but loops at least once)
                while True:
                    self.serviceOne(stack, duration=0.01, step=0.01)
                    # check received
                    if stack.rxMsgs:
                        received += len(stack.rxMsgs)
                        while stack.rxMsgs:
                            verifier.verifyMessage(stack.rxMsgs.popleft())
                    # keep servicing if there are a lot of transactions
                    if len(stack.transactions) <= maxTransactions:
                        break

        # all sent, continue handle received
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

        # check result
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
        '''
        Sends test messages.
            - self.msgSize: message size
            - self.msgCount: per remote message count

        :param stack: the stack to service
        :param duration: service duration to prevent hang
        '''
        console.terse("\nMessages Sender {0} *********\n".format(stack.name))
        maxTransactions = MAX_TRANSACTIONS * len(stack.remotes)
        for msg in data.generateMessages(name=stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                # send message
                stack.transmit(msg, uid=remote.uid)
                # service while there are too much transactions (but loops at least once)
                while True:
                    self.serviceOne(stack, duration=0.01, step=0.01)
                    if len(stack.transactions) <= maxTransactions:
                        break

        # done, wait others
        self.doneCounter.inc()
        elapsed = 0.0  # be safe from engine unexpected stop
        step = 1.0
        while not self.stopFlag.get() and elapsed < duration * 2:
            self.serviceOne(stack, duration=step, timeout=step)
            elapsed += step

        # check result
        console.terse("\nStack '{0}' uid={1}\n\tTransactions: {2}\n\tStats: {3}\n"
                      .format(stack.name, stack.local.uid, stack.transactions, stack.stats))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(stack.rxMsgs), 0)

    def receive(self, stack, duration=3.0):
        '''
        Receives test messages.
            - self.msgSize: message size
            - self.msgCount: per remote message count

        :param stack: the stack to service
        :param duration: service duration to prevent hang
        '''
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
        '''
        Master peer main function. It creates a RoadStack, sends/receives a bunch of test messages to remote peers and
        checks the result

        :param name: the name of this peer
        :param port: port to bind to
        :param minionCount: count of remote peers
        :param action: action function. Could be one of self.send, self.receive or self.bidirectional
        :return: if done without errors the process will end with 0 exit code
        '''
        self.engine = False
        # create stack
        self.stack = self.createStack(name, port)

        console.terse("\nCreated {0} at {1} *********\n".format(name, self.stack.ha))

        console.terse("\n{0} Waiting For Minions *********\n".format(name))

        # wait minions to join and allow
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

        # verify all minions connected
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), minionCount)
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)

        console.terse("\n{0} Bootstrap Done ({1}) *********\n".format(name, serviceCode))
        # do the job
        action(self.stack, duration=self.duration)

    def minionPeer(self, name, port, remoteAddresses, action):
        '''
        Slave peer main function. It creates a RoadStack, sends/receives a bunch of test messages to remote peers and
        checks the result

        :param name: the name of this peer
        :param port: port to bind to
        :param minionCount: count of remote peers
        :param action: action function. Could be one of self.send, self.receive or self.bidirectional
        :return: if done without errors the process will end with 0 exit code
        '''
        self.engine = False
        # Create stack
        self.stack = self.createStack(name, port)

        console.terse("\nCreated {0} at {1} *********\n".format(name, self.stack.ha))

        console.terse("\n{0} Joining Remotes *********\n".format(name))
        # join with all masters
        self.joinAll(self.stack, remoteAddresses, retryCount=10)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined, "{0}: remote '{1}' at {2} is not joined".format(
                name, remote.name, remote.ha))

        console.terse("\n{0} Allowing Remotes *********\n".format(name))
        # allow all masters
        self.allowAll(self.stack, retryCount=10)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.allowed, "{0}: remote '{1}' at {2} is not allowed".format(
                name, remote.name, remote.ha))

        console.terse("\n{0} Bootstrap Done *********\n".format(name))
        # do the job
        action(self.stack, duration=self.duration)

    def messagingMultiPeers(self,
                            masterCount,
                            minionCount,
                            msgSize,
                            msgCount,
                            duration,
                            direction):
        '''
        Perform the test. This function creates a number of processes which are master and slave network peers. Each
        process sends a bunch of messages to each process from the opposite group (for bidirectional case)

        :param masterCount: count of master peers
        :param minionCount: count of slave peers
        :param msgSize: size of the message stuff, actually the message would be bigger
        :param msgCount: count of messages to be sent from peer to peer
        :param duration: test duration limit, will be used in service calls so actual allowed duration will be greater
        :param direction: sending duration, could be one of DIR_TO_MASTER, DIR_FROM_MASTER or DIR_BIDIRECTIONAL
        :return: throw PyUnit assertion if fail
        '''
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

        # create masters
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

        # create minions
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

        # start masters first
        for proc in masterProcs:
            proc.start()
        time.sleep(1.0)  # let masters start
        # start minions
        for proc in minionProcs:
            proc.start()

        # wait until all workers done their job
        elapsed = 0.0  # be safe from worker unexpected stop
        step = 1.0
        while self.doneCounter.get() < masterCount + minionCount and elapsed < duration * 2:
            time.sleep(step)
            elapsed += step
        # set stop flag
        self.stopFlag.inc()

        # wait all processes exited
        for procs in (masterProcs, minionProcs):
            for proc in procs:
                proc.join()

        # ensure all workers successfully done
        for procs in (masterProcs, minionProcs):
            for proc in procs:
                self.assertEqual(proc.exitcode, 0, "'{0}' returned {1}".format(proc.name, proc.exitcode))
