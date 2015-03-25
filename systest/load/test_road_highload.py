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
from nose_parameterized import parameterized
from ddt import ddt, data, unpack

import os
import sys
import time
import tempfile
import shutil
import multiprocessing

from BitVector import BitVector

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
    # console.reinit(verbosity=console.Wordage.terse)
    console.reinit(verbosity=console.Wordage.concise)


def tearDownModule():
    pass

MULTI_MASTER_COUNT = 3
MULTI_MINION_COUNT = 5
MSG_SIZE_MED = 1024
MSG_COUNT_MED = 100
DIR_BIDIRECTIONAL = 'bidirectional'
DIR_TO_MASTER = 'to_master'
DIR_FROM_MASTER = 'from_master'


def getStuff(name='master', size=1024, number=0):
    alpha = '{0}{1}{2}{3}'.format(name, number,
                                  ''.join([chr(n) for n in xrange(ord('A'), ord('Z') + 1)]),
                                  ''.join([chr(n) for n in xrange(ord('a'), ord('z') + 1)]))
    num = size / len(alpha)
    ret = ''.join([alpha for _ in xrange(num)])
    num = size - len(ret)
    ret = ''.join([ret, alpha[:num]])
    assert len(ret) == size, 'Coding fault: generated data size not equal to requested'
    return ret


def createData(name='master', size=1024, number=0, house='manor', queue='stuff'):
    stuff = getStuff(name, size, number)
    ret = odict(house=house, queue=queue, sender=name, number=number, stuff=stuff)
    return ret


def generateMessages(name, size, count, house='manor', queue='stuff'):
    for i in xrange(count):
        yield createData(name, size, i, house, queue)


class MessageVerifier():
    def __init__(self, size, count, house, queue):
        self.size = size
        self.count = count
        self.house = house
        self.queue = queue
        self.received = {}

    def verifyMessage(self, msg):
        sender = msg[0]['sender']
        number = msg[0]['number']
        expectedMsg = createData(sender, self.size, number, self.house, self.queue)
        equal = expectedMsg == msg[0]

        if sender not in self.received:
            self.received[sender] = (BitVector(size=self.count),  # received
                                     BitVector(size=self.count),  # duplicated
                                     BitVector(size=self.count))  # wrong content

        if self.received[sender][0][number]:  # duplicate
            self.received[sender][1][number] = 1
        else:  # first time received
            self.received[sender][0][number] = 1
        if not equal:
            self.received[sender][2][number] = 1

    def checkAllDone(self, remoteCount, msgCount):
        errors = []
        for name, results in self.received.iteritems():
            rcv = results[0].count_bits()
            dup = results[1].count_bits()
            bad = results[2].count_bits()
            if rcv != self.count:
                errors.append('{0}: lost {1} messages'.format(name, self.count - rcv))
            if dup:
                errors.append('{0}: got duplications for {1} messages'.format(name, dup))
            if bad:
                errors.append('{0}: {1} received messages are broken'.format(name, bad))
        return errors


# @ddt
class BasicTestCase(unittest.TestCase):
    """"""

    def __init__(self, *args, **kwargs):
        super(BasicTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)
        self.baseDirpath = tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)
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
        verifier = MessageVerifier(size=self.msgSize, count=self.msgCount, house='manor', queue='stuff')
        received = 0
        expected = len(stack.remotes) * self.msgCount
        for msg in generateMessages(name=self.stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                # send message
                stack.transmit(msg, uid=remote.uid)
                self.serviceOne(stack, duration=0.01, step=0.01)
                # check received
                if stack.rxMsgs:
                    received += len(stack.rxMsgs)
                    while stack.rxMsgs:
                        verifier.verifyMessage(stack.rxMsgs.popleft())

        while received < expected:
            self.serviceOne(stack, duration=3.0, timeout=3.0,
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

        console.terse("\nStack '{0}' uid={1}\n\tTransactions: {2}\n\trcv/exp: {3}/{4}\n\tStats: {5}\n"
                      .format(stack.name, stack.local.uid, stack.transactions, received, expected, stack.stats))
        self.assertEqual(len(stack.transactions), 0)
        rcvErrors = verifier.checkAllDone(remoteCount=len(stack.remotes), msgCount=self.msgCount)
        if rcvErrors:
            console.terse("{0} received message with the following errors:\n".format(stack.name))
            for s in rcvErrors:
                console.terse("\t{0} from {1}\n".format(stack.name, s))
        self.assertEqual(len(rcvErrors), 0)
        self.assertEqual(received, expected)

    def send(self, stack, msgs=None, duration=3.0):
        msgs = msgs or []

        console.terse("\nMessages Sender {0} *********\n".format(stack.name))
        for msg in generateMessages(name=stack.name, size=self.msgSize, count=self.msgCount):
            for remote in stack.remotes.values():
                stack.transmit(msg, uid=remote.uid)
                self.serviceOne(stack, duration=0.01, step=0.01)

        serviceCode = self.serviceOne(stack, duration=duration, timeout=1.0)

        console.terse("\nStack '{0}' uid={1} serviceCode={2}\n".format(stack.name, stack.local.uid, serviceCode))
        self.assertEqual(len(stack.transactions), 0)
        self.assertEqual(len(stack.rxMsgs), 0)

    def receive(self, stack, msgs=None, duration=3.0):
        msgs = msgs or []

        console.terse("\nMessages Receiver {0} *********\n".format(stack.name))

        verifier = MessageVerifier(size=self.msgSize, count=self.msgCount, house='manor', queue='stuff')
        received = 0
        expected = len(stack.remotes) * self.msgCount
        while received < expected:
            self.serviceOne(stack, duration=3.0, timeout=3.0,
                            exitCase=lambda: len(stack.rxMsgs) >= min(10, expected - received))
            # received nothing during timeout, assume there is nothing to receive
            if not stack.rxMsgs:
                break

            received += len(stack.rxMsgs)

            while stack.rxMsgs:
                rcvMsg = stack.rxMsgs.popleft()
                verifier.verifyMessage(rcvMsg)

        console.terse("\nStack '{0}' uid={1}\n".format(stack.name, stack.local.uid))
        self.assertEqual(len(stack.transactions), 0)
        rcvErrors = verifier.checkAllDone(remoteCount=len(stack.remotes), msgCount=self.msgCount)
        if rcvErrors:
            console.terse("Receive message with the following errors:\n")
            for s in rcvErrors:
                console.terse("\t{0}".format(s))
        self.assertEqual(len(rcvErrors), 0)
        self.assertEqual(received, expected)

    def masterPeer(self, name, port, minionCount, action):
        # create stack
        self.stack = self.createStack(name, port)

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

        serviceCode = self.serviceOne(self.stack, timeout=10.0, exitCase=isBootstrapDone)

        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), minionCount)
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)

        console.terse("\n{0} Bootstrap Done ({1}) *********\n".format(name, serviceCode))

        action(self.stack, duration=self.duration)

    def minionPeer(self, name, port, remoteAddresses, action):
        # Create stack
        self.stack = self.createStack(name, port)

        console.terse("\n{0} Joining Remotes *********\n".format(name))

        self.joinAll(self.stack, remoteAddresses)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.joined)

        console.terse("\n{0} Allowing Remotes *********\n".format(name))

        self.allowAll(self.stack)
        self.assertEqual(len(self.stack.transactions), 0)
        self.assertEqual(len(self.stack.remotes), len(remoteAddresses))
        for remote in self.stack.remotes.values():
            self.assertTrue(remote.allowed)

        console.terse("\n{0} Bootstrap Done *********\n".format(name))

        action(self.stack, duration=self.duration)

    # @parameterized.expand([
    #     ("To Master One To One",       1, 1, 1024, 10, 100.0, "to_master"),
    #     ("To Master Many To One",      1, 5, 1024, 10, 100.0, "to_master"),
    #     ("To Master One To Many",      3, 1, 1024, 10, 100.0, "to_master"),
    #     ("To Master Many To Many",     3, 5, 1024, 10, 100.0, "to_master"),
    #     ("From Master One To One",     1, 1, 1024, 10, 100.0, "from_master"),
    #     ("From Master Many To One",    1, 5, 1024, 10, 100.0, "from_master"),
    #     ("From Master One To Many",    3, 1, 1024, 10, 100.0, "from_master"),
    #     ("From Master Many To Many",   3, 5, 1024, 10, 100.0, "from_master"),
    #     ("Bidirectional One To One",   1, 1, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional Many To One",  1, 5, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional One To Many",  3, 1, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional Many To Many", 3, 5, 1024, 10, 100.0, "bidirectional")
    # ])
    # @data(
    #     ("To Master One To One",       1, 1, 1024, 10, 100.0, "to_master"),
    #     ("To Master Many To One",      1, 5, 1024, 10, 100.0, "to_master"),
    #     ("To Master One To Many",      3, 1, 1024, 10, 100.0, "to_master"),
    #     ("To Master Many To Many",     3, 5, 1024, 10, 100.0, "to_master"),
    #     ("From Master One To One",     1, 1, 1024, 10, 100.0, "from_master"),
    #     ("From Master Many To One",    1, 5, 1024, 10, 100.0, "from_master"),
    #     ("From Master One To Many",    3, 1, 1024, 10, 100.0, "from_master"),
    #     ("From Master Many To Many",   3, 5, 1024, 10, 100.0, "from_master"),
    #     ("Bidirectional One To One",   1, 1, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional Many To One",  1, 5, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional One To Many",  3, 1, 1024, 10, 100.0, "bidirectional"),
    #     ("Bidirectional Many To Many", 3, 5, 1024, 10, 100.0, "bidirectional"),
    # )
    # @unpack
    def messagingMultiPeers(self,
                            # name,
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
        master_dir = {DIR_BIDIRECTIONAL: self.bidirectional,
                      DIR_TO_MASTER:     self.receive,
                      DIR_FROM_MASTER:   self.send}
        minion_dir = {DIR_BIDIRECTIONAL: self.bidirectional,
                      DIR_TO_MASTER:     self.send,
                      DIR_FROM_MASTER:   self.receive}

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
                                                       minionCount,
                                                       master_dir[direction]))
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
                                                       minion_dir[direction]))
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

    def testOneToOneToMaster(self):
        console.terse("{0}\n".format(self.testOneToOneToMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_TO_MASTER)

    def testManyToOneToMaster(self):
        console.terse("{0}\n".format(self.testManyToOneToMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_TO_MASTER)

    def testOneToManyToMaster(self):
        console.terse("{0}\n".format(self.testOneToManyToMaster.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_TO_MASTER)

    def testManyToManyToMaster(self):
        console.terse("{0}\n".format(self.testManyToManyToMaster.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_TO_MASTER)

    def testOneToOneFromMaster(self):
        console.terse("{0}\n".format(self.testOneToOneFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_FROM_MASTER)

    def testManyToOneFromMaster(self):
        console.terse("{0}\n".format(self.testManyToOneFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_FROM_MASTER)

    def testOneToManyFromMaster(self):
        console.terse("{0}\n".format(self.testOneToManyFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_FROM_MASTER)

    def testManyToManyFromMaster(self):
        console.terse("{0}\n".format(self.testManyToManyFromMaster.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_FROM_MASTER)

    def testOneToOneBidirectional(self):
        console.terse("{0}\n".format(self.testOneToOneBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)

    def testManyToOneBidirectional(self):
        console.terse("{0}\n".format(self.testManyToOneBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=1,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)

    def testOneToManyBidirectional(self):
        console.terse("{0}\n".format(self.testOneToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=1,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)

    def testManyToManyBidirectional(self):
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=MULTI_MASTER_COUNT,
                                 minionCount=MULTI_MINION_COUNT,
                                 msgSize=MSG_SIZE_MED,
                                 msgCount=MSG_COUNT_MED,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)

    def testManyToManyBidirectional1(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024,
                                 msgCount=100,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}'.format(e-s))

    def testManyToManyBidirectional2(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024*10,
                                 msgCount=100,
                                 duration=100.0,
                                 direction=DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}'.format(e-s))

    def testManyToManyBidirectional3(self):
        from datetime import datetime as dt
        s = dt.now()
        console.terse("{0}\n".format(self.testManyToManyBidirectional.__doc__))
        self.messagingMultiPeers(masterCount=3,
                                 minionCount=5,
                                 msgSize=1024*100,
                                 msgCount=100,
                                 duration=1000.0,
                                 direction=DIR_BIDIRECTIONAL)
        e = dt.now()
        console.terse('Test time: {0}'.format(e-s))


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

    # console.reinit(verbosity=console.Wordage.concise)

    runAll()  # run all unittests

    # runSome()  #only run some
