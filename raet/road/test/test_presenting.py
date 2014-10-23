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

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing
from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import estating, keeping, stacking

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

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self,
                       base,
                       name='',
                       ha=None,
                       main=None,
                       auto=raeting.autoModes.never,
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
                        kind=None, ):
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
                                   dirpath=data['dirpath'],)

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

    def message(self, main, other, mains, others, duration=2.0):
        '''
        Utility to send messages both ways
        '''
        for msg in mains:
            main.transmit(msg)
        for msg in others:
            other.transmit(msg)

        self.service(main, other, duration=duration)

    def flushReceives(self, stack):
        '''
        Flush any queued up udp packets in receive buffer
        '''
        stack.serviceReceives()
        stack.rxes.clear()

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


    def testJoinNameRoleDiffer(self):
        '''
        Test join from other where name and role are different
        '''
        console.terse("{0}\n".format(self.testJoinNameRoleDiffer.__doc__))

        mainData = self.createRoadData(name='main_stack',
                                       role='main',
                                       base=self.base,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.main, None)
        self.assertIs(other.keep.auto, raeting.autoModes.once)

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
            self.assertIs(remote.alived, None)

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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.never)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertIs(other.keep.auto, raeting.autoModes.never)
        self.assertIs(other.main, None)

        console.terse("\nJoin Main to Other *********\n")
        self.join(main, other) # vacuous join fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)
            self.assertEqual(len(stack.nameRemotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.autoModes.once
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.autoModes.once)

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
            self.assertIs(remote.alived, None)

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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.autoModes.never)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.keep.auto, raeting.autoModes.never)
        self.assertIs(other.main, None)

        console.terse("\nJoin Main to Other *********\n")
        self.join(main, other) # vacuous join fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)
            self.assertEqual(len(stack.nameRemotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.autoModes.once
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.autoModes.once)


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
            self.assertIs(remote.alived, None)

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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other_stack',
                                        role='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=True,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertNotEqual(main.local.name, main.local.role)
        self.assertNotEqual(other.local.name, other.local.role)
        self.assertIs(other.main, True)
        self.assertIs(other.keep.auto, raeting.autoModes.once)

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
            self.assertIs(remote.alived, None)

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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other', base=self.base)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=raeting.autoModes.once,
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

        console.terse("\nAlive Other to Main *********\n")
        for stack in [main, other]:
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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
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
            self.assertIs(remote.alived, None)

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))

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
            self.assertIs(remote.alived, None)

        console.terse("\nAlive Other to Main *********\n")
        for remote in [main.remotes.values()[0],
                       other.remotes.values()[0]]:
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     #uid=1,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
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

        console.terse("\nAllow Main to Other *********\n")
        # force unjoined already unallowed unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None
            stack.remotes.values()[0].allowed = None

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

        console.terse("\nAlive Other to Main *********\n")
        # force unjoined unallowed already unalived
        for stack in [main, other]:
            stack.remotes.values()[0].joined = None
            stack.remotes.values()[0].allowed = None

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
            self.assertIs(remote.alived, None)

        # Alive should complete now
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
            self.assertIs(remote.alived, None)

        # Alive should complete now
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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
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
                                     auto=raeting.autoModes.never,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.autoModes.once

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
                                     auto=raeting.autoModes.never,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.autoModes.once

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
                                     auto=raeting.autoModes.never,
                                     ha=("", raeting.RAET_TEST_PORT))

        for stack in [main, other]:
            self.assertEqual(len(stack.remotes), 0)

        self.join(main, other) # bootstrap channel fails because other not main
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)

        # now fix it so other can accept vacuous joins
        other.main = True
        other.keep.auto = raeting.autoModes.once

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
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once,)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))

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

    def testManageBothSides(self):
        '''
        Test stack manage remotes main and others
        '''
        console.terse("{0}\n".format(self.testManageBothSides.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once)
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))

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

    def testManageMainRebootCascade(self):
        '''
        Test stack manage remotes as if main were rebooted
        '''
        console.terse("{0}\n".format(self.testManageMainRebootCascade.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.autoModes.once)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))

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

    def testManageRebootCascadeBothSides(self):
        '''
        Test stack manage remotes as if main were rebooted
        '''
        console.terse("{0}\n".format(self.testManageRebootCascadeBothSides.__doc__))

        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=raeting.autoModes.once)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))

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


    def testManageRebootCascadeBothSidesAlt(self):
        '''
        Test stack manage remotes as if main were rebooted and main name
        means it loses simultaneous join name resolution
        '''
        console.terse("{0}\n".format(self.testManageRebootCascadeBothSidesAlt.__doc__))

        mainData = self.createRoadData(name='zmain',
                                       base=self.base,
                                       auto=raeting.autoModes.once)
        mainDirpath = mainData['dirpath']
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other',
                                        base=self.base,
                                        auto=raeting.autoModes.once)
        otherDirpath = otherData['dirpath']
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     main=None,
                                     auto=otherData['auto'],
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once)
        other1Dirpath = other1Data['dirpath']
        keeping.clearAllKeep(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     main=None,
                                     auto=other1Data['auto'],
                                     ha=("", 7532))


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

    #runSome()#only run some

    runOne('testJoinFromMainKindChange')
