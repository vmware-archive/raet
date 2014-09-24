# -*- coding: utf-8 -*-
'''
Tests for the join transaction

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


def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self,
                       base,
                       name='',
                       ha=None,
                       main=None,
                       auto=raeting.autoModes.never):
        '''
        name is local estate name (which is stack name property)
        base is the base directory for the keep files
        auto is the auto accept status mode ()
        Creates odict and populates with data to setup road stack

        '''
        data = odict()
        data['name'] = name
        data['ha'] = ha
        data['main'] =  main
        data['auto'] = auto
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
                        auto=None,):
        '''
        Creates stack and local estate from data with
        and overrides with parameters

        returns stack

        '''
        stack = stacking.RoadStack(store=self.store,
                                   name=data['name'],
                                   uid=uid,
                                   ha=ha or data['ha'],
                                   sigkey=data['sighex'],
                                   prikey=data['prihex'],
                                   auto=auto or data['auto'],
                                   main=main or data['main'],
                                   dirpath=data['dirpath'],)

        return stack

    def join(self, initiator, correspondent, deid=None, duration=1.0,
                cascade=False, renewal=False):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        if not initiator.remotes:
            remote =  initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=correspondent.local.ha))
            deid = remote.uid

        initiator.join(uid=deid, cascade=cascade, renewal=renewal)
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

    def flushReceives(self, stack):
        '''
        Flush any queued up udp packets in receive buffer
        '''
        stack.serviceReceives()
        while stack.rxes:
            stack.rxes.popleft()

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
            self.store.advanceStamp(0.05)
            time.sleep(0.05)

    def getAcceptedStacks(self):
        alphaData = self.createRoadData(base=self.base,
                                       name='alpha',
                                       ha=("", raeting.RAET_PORT),
                                       main=True,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                        name='beta',
                                        ha=("", raeting.RAET_TEST_PORT),
                                        main=None,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin from Beta to Alpha *********\n")

        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(beta.remotes), 0)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, None)

        self.join(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, None)

        return alpha, beta

    def bootstrapJoinedRemotes(self):
        alphaData = self.createRoadData(base=self.base,
                                        name='alpha',
                                        ha=("", raeting.RAET_PORT),
                                        main=True,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=None,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin from Beta to Alpha *********\n")

        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(beta.remotes), 0)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, None)

        return alpha, beta

    def copyData(self, remote):
        keep = {}
        keep['role'] = remote.role
        keep['verhex'] = remote.verfer.keyhex
        keep['pubhex'] = remote.pubber.keyhex
        keep['name'] = remote.name
        keep['ha'] = remote.ha
        keep['fuid'] = remote.fuid
        keep['main'] = remote.main
        keep['kind'] = remote.kind
        return keep

    def sameRoleKeys(self, remote, data):
        '''
        Returns True if role and keys match, False otherwise
        '''
        return (remote.role ==  data['role'] and
                remote.verfer.keyhex == data['verhex'] and
                remote.pubber.keyhex == data['pubhex'])

    def sameAll(self, remote, data):
        return (self.sameRoleKeys(remote, data) and
                remote.name == data['name'] and
                remote.ha == data['ha'] and
                remote.main == data['main'] and
                remote.kind == data['kind'])

    def testJoinBasic(self):
        '''
        Test join
        '''
        console.terse("{0}\n".format(self.testJoinBasic.__doc__))

        alphaData = self.createRoadData(base=self.base,
                                        name='alpha',
                                        ha=("", raeting.RAET_PORT),
                                        main=True,
                                        auto=raeting.autoModes.once)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=None,
                                       auto=raeting.autoModes.once)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin from Beta to Alpha *********\n")
        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, raeting.autoModes.once)
        self.assertEqual(len(beta.remotes), 0)
        self.join(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        console.terse("\nAllow Beta to Alpha *********\n")
        self.allow(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, True)
                self.assertIs(remote.alived, None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewMain(self):
        '''
        Test joinent accept vacuous join with an updated main (D1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        oldMain = None
        newMain = True
        # Name: Old
        # Main: New
        self.assertIs(beta.main, oldMain)
        beta.main = newMain
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        #keep['main'] = new_main  # why?
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.main, newMain)

        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewAppl(self):
        '''
        Test joinent accept vacuous join with updated application kind (D2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewAppl.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        oldAppl = None
        newAppl = 33
        # Name: Old
        # Main: Either
        # Appl: New
        self.assertIs(beta.kind, oldAppl)
        beta.kind = newAppl
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.kind, newAppl)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewRha(self):
        '''
        Test joinent accept vacuous join with updated remote host address (D3)

        This test is not right
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewRha.__doc__))


        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        newHa = ('127.0.0.5', beta.local.ha[1])
        oldHa = ('127.0.0.1', beta.local.ha[1])

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=newHa,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  New: alpha remote ha is set to 127.0.0.5, beta actual ha is 127.0.0.1
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        self.assertEqual(alphaRemote.ha, newHa)
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.ha, oldHa)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewFuid(self):
        '''
        Test joinent accept vacuous join with an updated fuid (D4)

        This test is not right.
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))

        newFuid = 33
        oldFuid = betaRemote.nuid

        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=newFuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: New: alphaRemote has uid=33 that is 'old', betaRemote has uid=2
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), True) # this test is backwards
        self.assertEqual(alphaRemote.fuid, oldFuid)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewKeys(self):
        '''
        Test joinent accept vacuous join with an updated keys (D5)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))

        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Old
        # Keys: New
        beta.local.signer = nacling.Signer()
        beta.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

        # Keys: New
        beta.local.priver = nacling.Privateer()
        betaRemote.fuid = 0
        betaRemote.sid = 0

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewRole(self):
        '''
        Test joinent accept vacuous join with an updated role (D6)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        oldRole = 'beta'
        newRole = 'beta_new'
        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: New
        self.assertIs(beta.local.role, oldRole)
        beta.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)

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
                'testJoinBasic',
                'testJoinentVacuousAcceptNewMain',
                'testJoinentVacuousAcceptNewAppl',
                'testJoinentVacuousAcceptNewRha',
                'testJoinentVacuousAcceptNewFuid',
                'testJoinentVacuousAcceptNewKeys',
                'testJoinentVacuousAcceptNewRole',
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

    #runOne('testJoinFromMain')
