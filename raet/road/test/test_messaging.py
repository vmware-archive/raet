# -*- coding: utf-8 -*-
'''
Tests for messaging reliability

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import time
import tempfile
import shutil
from collections import deque

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.aid.aiding import just
from ioflo.base.storing import Store
from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import estating, keeping, stacking, packeting, transacting

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
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self,
                       base,
                       name='',
                       ha=None,
                       main=None,
                       auto=raeting.AutoMode.never.value,
                       role=None,
                       kind=None, ):
        '''
        Creates odict and populates with data to setup road stack

        '''
        data = odict()
        data['name'] = name
        data['ha'] = ha
        data['main'] =  main
        data['auto'] = auto
        data['role'] = role if role is not None else name
        data['kind'] = kind
        data['dirpath'] = os.path.join(base, 'road', 'keep', name)
        signer = nacling.Signer()
        data['sighex'] = signer.keyhex
        data['verhex'] = signer.verhex
        privateer = nacling.Privateer()
        data['prihex'] = privateer.keyhex
        data['pubhex'] = privateer.pubhex

        return data

    def createRoadStack(self,
                        data,
                        uid=None,
                        ha=None,
                        main=None,
                        auto=None,
                        role=None,
                        kind=None,
                        period=None,
                        offset=None,):
        '''
        Creates stack and local estate from data with
        and overrides with parameters

        returns stack

        '''
        stack = stacking.RoadStack(store=self.store,
                                   name=data['name'],
                                   uid=uid,
                                   ha=ha or data['ha'],
                                   main=main if main is not None else data['main'],
                                   role=role if role is not None else data['role'],
                                   sigkey=data['sighex'],
                                   prikey=data['prihex'],
                                   auto=auto if auto is not None else data['auto'],
                                   kind=kind if kind is not None else data['kind'],
                                   dirpath=data['dirpath'],
                                   period=period,
                                   offset=offset,)

        return stack

    def join(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        if not initiator.remotes:
            initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=correspondent.local.ha))
        initiator.join(uid=deid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def allow(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        initiator.allow(uid=deid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def alive(self, initiator, correspondent, duid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do alive. Call from test method.
        '''
        console.terse("\nAlive Transaction **************\n")
        initiator.alive(uid=duid, cascade=cascade)
        self.serviceStacks([correspondent, initiator], duration=duration)

    def message(self, msgs, initiator, correspondent, duration=2.0):
        '''
        Utility to send messages both ways
        '''
        for msg in msgs:
            initiator.transmit(msg)

        self.serviceStacks([initiator, correspondent], duration=duration)

    def flushReceives(self, stack):
        '''
        Flush any queued up udp packets in receive buffer
        '''
        stack.serviceReceives()
        stack.rxes.clear()

    def dupReceives(self, stack):
        '''
        Duplicate each queued up udp packet in receive buffer
        '''
        stack.serviceReceives()
        rxes = stack.rxes
        stack.rxes = deque()
        for rx in rxes:
            stack.rxes.append(rx) # one
            stack.rxes.append(rx) # and one more

    def serviceStack(self, stack, duration=1.0):
        '''
        Utility method to service queues for one stack. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            stack.serviceAll()
            if not (stack.transactions):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def serviceStacks(self, stacks, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAll()
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def serviceStacksWithDrops(self, stacks, dropage=None, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        Drops tx msgs in .txes deque based on drops filter which is list
        of truthy falsey values. For each element of drops if truthy then drop
        the tx at the corresponding index for each service of the txes deque.
        '''
        if dropage is None:
            dropage = [[], []]
        for k in range(len(stacks) - len(dropage)):
            dropage.append([])  # ensure a drops list per stack even if empty
        indices =  []
        for stack in stacks:
            indices.append(0)

        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for i, stack in enumerate(stacks):
                stack.serviceTxMsgs()
                drops = dropage[i]
                j = indices[i]
                while stack.txes:
                    try:
                        drop = drops[j]
                    except IndexError:
                        drop = False

                    if drop:
                        stack.txes.popleft()  # pop and drop
                        console.concise("Stack {0}: Dropping {1}\n".format(stack.name, j))
                    else:
                        stack.serviceTxOnce() # service
                    j += 1
                indices[i] = j

            time.sleep(0.05)
            for stack in stacks:
                stack.serviceAllRx()

            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.05)

    def serviceStacksWithLimits(self, stacks, limits, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        Drops rx msgs in .rxes deque based on buffer size limits. Limits
        is list of rx buffer size limits for each stack in stacks
        A limit of None mean no limit on buffer size
        '''
        if limits is None:
            limits = [None, None]
        for k in range(len(stacks) - len(limits)):
            limits.append(None)  # ensure a limit per stack even if empty

        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for i, stack in enumerate(stacks):
                stack.serviceTxMsgs()
                stack.serviceTxes()

            time.sleep(0.05)
            for i, stack in enumerate(stacks):
                limit = limits[i]
                stack.serviceReceives()
                if not limit:
                    stack.serviceRxes()
                else:
                    k = 0
                    while stack.rxes and k < limit:  # process upto limit
                        stack.serviceRxOnce()
                        k += 1
                    while stack.rxes:  # flush rest
                        stack.rxes.popleft()
                stack.process()

            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.05)

    def serviceStacksWithDropsLimits(self, stacks, dropage=None, limits=None, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        Drops tx msgs in .txes deque based on drops filter which is list
        of truthy falsey values. For each element of drops if truthy then drop
        the tx at the corresponding index for each service of the txes deque.

        Drops rx msgs in .rxes deque based on buffer size limits. Limits
        is list of rx buffer size limits for each stack in stacks
        A limit of None mean no limit on buffer size
        '''
        if dropage is None:
            dropage = [[], []]
        for k in range(len(stacks) - len(dropage)):
            dropage.append([])  # ensure a drops list per stack even if empty
        indices =  []
        for stack in stacks:
            indices.append(0)

        if limits is None:
            limits = [None, None]
        for k in range(len(stacks) - len(limits)):
            limits.append(None)  # ensure a limit per stack even if empty

        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for i, stack in enumerate(stacks):
                stack.serviceTxMsgs()
                drops = dropage[i]
                j = indices[i]
                while stack.txes:
                    try:
                        drop = drops[j]
                    except IndexError:
                        drop = False

                    if drop:
                        stack.txes.popleft()  # pop and drop
                        console.concise("Stack {0}: Dropping {1}\n".format(stack.name, j))
                    else:
                        stack.serviceTxOnce() # service
                    j += 1
                indices[i] = j

            time.sleep(0.05)
            for i, stack in enumerate(stacks):
                limit = limits[i]
                stack.serviceReceives()
                if not limit:
                    stack.serviceRxes()
                else:
                    k = 0
                    while stack.rxes and k < limit:  # process upto limit
                        stack.serviceRxOnce()
                        k += 1
                    while stack.rxes:  # flush rest
                        stack.rxes.popleft()
                stack.process()

            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.05)

    def serviceStacksFlushTx(self, stacks, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        This flushes the txes deques
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAllRx()
                stack.serviceTxMsgs()
                stack.txes.clear()
                stack.serviceTxes()

            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def serviceStacksFlushRx(self, stacks, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        This flushes the rxes.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceReceives()
                stack.rxes.clear()
                stack.serviceRxes()
                stack.process()
                stack.serviceAllTx()
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def testMessageBurstZero(self):
        '''
        Test message with burst limit of 0, that is, no limit
        '''
        console.terse("{0}\n".format(self.testMessageBurstZero.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        self.message(msgs, alpha, beta, duration=5.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage Beta to Alpha *********\n")
        self.message(msgs, beta, alpha, duration=5.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageBurstOne(self):
        '''
        Test message with burst limit of 1
        '''
        console.terse("{0}\n".format(self.testMessageBurstOne.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        stacking.RoadStack.BurstSize = 1
        self.assertEqual(stacking.RoadStack.BurstSize, 1)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        self.message(msgs, alpha, beta, duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage Beta to Alpha *********\n")
        self.message(msgs, beta, alpha, duration=10.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageBurstEleven(self):
        '''
        Test message with burst limit of 11
        '''
        console.terse("{0}\n".format(self.testMessageBurstEleven.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        stacking.RoadStack.BurstSize = 11
        self.assertEqual(stacking.RoadStack.BurstSize, 11)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        self.message(msgs, alpha, beta, duration=5.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage Beta to Alpha *********\n")
        self.message(msgs, beta, alpha, duration=5.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithDrops(self):
        '''
        Test message with packets dropped
        '''
        console.terse("{0}\n".format(self.testMessageWithDrops.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                     main=True,
                                     auto=betaData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        drops = [0, 1, 1, 0, 0, 0, 0, 0, 1]
        dropage = [list(drops), list(drops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage with drops Beta to Alpha *********\n")
        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 0)
        beta.transmit(sentMsg)

        drops = [0, 1, 0, 1, 1, 0, 0, 0, 1]
        dropage = [list(drops), list(drops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=10.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithBurstDrops(self):
        '''
        Test message with packets dropped
        '''
        console.terse("{0}\n".format(self.testMessageWithBurstDrops.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)


        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        stacking.RoadStack.BurstSize = 4
        self.assertEqual(stacking.RoadStack.BurstSize, 4)

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        drops = [0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]
        dropage = [list(drops), list(drops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage with drops Beta to Alpha *********\n")
        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 0)
        beta.transmit(sentMsg)

        drops = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1]
        dropage = [list(drops), list(drops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=10.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithBufferDrops(self):
        '''
        Test message with packets dropped due to small buffers using tx drops
        '''
        console.terse("{0}\n".format(self.testMessageWithBufferDrops.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive


        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        alphaDrops = [0] * 9 + [1] * 26 + [0] * 10 + [1] * 17
        betaDrops = []
        dropage = [list(alphaDrops), list(betaDrops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithLimits(self):
        '''
        Test message with packets dropped due to small buffers using limits
        '''
        console.terse("{0}\n".format(self.testMessageWithLimits.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive


        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        limits = [9, 9]
        self.serviceStacksWithLimits([alpha, beta], limits=limits, duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithDropsLimits(self):
        '''
        Test message with packets dropped both from lost tx using drops and
        lost rx due to small buffers using limits
        '''
        console.terse("{0}\n".format(self.testMessageWithDropsLimits.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive


        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        alphaDrops = [0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]
        betaDrops = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1]
        dropage = [list(alphaDrops), list(betaDrops)]

        limits = [9, 9]
        self.serviceStacksWithDropsLimits([alpha, beta],
                                          dropage=dropage,
                                          limits=limits,
                                          duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithBurstElevenDropsLimits(self):
        '''
        Test message with packets dropped both from lost tx using drops and
        lost rx due to small buffers using limits with burst size of eleven
        '''
        console.terse("{0}\n".format(self.testMessageWithBurstElevenDropsLimits.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive


        stacking.RoadStack.BurstSize = 11
        self.assertEqual(stacking.RoadStack.BurstSize, 11)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        alphaDrops = [0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]
        betaDrops = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1]
        dropage = [list(alphaDrops), list(betaDrops)]

        limits = [9, 9]
        self.serviceStacksWithDropsLimits([alpha, beta],
                                          dropage=dropage,
                                          limits=limits,
                                          duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageWithBurstSevenDropsLimits(self):
        '''
        Test message with packets dropped both from lost tx using drops and
        lost rx due to small buffers using limits with burst size of seven
        '''
        console.terse("{0}\n".format(self.testMessageWithBurstSevenDropsLimits.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive


        stacking.RoadStack.BurstSize = 7
        self.assertEqual(stacking.RoadStack.BurstSize, 7)

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        alphaDrops = [0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1]
        betaDrops = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1]
        dropage = [list(alphaDrops), list(betaDrops)]

        limits = [9, 9]
        self.serviceStacksWithDropsLimits([alpha, beta],
                                          dropage=dropage,
                                          limits=limits,
                                          duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageDropAllFirst(self):
        '''
        Test message with all first segments dropped.
        '''
        console.terse("{0}\n".format(self.testMessageDropAllFirst.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta)  # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in xrange(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        msgs.append(sentMsg)

        console.terse("\nMessage with drops Alpha to Beta *********\n")
        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 0)
        alpha.transmit(sentMsg)

        drops = [1]*40
        dropage = [list(drops), list(drops)]
        self.serviceStacksFlushTx([alpha, beta], duration=0.01)  # 1 iteration drop all
        self.serviceStacks([alpha, beta], duration=10.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        console.terse("\nMessage with drops Beta to Alpha *********\n")
        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 0)
        beta.transmit(sentMsg)

        drops = [1]*40
        dropage = [list(drops), list(drops)]
        self.serviceStacksWithDrops([alpha, beta], dropage=dropage, duration=0.01)  # 1 iteration drop all
        self.serviceStacks([alpha, beta], duration=10.0)

        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(beta.txMsgs), 0)
        self.assertEqual(len(beta.txes), 0)
        self.assertEqual(len(alpha.rxes), 0)
        self.assertEqual(len(alpha.rxMsgs), 1)
        receivedMsg, source = alpha.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageSingleSegmentedDuplicate(self):
        '''
        Test single segmented message received twice
        '''
        console.terse("{0}\n".format(self.testMessageSingleSegmentedDuplicate.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(5):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        alpha.transmit(sentMsg)
        # Send the message and redo the message
        self.serviceStack(alpha, duration=0.5)  # transmit
        self.assertIn('redo_segment', alpha.stats)

        self.serviceStacks((beta, alpha))

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)

        # withoutfix comment out
        self.assertEqual(len(beta.rxMsgs), 1)
        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testMessageSegmentedLostAckDuplicate(self):
        '''
        Test single segmented message received twice
        '''
        console.terse("{0}\n".format(self.testMessageSegmentedLostAckDuplicate.__doc__))

        alphaData = self.createRoadData(name='alpha',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData,
                                     main=True,
                                     auto=alphaData['auto'],
                                     ha=None)

        betaData = self.createRoadData(name='beta',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData,
                                    main=True,
                                    auto=betaData['auto'],
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin *********\n")
        self.join(alpha, beta) # vacuous join fails because other not main
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow *********\n")
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nMessage Alpha to Beta *********\n")
        msgs = []
        bloat = []
        for i in range(15):  # 2 segments expected
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        sentMsg = odict(who="Green", data=bloat)
        alpha.transmit(sentMsg)
        # Messenger: send the message
        alpha.serviceAll()
        self.store.advanceStamp(0.1)
        time.sleep(0.1)
        # Messengent: receive, handle the message, send Ack, remove transaction
        beta.serviceAll()
        self.store.advanceStamp(0.1)
        time.sleep(0.1)
        # Drop Ack as if it's lost
        alpha.serviceReceives()
        self.assertEqual(len(alpha.rxes), 1)
        alpha.rxes.clear()
        # Messenger: resend last segment without AF
        self.serviceStack(alpha, duration=0.5)  # transmit
        self.assertIn('redo_segment', alpha.stats)
        # Messengent: create new transaction and request missed segments, all but the last one
        self.serviceStacks((beta, alpha))

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(alpha.txMsgs), 0)
        self.assertEqual(len(alpha.txes), 0)
        self.assertEqual(len(beta.rxes), 0)

        # without fix comment out
        self.assertEqual(len(beta.rxMsgs), 1)

        receivedMsg, source = beta.rxMsgs.popleft()
        self.assertDictEqual(sentMsg, receivedMsg)

        stacking.RoadStack.BurstSize = 0
        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()


def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    '''
    Unittest runner
    '''
    tests =  []
    names = [
                'testMessageBurstZero',
                'testMessageBurstOne',
                'testMessageBurstEleven',
                'testMessageWithDrops',
                'testMessageWithBurstDrops',
                'testMessageWithBufferDrops',
                'testMessageWithLimits',
                'testMessageWithDropsLimits',
                'testMessageWithBurstElevenDropsLimits',
                'testMessageWithBurstSevenDropsLimits',
                'testMessageDropAllFirst',
                'testMessageSingleSegmentedDuplicate',
                'testMessageSegmentedLostAckDuplicate',
            ]

    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    '''
    Unittest runner
    '''
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    #runAll() #run all unittests

    runSome()#only run some

    #runOne('testMessageWithBurstSevenDropsLimits')
