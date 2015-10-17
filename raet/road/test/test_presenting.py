# -*- coding: utf-8 -*-
'''
Tests to try out keeping. Potentially ephemeral

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
        self.service(correspondent, initiator, duration=duration)

    def allow(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        initiator.allow(uid=deid, cascade=cascade)
        self.service(correspondent, initiator, duration=duration)

    def alive(self, initiator, correspondent, duid=None, duration=1.0,
                cascade=False):
        '''
        Utility method to do alive. Call from test method.
        '''
        console.terse("\nAlive Transaction **************\n")
        initiator.alive(uid=duid, cascade=cascade)
        self.service(correspondent, initiator, duration=duration)

    def message(self, msgs, initiator, correspondent, duration=2.0):
        '''
        Utility to send messages both ways
        '''
        for msg in msgs:
            initiator.transmit(msg)

        self.service(initiator, correspondent, duration=duration)

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

    def service(self, main, other, duration=1.0):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            other.serviceAll()
            main.serviceAll()
            if not (main.transactions or other.transactions):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

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

    def serviceStacksDropRx(self, stacks, duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
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

    def serviceManageStacks(self, stacks, duration=1.0, cascade=False):
        '''
        Utility method to service queues and manage presence for list of stacks.
        Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceAllRx()
                stack.manage(cascade=cascade)
                stack.serviceAllTx()
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def answerAlive(self, stack, deid=None, kind=raeting.PcktKind.nack.value, dataMod=None):
        '''
        Utility method to receive a packet in the given stack and send alive nack as a responce
        Call from test method.
        :param stack: correspondent stack that have to receive and nack a transaction
        :param deid: remote estate id in the stack
        :param kind: nack kind (nack, reject, ...)
        :rtype : None
        '''
        stack.serviceReceives()
        # process rx
        raw, sa = stack.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(stack.name, raw))
        packet = packeting.RxPacket(stack=stack, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        data = odict(hk=stack.Hk, bk=stack.Bk, fk=stack.Fk, ck=stack.Ck)
        if dataMod:
            data.update(dataMod)
        remote = stack.retrieveRemote(deid)
        alivent = transacting.Alivent(stack=stack,
                                      remote=remote,
                                      bcst=packet.data['bf'],
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        if kind == raeting.PcktKind.ack:
            alivent.alive()
        else:
            alivent.nack(kind=kind)

    def aliveBrokenInner(self, stack, uid=None, timeout=None, cascade=False):
        '''
        Initiate alive transaction
        If duid is None then create remote at ha
        '''
        remote = stack.retrieveRemote(uid=uid)
        self.assertIsNotNone(remote)
        data = odict(hk=stack.Hk, bk=stack.Bk, fk=stack.Fk, ck=stack.Ck)
        data['ck'] = -1
        aliver = transacting.Aliver(stack=stack,
                                    remote=remote,
                                    timeout=timeout,
                                    txData=data,
                                    cascade=cascade)
        aliver.alive()

    def testJoinNameRoleDiffer(self):
        '''
        Test join from other where name and role are different
        '''
        console.terse("{0}\n".format(self.testJoinNameRoleDiffer.__doc__))

        mainData = self.createRoadData(name='main_stack',
                                       role='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.main, None)
        self.assertIs(other.keep.auto, raeting.AutoMode.once.value)

        console.terse("\nJoin Other to Main *********\n")
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow Other to Main *********\n")
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        console.terse("\nAlive Other to Main *********\n")
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Main to Other *********\n")
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinFromMain(self):
        '''
        Test join,initiated by main
        '''
        console.terse("{0}\n".format(self.testJoinFromMain.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.never.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertIs(other.keep.auto, raeting.AutoMode.never.value)
        self.assertIs(other.main, None)

        console.terse("\nJoin Main to Other *********\n")
        self.join(main, other) # vacuous join fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)
            self.assertEqual(len(stack.nameRemotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.AutoMode.once.value
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.AutoMode.once.value)

        self.join(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow Main to Other *********\n")
        self.allow(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Main to other *********\n")
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Other to Main *********\n")
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)


        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinFromMainNameRoleDiffer(self):
        '''
        Test join from main where name and role are different
        '''
        console.terse("{0}\n".format(self.testJoinFromMainNameRoleDiffer.__doc__))

        mainData = self.createRoadData(name='main_stack',
                                       role='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.never.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.keep.auto, raeting.AutoMode.never.value)
        self.assertIs(other.main, None)

        console.terse("\nJoin Main to Other *********\n")
        self.join(main, other) # vacuous join fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)
            self.assertEqual(len(stack.nameRemotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.AutoMode.once.value
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.AutoMode.once.value)


        self.join(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow Main to Other *********\n")
        self.allow(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Main to other *********\n")
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Other to Main *********\n")
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinFromMainKindChange(self):
        '''
        Test allow from main where name changed from join
        This reproduces what happens if name changed after successful join
        and reboot
        so joined is persisted so allow fails
        '''
        console.terse("{0}\n".format(self.testJoinFromMainKindChange.__doc__))

        mainData = self.createRoadData(name='main_stack',
                                       role='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.AutoMode.once.value)

        console.terse("\nJoin Main to Other *********\n")
        self.join(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        # Change kind
        other.kind =  1
        self.assertNotEqual(other.kind, otherData['kind'])
        main.kind =  1
        self.assertNotEqual(main.kind, mainData['kind'])

        self.join(main, other) # fails because not same all and immutable road
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(main.nameRemotes), 0)

        self.assertEqual(len(other.remotes), 1)
        self.assertEqual(len(other.nameRemotes), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, True)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)

        other.mutable = True
        self.assertIs(other.mutable, True)
        self.join(main, other) # fails because not same all and immutable road
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        console.terse("\nAllow Main to Other *********\n")
        self.allow(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # fast alive

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Main to other *********\n")
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived

        console.terse("\nAlive Other to Main *********\n")
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)


        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliveDead(self):
        '''
        Test basic alive transaction given already joined and allowed
        '''
        console.terse("{0}\n".format(self.testAliveDead.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other', base=self.base)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=raeting.AutoMode.once.value,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.join(other, main)
        remotes = []
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            remotes.append(remote)
            self.assertIs(remote.joined, True)
            self.assertNotEqual(remote.nuid, 0)
            self.assertNotEqual(remote.fuid, 0)

        self.assertEqual(remotes[0].fuid, remotes[1].nuid)
        self.assertEqual(remotes[1].fuid, remotes[0].nuid)

        for stack in [main, other]:
            self.assertIs(stack.remotes.values()[0].allowed, None)
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Other to Main *********\n")
        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            remote.alived = None
            self.assertIs(stack.remotes.values()[0].alived, None)
        self.alive(other, main, duid=other.remotes.values()[0].uid)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Main to Other *********\n")
        for stack in [main, other]:
            stack.remotes.values()[0].alived = None
            self.assertIs(stack.remotes.values()[0].alived, None)
        self.alive(main, other, duid=main.remotes.values()[0].uid)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nDead Other from Main *********\n")
        # start alive from main to other but do not service responses from other
        # so main alive trans times out and other  appears dead to main
        for stack in [main, other]:
            self.assertIs(stack.remotes.values()[0].alived, True)
        main.alive()
        self.serviceStack(main, duration=3.0) # only service main
        self.assertEqual(len(main.transactions), 0) # timed out
        self.assertIs(main.remotes.values()[0].alived,  False)
        self.serviceStack(other, duration=3.0) # now service other side
        self.assertEqual(len(other.transactions), 0) # gets queued requests
        self.assertIs(other.remotes.values()[0].alived,  True)
        self.assertIs(main.remotes.values()[0].alived,  False)

        console.terse("\nDead Main from Other *********\n")
        # start alive from other to main but do not service responses from main
        # so other alive trans times out and main  appears dead to other
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
        self.assertIs(other.remotes.values()[0].alived, True)
        other.alive()
        self.serviceStack(other, duration=3.0) # only service other
        self.assertEqual(len(other.transactions), 0) # timed out
        self.assertIs(other.remotes.values()[0].alived, False)
        self.serviceStack(main, duration=3.0) # now service main side
        self.assertEqual(len(main.transactions), 0) # gets queued requests
        self.assertIs(main.remotes.values()[0].alived,  True)
        self.assertIs(other.remotes.values()[0].alived,  False)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliveDeadMultiple(self):
        '''
        Test alive transaction with multiple remotes given already joined and allowed
        '''
        console.terse("{0}\n".format(self.testAliveDeadMultiple.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))


        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))

        self.join(other1, main)
        for stack in [main, other1]:
            self.assertEqual(len(stack.transactions), 0)

        self.assertEqual(len(main.remotes), 2)
        self.assertEqual(len(other1.remotes), 1)

        for remote in [main.remotes.values()[1],
                        other1.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        self.allow(other1, main)
        for stack in [main, other1]:
            self.assertEqual(len(stack.transactions), 0)
        for remote in [main.remotes.values()[1],
                        other1.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Other to Main *********\n")
        for remote in [main.remotes.values()[0],
                       other.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            remote.alived = None  # force not alived
            self.assertIs(remote.alived, None)

        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
        for remote in [main.remotes.values()[0],
                       other.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Main to Other *********\n")
        for remote in [main.remotes.values()[0],
                       other.remotes.values()[0]]:
            remote.alived =  None
            self.assertIs(remote.alived, None)

        self.alive(main, other, duid=main.remotes.values()[0].uid)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
        for remote in [main.remotes.values()[0],
                       other.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Other1 to Main *********\n")
        for remote in [main.remotes.values()[1],
                       other1.remotes.values()[0]]:
            remote.alived =  None
            self.assertIs(remote.alived, None)

        self.alive(other1, main, duid=other1.remotes.values()[0].uid)
        for stack in [main, other1]:
            self.assertEqual(len(stack.transactions), 0)
        for remote in [main.remotes.values()[1],
                       other1.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Main to Other1 *********\n")
        for remote in [main.remotes.values()[1],
                       other1.remotes.values()[0]]:
            remote.alived =  None
            self.assertIs(remote.alived, None)

        self.alive(main, other1, duid=main.remotes.values()[1].uid)
        for stack in [main, other1]:
            self.assertEqual(len(stack.transactions), 0)
        for remote in [main.remotes.values()[1],
                       other1.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nDead Other to Main from Main *********\n")
        for remote in main.remotes.values():
            self.assertIs(remote.alived, True)
            main.alive(uid=remote.nuid)
        # do not service other stack so other appears dead to main
        self.serviceStacks([main, other1], duration=4.0)
        for stack in [main, other, other1]:
            self.assertEqual(len(stack.transactions), 0)
        self.assertIs(main.remotes.values()[0].alived, False)
        self.assertIs(main.remotes.values()[1].alived, True)
        self.assertIs(other.remotes.values()[0].alived, True)
        self.assertIs(other1.remotes.values()[0].alived, True)

        console.terse("\nDead Main to Other From Other *********\n")
        self.flushReceives(other) # flush packets sent by main to other
        # do not service main stack so main appears dead to other
        other.alive(uid=other.remotes.values()[0].nuid)
        self.serviceStacks([other], duration=3.0) # other
        for stack in [main, other, other1]:
            self.assertEqual(len(stack.transactions), 0)
        self.assertIs(main.remotes.values()[0].alived, False)
        self.assertIs(main.remotes.values()[1].alived, True)
        self.assertIs(other.remotes.values()[0].alived, False)
        self.assertIs(other1.remotes.values()[0].alived, True)
        self.flushReceives(main) # flush buffered packets on main

        #bring other back to life
        console.terse("\nReliven main to other from other *********\n")
        for  remote in [main.remotes.values()[0],
                        other.remotes.values()[0]]:
            self.assertIs(remote.alived, False)
        other.alive(cascade=True)
        self.serviceStacks([other, main], duration=3.0)
        for  remote in [main.remotes.values()[0],
                        other.remotes.values()[0]]:
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Dead Other 1 to Main from Main *********\n")
        for remote in main.remotes.values():
            self.assertIs(remote.alived, True)
            main.alive(uid=remote.nuid)
        # do not service other1 stack so other appears dead to main
        self.serviceStacks([main, other], duration=3.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
        self.assertIs(main.remotes.values()[0].alived, True)
        self.assertIs(main.remotes.values()[1].alived, False)
        self.assertIs(other.remotes.values()[0].alived, True)
        self.assertIs(other1.remotes.values()[0].alived, True)

        console.terse("\nDead Main to Other1 From Other1 *********\n")
        # do not service main stack so main appears dead to other1
        self.flushReceives(other1) # flush packets sent by main to other
        other1.alive(uid=other.remotes.values()[0].nuid)
        self.serviceStacks([other1], duration=3.0) # other
        for stack in [other1]:
            self.assertEqual(len(stack.transactions), 0)
        self.assertIs(main.remotes.values()[0].alived, True)
        self.assertIs(main.remotes.values()[1].alived, False)
        self.assertIs(other.remotes.values()[0].alived, True)
        self.assertIs(other1.remotes.values()[0].alived, False)
        self.flushReceives(main) # flush packets sent other1 to main


        console.terse("\nReliven main to other1 from other 1 *********\n")
        #bring main back to life from other1
        for  remote in [main.remotes.values()[1],
                        other1.remotes.values()[0]]:
            self.assertIs(remote.alived, False)
        other1.alive(cascade=True)
        self.serviceStacks([other1, main], duration=3.0)
        for  remote in [main.remotes.values()[1],
                        other1.remotes.values()[0]]:
            self.assertIs(remote.alived, True)

        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)


    def testAliveUnjoinedUnallowedBoth(self):
        '''
        Test alive transaction for other to main  given
        unjoined and/or unallowed on both main and other

        Merely set the joined, allowed, and alived status
        Do not create fresh stacks.
        '''
        console.terse("{0}\n".format(self.testAliveUnjoinedUnallowedBoth.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     #uid=1,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     #uid=1,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        console.terse("\nAllow Other to Main *********\n")
        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.allow(other, main) # will join instead since unjoined
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main) # now try to allow again
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)


        console.terse("\nAllow Main to Other *********\n")
        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None
            stack.remotes.values()[0].allowed = None
            stack.remotes.values()[0].alived = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.allow(main, other) # will join instead since unjoined
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(main, other) # now try to allow again
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Other to Main *********\n")
        # force unjoined unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None
            stack.remotes.values()[0].allowed = None
            stack.remotes.values()[0].alived = None

        # alive checks for joined and if not then joins
        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        # Alive checks for allowed and if not allows
        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        # Alive should complete now
        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            remote.alived = None
            self.assertIs(remote.alived, None)

        self.alive(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        console.terse("\nAlive Main to Other *********\n")
        # now do same from main to other
        # force unjoined unallowed unalived
        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            remote.joined = None
            remote.allowed = None
            remote.alived = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        # Alive checks for allowed and if not allows
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        # Alive should complete now
        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            remote.alived = None
            self.assertIs(remote.alived, None)

        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testCascadeBoth(self):
        '''
        Test allow and alive cascades for other to main unjoined and/or unallowed on both
        but with cascade = True so it repairs joined and allowed status and redos
        alive

        create fresh stacks on each cascade.
        '''
        console.terse("{0}\n".format(self.testCascadeBoth.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("\nJoin Other to Main Cascade *********\n")
        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(other, main, cascade=True) # now join cascade w
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True) # cascade will include alive
            self.assertIs(remote.alived, True)  # cascade will include alive

        console.terse("\Join Main to Other Cascade *********\n")
        main.server.close()
        other.server.close()
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=raeting.AutoMode.never.value,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.AutoMode.once.value

        self.join(main, other) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.join(main, other, cascade=True) # now alive cascade
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # cascade will include alive

        console.terse("\nAllow Other to Main Cascade *********\n")
        main.server.close()
        other.server.close()
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(other, main) # bootstrap channel since allow requires remote
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.allow(other, main, cascade=True) # now allow cascade so join then allow
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # cascade will include alive

        console.terse("\nAllow Main to Other Cascade *********\n")
        main.server.close()
        other.server.close()
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=raeting.AutoMode.never.value,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.AutoMode.once.value

        self.join(main, other) # bootstrap channel since allow requires remote
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.allow(main, other, cascade=True) # now allow cascade so join then allow
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # cascade will include alive

        console.terse("\nAlive Other to Main Cascade *********\n")
        main.server.close()
        other.server.close()
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.alive(other, main, cascade=True) # now alive cascade
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # cascade will include alive

        console.terse("\nAlive Main to Other Cascade *********\n")
        main.server.close()
        other.server.close()
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=raeting.AutoMode.never.value,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.AutoMode.once.value

        self.join(main, other) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
        self.alive(main, other, cascade=True) # now alive cascade
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)  # cascade will include alive

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageOneSide(self):
        '''
        Test stack manage remotes
        '''
        console.terse("{0}\n".format(self.testManageOneSide.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value,)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))

        for  stack in [other, other1]:
            self.join(stack, main)
            self.allow(stack, main)

        console.terse("\nTest manage remotes presence *********\n")
        console.terse("\nMake all alive *********\n")
        stacks = [main, other, other1]
        for remote in main.remotes.values(): #make all alive
            main.alive(uid=remote.uid)
        self.serviceStacks(stacks, duration=3.0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alived)

        main.manage()
        for stack in stacks: # no alive transactions started
            self.assertEqual(len(stack.transactions), 0)

        console.terse("\nMake all expired so send alive *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        main.manage()
        for remote in main.remotes.values(): # should start
            self.assertIs(remote.alived, True)

        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions

        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alived)


        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)

    def testManageBothSides(self):
        '''
        Test stack manage remotes main and others
        '''
        console.terse("{0}\n".format(self.testManageBothSides.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))

        for stack in [other, other1]:
            self.join(stack, main)
            self.allow(stack, main)

        console.terse("\nTest manage remotes presence both ways *********\n")
        console.terse("\nMake all alive *********\n")
        stacks = [main, other, other1]
        for remote in main.remotes.values(): #make all alive
            main.alive(uid=remote.uid)
        self.serviceStacks(stacks, duration=3.0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alived)

        for stack in stacks:
            stack.manage()

        for stack in stacks: # no alive transactions started
            self.assertEqual(len(stack.transactions), 0)

        console.terse("\nMake all expired so send alive *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        for stack in stacks:
            stack.manage()

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)


        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)

    def testManageMainRebootCascade(self):
        '''
        Test stack manage remotes as if main were rebooted
        '''
        console.terse("{0}\n".format(self.testManageMainRebootCascade.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))

        for stack in [other, other1]:
            self.join(stack, main)
            self.allow(stack, main)

        console.terse("\nTest manage remotes presence *********\n")
        console.terse("\nMake all alive *********\n")
        stacks = [main, other, other1]
        for remote in main.remotes.values(): #make all alive
            main.alive(uid=remote.uid)
        self.serviceStacks(stacks, duration=3.0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alived)

        main.manage(immediate=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        for remote in main.remotes.values():
            self.assertIs(remote.alived, True)

        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alived)

        # now close down main and reload from saved data and manage
        console.terse("\nMake all alive with cascade after main reboots *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,
                                  )
        stacks = [main, other, other1]

        for remote in main.remotes.values():
            self.assertIs(remote.joined, True) #joined status is persisted
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)

        main.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        for remote in main.remotes.values(): # should reset alive to None
            self.assertIs(remote.alived, None)
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for remote in main.remotes.values():
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertIs(remote.alived, True)

        # Now test as if others are rebooted
        console.terse("\nMake all alive with cascade after others reboot *********\n")
        other.server.close()
        other1.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath,
                                   store=self.store)
        other1 = stacking.RoadStack(dirpath=other1Dirpath,
                                    store=self.store)
        stacks = [main, other, other1]

        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        main.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        for remote in main.remotes.values():
            self.assertIs(remote.alived, True)
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)

    def testManageRebootCascadeBothSides(self):
        '''
        Test stack manage remotes as if main were rebooted
        '''
        console.terse("{0}\n".format(self.testManageRebootCascadeBothSides.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))

        for stack in (other, other1):
            self.join(stack, main)
            self.allow(stack, main)

        console.terse("\nTest manage remotes presence *********\n")
        console.terse("\nMake all alive *********\n")
        stacks = [main, other, other1]
        for remote in main.remotes.values(): #make all alive
            main.alive(uid=remote.uid)
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        main.manage(immediate=True)
        other.manage(immediate=True)
        other1.manage(immediate=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        # now test if main rebooted
        console.terse("\nMake all alive with cascade after main reboots *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        stacks = [main, other, other1]

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        main.manage(immediate=True, cascade=True)
        other.manage(cascade=True)
        other1.manage(cascade=True)
        self.assertEqual(len(main.transactions), 2)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, None)

        for stack in [other, other1]:
             for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        self.serviceManageStacks(stacks, duration=3.0, cascade=True)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # Now test as if others are rebooted but not main
        console.terse("\nMake all alive with cascade after others reboot *********\n")
        other.server.close()
        other1.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)
        stacks = [main, other, other1]

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        for stack in [other, other1]:
             for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        main.manage(cascade=True)
        other.manage(immediate=True,cascade=True)
        other1.manage(immediate=True,cascade=True)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 1)
        self.assertEqual(len(other1.transactions), 1)

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.serviceManageStacks(stacks, duration=3.0, cascade=True)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # now close down all and reload from saved data and manage
        console.terse("\nMake all alive with cascade after all reboot *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        other.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1.server.close()
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)

        stacks = [main, other, other1]

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        main.manage(immediate=True, cascade=True)
        other.manage(immediate=True, cascade=True)
        other1.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # now close down all and reload from saved data but loose joined status
        console.terse("\nMake all alive with cascade after all reboot and lose join *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        other.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1.server.close()
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)

        stacks = [main, other, other1]

        for stack in stacks:
            for remote in stack.remotes.values():
                remote.joined = None
                self.assertIs(remote.joined, None) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        main.manage(immediate=True, cascade=True)
        other.manage(immediate=True, cascade=True)
        other1.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)


    def testManageRebootCascadeBothSidesAlt(self):
        '''
        Test stack manage remotes as if main were rebooted and main name
        means it loses simultaneous join name resolution
        '''
        console.terse("{0}\n".format(self.testManageRebootCascadeBothSidesAlt.__doc__))

        mainData = self.createRoadData(name='zmain',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.AutoMode.once.value)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7533))


        for stack in (other, other1):
            self.join(stack, main, cascade=True)
            self.allow(stack, main, cascade=True)

        stacks = [main, other, other1]
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)


        console.terse("\nTest manage remotes presence *********\n")
        main.manage(immediate=True)
        other.manage(immediate=True)
        other1.manage(immediate=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        # now test if main rebooted
        console.terse("\nMake all alive with cascade after main reboots *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        stacks = [main, other, other1]

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        main.manage(immediate=True, cascade=True)
        other.manage(cascade=True)
        other1.manage(cascade=True)
        self.assertEqual(len(main.transactions), 2)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, None)

        for stack in [other, other1]:
             for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        self.serviceManageStacks(stacks, duration=3.0, cascade=True)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # Now test as if others are rebooted but not main
        console.terse("\nMake all alive with cascade after others reboot *********\n")
        other.server.close()
        other1.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)
        stacks = [main, other, other1]

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        for stack in [other, other1]:
             for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        main.manage(cascade=True)
        other.manage(immediate=True,cascade=True)
        other1.manage(immediate=True,cascade=True)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 1)
        self.assertEqual(len(other1.transactions), 1)

        for stack in [main]:
            for remote in stack.remotes.values():
                self.assertIs(remote.alived, True)

        for stack in [other, other1]:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.serviceManageStacks(stacks, duration=3.0, cascade=True)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # now close down all and reload from saved data and manage
        console.terse("\nMake all alive with cascade after all reboot *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        other.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1.server.close()
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)

        stacks = [main, other, other1]

        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        main.manage(immediate=True, cascade=True)
        other.manage(immediate=True, cascade=True)
        other1.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        # now close down all and reload from saved data but loose joined status
        console.terse("\nMake all alive with cascade after all reboot and lose join *********\n")
        main.server.close()
        main = stacking.RoadStack(store=self.store,
                                  main=True,
                                  dirpath=mainDirpath,)
        other.server.close()
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)
        other1.server.close()
        other1 = stacking.RoadStack(dirpath=other1Dirpath, store=self.store)

        stacks = [main, other, other1]

        for stack in stacks:
            for remote in stack.remotes.values():
                remote.joined = None
                self.assertIs(remote.joined, None) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        main.manage(immediate=True, cascade=True)
        other.manage(immediate=True, cascade=True)
        other1.manage(immediate=True, cascade=True)
        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions
        self.assertEqual(len(other.transactions), 1) # started 1 alive transactions
        self.assertEqual(len(other1.transactions), 1) # started 1 alive transactions
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None) #joined status is persisted
                self.assertIs(remote.allowed, None) # None on reload from file
                self.assertIs(remote.alived, None) # None on reload from file

        self.serviceManageStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for stack in stacks:
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, True)

        for stack in [main, other, other1]:
            stack.server.close()
            stack.clearAllKeeps()
        time.sleep(0.1)

    def testManageUnjoinedAllTimersExpired(self):
        '''
        Test stack manage unjoined remotes as if both presence and reap timers expired (A1)
        '''
        console.terse("{0}\n".format(self.testManageUnjoinedAllTimersExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the unjoined remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)

        # Manage
        main.clearStats()
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 join transactions
        self.assertIs(remote.joined, None)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # join is done
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # join success
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # still reaped

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageUnallowedAllTimersExpired(self):
        '''
        Test stack manage unallowed remotes as if both presence and reap timers expired (A2)
        '''
        console.terse("{0}\n".format(self.testManageUnallowedAllTimersExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the unallowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)

        # Manage
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 allow transactions
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # allow is done
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # fast alive
        self.assertFalse(remote.reaped) # unreaped by first non-join transaction

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageCascadeUnjoinedAllTimersExpired(self):
        '''
        Test stack manage cascade unjoined remotes as if both presence and reap timers expired (A3)
        '''
        console.terse("{0}\n".format(self.testManageCascadeUnjoinedAllTimersExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage cascade the unjoined remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)

        # Manage
        main.manage(cascade=True)
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 join transactions
        self.assertIs(remote.joined, None)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # join success
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # alive success
        self.assertFalse(remote.reaped) # unreaped

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageCascadeUnallowedAllTimersExpired(self):
        '''
        Test stack manage cascade unallowed remotes as if both presence and reap timers expired (A4)
        '''
        console.terse("{0}\n".format(self.testManageCascadeUnallowedAllTimersExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage cascade the unallowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)

        # Manage
        main.manage(cascade=True)
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 allow transactions
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # alive success
        self.assertFalse(remote.reaped) # unreaped

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageUnalivedAllTimersExpired(self):
        '''
        Test stack manage not alived remotes as if both presence and reap timers expired (A5)
        '''
        console.terse("{0}\n".format(self.testManageUnalivedAllTimersExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the joined and allowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)
        main.remotes.values()[0].alived = None  # reset alived

        # Manage
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 alive transactions
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertIsNone(remote.alived)  # alived status isn't changed
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived) # alive success
        self.assertFalse(remote.reaped) # unreaped

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageUnjoinedPresenceTimerExpired(self):
        '''
        Test stack manage unjoined remotes as if presence timer expired (B1)
        '''
        console.terse("{0}\n".format(self.testManageUnjoinedPresenceTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the unjoined remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)

        # Manage
        main.clearStats()
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 join transactions
        self.assertIs(remote.joined, None)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # join is done
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # join success
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageUnallowedPresenceTimerExpired(self):
        '''
        Test stack manage unallowed remotes as if presence timer expired (B2)
        '''
        console.terse("{0}\n".format(self.testManageUnallowedPresenceTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the unallowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)

        # Manage
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 allow transactions
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # allow is done
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # fast alive
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageCascadeUnjoinedPresenceTimerExpired(self):
        '''
        Test stack manage cascade unjoined remotes as if presence timer expired (B3)
        '''
        console.terse("{0}\n".format(self.testManageCascadeUnjoinedPresenceTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None

        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, None)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage cascade the unjoined remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)

        # Manage
        main.manage(cascade=True)
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 join transactions
        self.assertIs(remote.joined, None)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # join success
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # alive success
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageCascadeUnallowedPresenceTimerExpired(self):
        '''
        Test stack manage cascade unallowed remotes as if presence timer expired (B4)
        '''
        console.terse("{0}\n".format(self.testManageCascadeUnallowedPresenceTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage cascade the unallowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)

        # Manage
        main.manage(cascade=True)
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 allow transactions
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed) # allow success
        self.assertTrue(remote.alived) # alive success
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageUnalivedPresenceTimerExpired(self):
        '''
        Test stack manage not alived remotes as if presence timer expired (B5)
        '''
        console.terse("{0}\n".format(self.testManageUnalivedPresenceTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the joined and allowed remote *********\n")
        console.terse("\nMake timer expired so send alive *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(stacking.RoadStack.Period + stacking.RoadStack.Offset)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)
        main.remotes.values()[0].alived = None  # reset alived

        # Manage
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 1) # started 1 alive transactions
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0) # all transactions finished
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived) # alive success
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageReapTimerExpired(self):
        '''
        Test stack manage remotes as if reap timer expired (C1)
        '''
        console.terse("{0}\n".format(self.testManageReapTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None,
                                    period=stacking.RoadStack.Interim*2) # set presence timeout longer than reap

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage remote *********\n")
        console.terse("\nMake reap timer expired so send nothing just reap *********\n")
        # advance clock so reap timer expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertFalse(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)

        # Manage
        main.clearStats()
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 0) # started no transactions because presence timer isn't expired
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # reaped the remote because reap timer expired

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped) # still reaped since there was no transactions

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageNoTimerExpired(self):
        '''
        Test stack manage remotes as if no timer expired (C2)
        '''
        console.terse("{0}\n".format(self.testManageNoTimerExpired.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage remote *********\n")
        # ensure no timer expired
        remote = main.remotes.values()[0]
        self.assertFalse(remote.timer.expired)
        self.assertFalse(remote.reapTimer.expired)

        # Manage
        main.clearStats()
        main.manage()
        remote = main.remotes.values()[0]

        self.assertEqual(len(main.transactions), 0) # started no transactions because presence timer isn't expired
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        # Service both sides
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testManageReaped(self):
        '''
        Test stack manage reaped remotes (D1)
        '''
        console.terse("{0}\n".format(self.testManageReaped.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        self.join(other, main) # bootstrap channel
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest manage the unallowed remote *********\n")
        console.terse("\nMake all expired so send alive and reap *********\n")
        # advance clock so both remote timers expire
        self.store.advanceStamp(stacking.RoadStack.Interim)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.timer.expired)
        self.assertTrue(remote.reapTimer.expired)
        # force reap the remote
        remote.reaped = True

        # Manage
        main.manage()
        remote = main.remotes.values()[0]

        # check nothing has changed
        self.assertEqual(len(main.transactions), 0) # started no transactions
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped)

        # Service both sides
        self.serviceStacks(stacks)
        # check nothing has changed
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertTrue(remote.reaped)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventUnjoined(self):
        '''
        Test unjoined alivent receives alive (A1)
        Refresh no change alive, nack unjoined, remove
        '''
        console.terse("{0}\n".format(self.testAliventUnjoined.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive

        # force unjoin, unallow and unalive other side
        other.remotes.values()[0].joined = None
        other.remotes.values()[0].allowed = None
        other.remotes.values()[0].alived = None

        self.assertTrue(main.remotes.values()[0].joined)
        self.assertTrue(main.remotes.values()[0].allowed)
        self.assertTrue(main.remotes.values()[0].alived)  # fast alive
        self.assertIs(other.remotes.values()[0].joined, None)
        self.assertIs(other.remotes.values()[0].allowed, None)
        self.assertIs(other.remotes.values()[0].alived, None)
        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertIs(remote.reaped, None)

        console.terse("\nTest unjoined alivent *********\n")
        main.alive() # no cascade alive, unjoined so would be joined as a final result
        self.serviceStack(main, duration=0.1)
        self.serviceStack(other, duration=0.1)
        self.assertEqual(len(other.transactions), 0) # transaction was removed
        self.assertIn('unjoined_alive_attempt', other.stats) # the reason is 'unjoined'
        self.assertEqual(other.stats['unjoined_alive_attempt'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None) # not changed
        self.assertIs(remote.reaped, None)

        # alive nacked as 'unjoined', the result would be join attempt from aliver side
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.allowed, None)
            self.assertIs(remote.alived, None)
            self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventUnallowed(self):
        '''
        Test unallowed alivent receives alive (A2)
        Refresh no change alive, nack unallowed, remove
        '''
        console.terse("{0}\n".format(self.testAliventUnallowed.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive

        # force unallow and unalive other side
        other.remotes.values()[0].allowed = None
        other.remotes.values()[0].alived = None

        self.assertTrue(main.remotes.values()[0].allowed)
        self.assertTrue(main.remotes.values()[0].alived)
        self.assertIs(other.remotes.values()[0].allowed, None)
        self.assertIs(other.remotes.values()[0].alived, None)
        for stack in [main, other]:
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest unallowed alivent *********\n")
        main.alive() # no cascade alive, unallowed so would be allowed as a final result
        self.serviceStack(main, duration=0.1)
        self.serviceStack(other, duration=0.1)
        self.assertEqual(len(other.transactions), 0) # transaction was removed
        self.assertIn('unallowed_alive_attempt', other.stats) # the reason is 'unallowed'
        self.assertEqual(other.stats['unallowed_alive_attempt'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None) # not changed
        self.assertIs(remote.reaped, None)

        # alive nacked as 'unallowed', the result would be allow attempt from aliver side
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventJoinedAllowed(self):
        '''
        Test joined and allowed alivent receives alive (C1)
        Ack, refresh alive, unreap
        '''
        console.terse("{0}\n".format(self.testAliventUnallowed.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # fast alive
            self.assertIs(remote.reaped, None)

        # force unalive and reap to check it would be unreaped as result
        other.remotes.values()[0].alived = None
        other.remotes.values()[0].reaped = True

        console.terse("\nTest joined allowed alivent *********\n")
        main.alive() # no cascade alive, joined and allowed so ack, refresh alive and unreap
        self.serviceStack(main, duration=0.1)
        self.serviceStack(other,duration=0.1)
        self.assertEqual(len(other.transactions), 0) # transaction finished
        self.assertIn('alive_complete', other.stats) # the reason is 'unallowed'
        self.assertEqual(other.stats['alive_complete'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived) # alive updated
        self.assertFalse(remote.reaped) # unreaped

        # alive acked
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)
        self.assertIs(main.remotes.values()[0].reaped, None)
        self.assertFalse(other.remotes.values()[0].reaped)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliverReceiveNack(self):
        '''
        Test aliver receive nack: nack, refuse (A2) and reject (A5)
        Other cases which are ack (A1), unjoined (A3) and unallowed (A4) are covered by other tests
        '''
        console.terse("{0}\n".format(self.testAliverReceiveNack.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)
            self.assertIs(remote.reaped, None)

        console.terse("\nTest aliver receive nack *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1)
        self.answerAlive(other, kind=raeting.PcktKind.nack.value)

        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('aliver_transaction_failure', main.stats) # transaction failed
        self.assertEqual(main.stats['aliver_transaction_failure'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive refuse *********\n")
        main.alive() # no cascade alive, aliver will set alive to False and remove transaction
        self.serviceStack(main, duration=0.1)
        self.answerAlive(other, kind=raeting.PcktKind.refuse.value)

        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('aliver_transaction_failure', main.stats) # transaction failed
        self.assertEqual(main.stats['aliver_transaction_failure'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive reject *********\n")
        main.alive() # no cascade alive, aliver will set alive to False and remove transaction
        self.serviceStack(main, duration=0.1)
        self.answerAlive(other, kind=raeting.PcktKind.reject.value)

        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertIs(remote.reaped, None)
        self.assertIs(main.remotes.values()[0].alived, False) # alive is set to false
        self.assertIn('aliver_transaction_failure', main.stats) # transaction failed
        self.assertEqual(main.stats['aliver_transaction_failure'], 1)

        main.clearStats()
        console.terse("\nTest invalid (unexpected) nack kind *********\n")
        main.alive() # no cascade alive, aliver will set alive to False and remove transaction
        self.serviceStack(main, duration=0.1)
        self.answerAlive(other, kind=raeting.PcktKind.unknown.value) # unknown is invalid kind for nack. it will be set to nack
        self.serviceStack(other) # send nack
        self.serviceStack(main) # receive nack

        self.assertEqual(len(main.transactions), 1) # transaction wasn't dropped, will attempt to redo
        self.assertEqual(len(other.transactions), 0)

        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertIs(remote.reaped, None)
        self.assertTrue(main.remotes.values()[0].alived) # alived after redo
        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliverAlivePackError(self):
        '''
        Test packet.pack() throws error in aliver.alive() (coverage)
        '''
        console.terse("{0}\n".format(self.testAliverAlivePackError.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)
            self.assertIs(remote.reaped, None)

        main.clearStats()
        console.terse("\nTest aliver packet.pack error *********\n")
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        main.alive() # will fail with packing error
        raeting.UDP_MAX_PACKET_SIZE = default_size

        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived) # alived status isn't changed
        self.assertIs(remote.reaped, None)
        self.assertIn('packing_error', main.stats) # transaction failed
        self.assertEqual(main.stats['packing_error'], 1)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliverErrorParseInner(self):
        '''
        Test aliver behavior if packet.parseInner() fail (coverage)
        '''
        console.terse("{0}\n".format(self.testAliverErrorParseInner.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        self.alive(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)
            self.assertIs(remote.reaped, None)

        main.clearStats()
        console.terse("\nTest aliver receive broken ack *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1) # main send alive to other
        self.answerAlive(other, kind=raeting.PcktKind.ack.value, dataMod={'ck': -1}) # other receive and answer
        self.serviceStack(other, duration=0.1) # other send the answer to main
        self.serviceStack(main, duration=0.1) # main handle the answer

        self.assertEqual(len(main.transactions), 1) # transaction wasn't handled
        self.assertEqual(len(main.remotes), 1)
        self.assertIn('parsing_inner_error', main.stats) # transaction failed
        self.assertEqual(main.stats['parsing_inner_error'], 1)

        self.serviceStacks(stacks) # retry and finish transaction
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('alive_complete', main.stats) # transaction failed
        self.assertEqual(main.stats['alive_complete'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive broken refuse *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1) # main send alive to other
        self.answerAlive(other, kind=raeting.PcktKind.refuse.value, dataMod={'ck': -1}) # other receive and answer
        self.serviceStack(other, duration=0.1) # other send the answer to main
        self.serviceStack(main, duration=0.1) # main handle the answer

        self.assertEqual(len(main.transactions), 1) # transaction wasn't handled
        self.assertEqual(len(main.remotes), 1)
        self.assertIn('parsing_inner_error', main.stats) # transaction failed
        self.assertEqual(main.stats['parsing_inner_error'], 1)

        self.serviceStacks(stacks) # retry and finish transaction
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('alive_complete', main.stats) # transaction failed
        self.assertEqual(main.stats['alive_complete'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive broken reject *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1) # main send alive to other
        self.answerAlive(other, kind=raeting.PcktKind.reject.value, dataMod={'ck': -1}) # other receive and answer
        self.serviceStack(other, duration=0.1) # other send the answer to main
        self.serviceStack(main, duration=0.1) # main handle the answer

        self.assertEqual(len(main.transactions), 1) # transaction wasn't handled
        self.assertEqual(len(main.remotes), 1)
        self.assertIn('parsing_inner_error', main.stats) # transaction failed
        self.assertEqual(main.stats['parsing_inner_error'], 1)

        self.serviceStacks(stacks) # retry and finish transaction
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('alive_complete', main.stats) # transaction failed
        self.assertEqual(main.stats['alive_complete'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive broken unjoined *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1) # main send alive to other
        self.answerAlive(other, kind=raeting.PcktKind.unjoined.value, dataMod={'ck': -1}) # other receive and answer
        self.serviceStack(other, duration=0.1) # other send the answer to main
        self.serviceStack(main, duration=0.1) # main handle the answer

        self.assertEqual(len(main.transactions), 1) # transaction wasn't handled
        self.assertEqual(len(main.remotes), 1)
        self.assertIn('parsing_inner_error', main.stats) # transaction failed
        self.assertEqual(main.stats['parsing_inner_error'], 1)

        self.serviceStacks(stacks) # retry and finish transaction
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('alive_complete', main.stats) # transaction failed
        self.assertEqual(main.stats['alive_complete'], 1)

        main.clearStats()
        console.terse("\nTest aliver receive broken unallowed *********\n")
        main.alive() # no cascade alive, answer nack, aliver will not change alive status and remove transaction
        self.serviceStack(main, duration=0.1) # main send alive to other
        self.answerAlive(other, kind=raeting.PcktKind.unallowed.value, dataMod={'ck': -1}) # other receive and answer
        self.serviceStack(other, duration=0.1) # other send the answer to main
        self.serviceStack(main, duration=0.1) # main handle the answer

        self.assertEqual(len(main.transactions), 1) # transaction wasn't handled
        self.assertEqual(len(main.remotes), 1)
        self.assertIn('parsing_inner_error', main.stats) # transaction failed
        self.assertEqual(main.stats['parsing_inner_error'], 1)

        self.serviceStacks(stacks) # retry and finish transaction
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # alived status isn't changed
            self.assertIs(remote.reaped, None)
        self.assertIn('alive_complete', main.stats) # transaction failed
        self.assertEqual(main.stats['alive_complete'], 1)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventAliveErrorParseInner(self):
        '''
        Test for Alivent.alive() error on parse packet inner. (coverage)
        '''
        console.terse("{0}\n".format(self.testAliventAliveErrorParseInner.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        other.remotes.values()[0].alived = None  # reset alived
        other.clearStats()
        console.terse("\nTest alive with broken coat kind *********\n")
        self.aliveBrokenInner(main) # alive with broken coat kind
        self.serviceStack(main, duration=0.1)
        self.serviceStack(other,duration=0.1)
        self.assertEqual(len(other.transactions), 0) # transaction finished
        self.assertIn('parsing_inner_error', other.stats) # Error ocured
        self.assertEqual(other.stats['parsing_inner_error'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertIsNone(remote.alived)  # alived status isn't changed
        self.assertIsNone(remote.reaped)

        # redo the broken packet then drop it
        self.serviceStacks(stacks, duration=10.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertFalse(remote.alived) # dead
        self.assertIs(main.remotes.values()[0].reaped, None)
        self.assertFalse(other.remotes.values()[0].reaped)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventAliveErrorPacketPack(self):
        '''
        Test for Alivent.alive() error on packing a packet. (coverage)
        '''
        console.terse("{0}\n".format(self.testAliventAliveErrorPacketPack.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)
            self.assertIs(remote.reaped, None)

        other.remotes.values()[0].alived = None
        other.clearStats()
        console.terse("\nTest alivent alive with packet pack error *********\n")
        main.alive() # alive
        self.serviceStack(main, duration=0.1) # aliver send
        default_size = raeting.UDP_MAX_PACKET_SIZE # backup
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will fail
        self.serviceStack(other,duration=0.1) # alivent receive
        raeting.UDP_MAX_PACKET_SIZE = default_size

        self.assertEqual(len(other.transactions), 0) # transaction removed
        self.assertIn('packing_error', other.stats) # Error ocured
        self.assertEqual(other.stats['packing_error'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertIsNone(remote.alived)
        self.assertIsNone(remote.reaped)

        # redo with normal udp packet limit
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # redo
        self.assertIs(main.remotes.values()[0].reaped, None)
        self.assertFalse(other.remotes.values()[0].reaped)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventNackErrorPacketPack(self):
        '''
        Test for Alivent.nack() error on packing a packet. (coverage)
        '''
        console.terse("{0}\n".format(self.testAliventNackErrorPacketPack.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # fast alive
            self.assertIs(remote.reaped, None)

        # force unallow and unalive joinent
        other.remotes.values()[0].allowed = None
        other.remotes.values()[0].alived = None
        self.assertIsNone(other.remotes.values()[0].allowed)
        self.assertIsNone(other.remotes.values()[0].alived)

        other.clearStats()
        console.terse("\nTest alivent nack with packet pack error *********\n")
        main.alive() # alive
        self.serviceStack(main, duration=0.1) # aliver send
        default_size = raeting.UDP_MAX_PACKET_SIZE # backup
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will fail
        self.serviceStack(other,duration=0.1) # alivent receive
        raeting.UDP_MAX_PACKET_SIZE = default_size

        self.assertEqual(len(other.transactions), 0) # transaction removed
        self.assertIn('packing_error', other.stats) # Error ocured
        self.assertEqual(other.stats['packing_error'], 1)
        self.assertEqual(len(main.transactions), 1)
        self.assertEqual(len(other.remotes), 1)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIsNone(remote.allowed)
        self.assertIsNone(remote.alived)
        self.assertIsNone(remote.reaped)

        # redo with normal udp packet limit
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # fast alive
        self.assertIs(main.remotes.values()[0].reaped, None)
        self.assertFalse(other.remotes.values()[0].reaped)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventReceiveRequest(self):
        '''
        Test for Alivent.receive() (coverage)
        '''
        console.terse("{0}\n".format(self.testAliventReceiveRequest.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        other.remotes.values()[0].alived = None  # reset alived
        other.clearStats()
        console.terse("\nTest alivent receive request *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.1) # Send alive
        # receive alive on other in custom way: use transaction receive instead of stack.correspond()
        other.serviceReceives()
        # handle rx
        raw, sa = other.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(other.name, raw))
        packet = packeting.RxPacket(stack=other, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        nuid = packet.data['de']
        self.assertNotEqual(nuid, 0)
        remote = other.remotes.get(nuid, None)
        self.assertIsNotNone(remote)
        rsid = packet.data['si']
        self.assertNotEqual(rsid, 0)
        remote.rsid = rsid
        # create transaction
        data = odict(hk=other.Hk, bk=other.Bk, fk=other.Fk, ck=other.Ck)
        alivent = transacting.Alivent(stack=other,
                                      remote=remote,
                                      bcst=packet.data['bf'],
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # receive
        alivent.receive(packet)
        self.serviceStacks(stacks) # Process alive

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliventProcessTimeout(self):
        '''
        Test for Alivent.process() (coverage)
        '''
        console.terse("{0}\n".format(self.testAliventProcessTimeout.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        other.remotes.values()[0].alived = None  # reset alived
        other.clearStats()
        console.terse("\nTest alivent process alive transaction timeout *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.1) # Send alive
        # receive alive on other in custom way: use transaction receive instead of stack.correspond()
        other.serviceReceives()
        # handle rx
        raw, sa = other.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(other.name, raw))
        packet = packeting.RxPacket(stack=other, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        nuid = packet.data['de']
        self.assertNotEqual(nuid, 0)
        remote = other.remotes.get(nuid, None)
        self.assertIsNotNone(remote)
        rsid = packet.data['si']
        self.assertNotEqual(rsid, 0)
        remote.rsid = rsid
        # create transaction
        data = odict(hk=other.Hk, bk=other.Bk, fk=other.Fk, ck=other.Ck)
        alivent = transacting.Alivent(stack=other,
                                      remote=remote,
                                      bcst=packet.data['bf'],
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # timeout
        self.assertTrue(alivent.timeout > 0.0)
        self.store.advanceStamp(alivent.timeout)
        alivent.process()
        self.serviceStacks(stacks) # Process alive

        self.assertIn('alivent_transaction_failure', stack.stats)
        self.assertEqual(stack.stats['alivent_transaction_failure'], 1)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = other.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertIsNone(remote.alived)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstAliveRequestDropped(self):
        '''
        Test network dropped first alive request (redo timeout)
        '''
        console.terse("{0}\n".format(self.testFirstAliveRequestDropped.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        main.remotes.values()[0].alived = None  # reset alived
        main.clearStats()
        console.terse("\nTest aliver didn't received response, redo *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.1) # Send alive
        self.flushReceives(other)
        self.serviceStacks(stacks) # timeout, redo, alive
        self.serviceStacks(stacks) # fix race condition

        self.assertIn('redo_alive', main.stats)
        self.assertEqual(main.stats['redo_alive'], 1) # 1 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # Alive complete

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllAliveRequestsDropped(self):
        '''
        Test network dropped all alive requests (transaction timeout)
        '''
        console.terse("{0}\n".format(self.testAllAliveRequestsDropped.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        other.remotes.values()[0].alived = None  # reset alived
        main.clearStats()
        console.terse("\nTest aliver received no response, transaction timeout *********\n")
        main.alive() # alive from main to other
        self.serviceStacksDropRx(stacks, duration=3.0)  # redo timeout, packet timeout, drop

        self.assertIn('redo_alive', main.stats)
        self.assertEqual(main.stats['redo_alive'], 3) # 3 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertFalse(remote.alived)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstAliveRequestDelayed(self):
        '''
        Test network delayed response so it has been received after redo.
        '''
        console.terse("{0}\n".format(self.testFirstAliveRequestDelayed.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived
        main.clearStats()
        other.clearStats()
        console.terse("\nTest alivent received both request and redo *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.5) # Send alive and redo
        self.serviceStacks(stacks) # service delayed messages
        self.serviceStacks(stacks) # fix race condition

        self.assertIn('redo_alive', main.stats)
        self.assertEqual(main.stats['redo_alive'], 1) # 1 redo
        self.assertIn('stale_correspondent_attempt', main.stats)
        self.assertEqual(main.stats['stale_correspondent_attempt'], 1) # 1 stale attempt
        self.assertIn('stale_correspondent_nack', main.stats)
        self.assertEqual(main.stats['stale_correspondent_nack'], 1) # 1 stale nack answer
        self.assertIn('alive_complete', main.stats)
        self.assertEqual(main.stats['alive_complete'], 1) # 1 complete on main
        self.assertIn('stale_packet', other.stats)
        self.assertEqual(other.stats['stale_packet'], 1) # 1 stale nack on other
        self.assertIn('alive_complete', other.stats)
        self.assertEqual(other.stats['alive_complete'], 2) # 2 complete on other
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # Alive complete

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllAliveRequestsDelayed(self):
        '''
        Test network delayed all alive requests (aliver receive response after transaction dropped)
        '''
        console.terse("{0}\n".format(self.testAllAliveRequestsDelayed.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        main.remotes.values()[0].alived = None   # reset alived
        other.remotes.values()[0].alived = None  # reset alived
        main.clearStats()
        other.clearStats()
        console.terse("\nTest alivent received alive and redo after aliver transaction timeout *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=3.0)  # redo timeout, packet timeout, drop
        self.serviceStacks(stacks) # ack 4 alives on other
        self.serviceStacks(stacks) # stale nack 4 alives on main
        for stack in stacks:
            self.assertEqual(len(stack.txes), 0) # ensure both stacks done

        self.assertIn('redo_alive', main.stats)
        self.assertEqual(main.stats['redo_alive'], 3) # 3 redo
        self.assertIn('stale_correspondent_attempt', main.stats)
        self.assertEqual(main.stats['stale_correspondent_attempt'], 4) # 4 stale attempt
        self.assertIn('stale_correspondent_nack', main.stats)
        self.assertEqual(main.stats['stale_correspondent_nack'], 4) # 4 stale nack answer
        self.assertIn('stale_packet', other.stats)
        self.assertEqual(other.stats['stale_packet'], 4) # 4 stale nack on other
        self.assertIn('alive_complete', other.stats)
        self.assertEqual(other.stats['alive_complete'], 4) # 2 complete on other
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
        self.assertFalse(main.remotes.values()[0].alived) # main didn't received correct alive ack
        self.assertTrue(other.remotes.values()[0].alived) # other received correct alive request

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstAliveRequestDuplicated(self):
        '''
        Test network duplicated first alive request (aliver ack both, alivent stale nack second)
        '''
        console.terse("{0}\n".format(self.testFirstAliveRequestDuplicated.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived)  # fast alive
            self.assertIs(remote.reaped, None)

        main.remotes.values()[0].alived = None  # reset alived
        main.clearStats()
        console.terse("\nTest alivent received duplicated request *********\n")
        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.1) # Send alive
        self.dupReceives(other)
        self.serviceStacks(stacks) # 1 req, 2 ack, 1st accept, 2nd nack
        self.serviceStacks(stacks) # fix race condition

        self.assertIn('stale_correspondent_attempt', main.stats)
        self.assertEqual(main.stats['stale_correspondent_attempt'], 1) # 1 stale attempt (dup)
        self.assertIn('stale_correspondent_nack', main.stats)
        self.assertEqual(main.stats['stale_correspondent_nack'], 1) # 1 stale nack answer (dup)
        self.assertIn('alive_complete', main.stats)
        self.assertEqual(main.stats['alive_complete'], 1) # 1 complete on main
        self.assertIn('stale_packet', other.stats)
        self.assertEqual(other.stats['stale_packet'], 1) # 1 stale nack on other (dup)
        self.assertIn('alive_complete', other.stats)
        self.assertEqual(other.stats['alive_complete'], 2) # 2 complete on other
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # Alive complete

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testAliveAckDuplicated(self):
        '''
        Test network duplicated alive ack response (stale nack the second one)
        '''
        console.terse("{0}\n".format(self.testAliveAckDuplicated.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                    main=True,
                                    auto=mainData['auto'],
                                    ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True, # only main can reap and unreap
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        stacks = [main, other]

        console.terse("\nBootstrap channel *********\n")
        # remote on joiner side have to be joined and allowed
        self.join(other, main) # bootstrap channel
        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertIs(remote.alived, True)
            self.assertIs(remote.reaped, None)

        main.clearStats()
        other.clearStats()
        console.terse("\nTest aliver received response twice *********\n")
        for stack in stacks:
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            remote.alived = None
            self.assertIs(remote.alived,  None) #  Reset alived

        main.alive() # alive from main to other
        self.serviceStack(main, duration=0.1) # Send alive
        self.serviceStack(other, duration=0.1) # Send ack
        self.dupReceives(main) # duplicate response
        self.serviceStacks(stacks) # 1st accept, 2nd stale nack
        self.serviceStacks(stacks) # fix race condition

        self.assertIn('stale_correspondent_attempt', main.stats)
        self.assertEqual(main.stats['stale_correspondent_attempt'], 1) # 1 stale attempt (dup)
        self.assertIn('stale_correspondent_nack', main.stats)
        self.assertEqual(main.stats['stale_correspondent_nack'], 1) # 1 stale nack answer (dup)
        self.assertIn('alive_complete', main.stats)
        self.assertEqual(main.stats['alive_complete'], 1) # 1 complete on main
        self.assertIn('stale_packet', other.stats)
        self.assertEqual(other.stats['stale_packet'], 1) # 1 stale nack on other (dup)
        self.assertIn('alive_complete', other.stats)
        self.assertEqual(other.stats['alive_complete'], 1) # 1 complete on other
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)
            self.assertTrue(remote.allowed)
            self.assertTrue(remote.alived) # Alive complete

        for stack in [main, other]:
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
                'testJoinNameRoleDiffer',
                'testJoinFromMain',
                'testJoinFromMainNameRoleDiffer',
                'testJoinFromMainKindChange',
                'testAliveDead',
                'testAliveDeadMultiple',
                'testAliveUnjoinedUnallowedBoth',
                'testCascadeBoth',
                'testManageOneSide',
                'testManageBothSides',
                'testManageMainRebootCascade',
                'testManageRebootCascadeBothSides',
                'testManageRebootCascadeBothSidesAlt',
                'testManageUnjoinedAllTimersExpired',
                'testManageUnallowedAllTimersExpired',
                'testManageCascadeUnjoinedAllTimersExpired',
                'testManageCascadeUnallowedAllTimersExpired',
                'testManageUnalivedAllTimersExpired',
                'testManageUnjoinedPresenceTimerExpired',
                'testManageUnallowedPresenceTimerExpired',
                'testManageCascadeUnjoinedPresenceTimerExpired',
                'testManageCascadeUnallowedPresenceTimerExpired',
                'testManageUnalivedPresenceTimerExpired',
                'testManageReapTimerExpired',
                'testManageNoTimerExpired',
                'testManageReaped',
                'testAliventUnjoined',
                'testAliventUnallowed',
                'testAliventJoinedAllowed',
                'testAliverReceiveNack',
                'testAliverAlivePackError',
                'testAliverErrorParseInner',
                'testAliventAliveErrorParseInner',
                'testAliventAliveErrorPacketPack',
                'testAliventNackErrorPacketPack',
                'testAliventReceiveRequest',
                'testAliventProcessTimeout',
                'testFirstAliveRequestDropped',
                'testAllAliveRequestsDropped',
                'testFirstAliveRequestDelayed',
                'testAllAliveRequestsDelayed',
                'testFirstAliveRequestDuplicated',
                'testAliveAckDuplicated',

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

    runAll() #run all unittests

    #runSome()#only run some

    #runOne('testAliveAckDuplicated')
