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

    def getAutoAcceptedStacks(self):
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

    def sameAllKeep(self, remote):
        keep = {}
        keep['role'] = remote.role
        keep['verhex'] = remote.verfer.keyhex
        keep['keyhex'] = remote.pubber.keyhex
        keep['name'] = remote.name
        keep['ha'] = remote.ha
        keep['fuid'] = remote.fuid
        keep['main'] = remote.main
        keep['application'] = remote.application
        return keep

    def sameAllCheck(self, remote, keep):
        self.assertEqual(remote.role, keep['role'])
        self.assertEqual(remote.verfer.keyhex, keep['verhex'])
        self.assertEqual(remote.pubber.keyhex, keep['keyhex'])
        self.assertEqual(remote.name, keep['name'])
        self.assertEqual(remote.ha, keep['ha'])
        self.assertEqual(remote.fuid, keep['fuid'])
        self.assertEqual(remote.main, keep['main'])
        self.assertEqual(remote.application, keep['application'])

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
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=beta_remote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

        old_main = None
        new_main = True
        # Name: Old
        # Main: New
        self.assertIs(beta.main, old_main)
        beta.main = new_main
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['main'] = new_main
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewAppl(self):
        '''
        Test joinent accept vacuous join with updated application (D2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewAppl.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=beta_remote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

        old_appl = None
        new_appl = 33
        # Name: Old
        # Main: Either
        # Appl: New
        self.assertIs(beta.application, old_appl)
        beta.application = new_appl
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['application'] = new_appl
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewRha(self):
        '''
        Test joinent accept vacuous join with updated remote host address (D3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewRha.__doc__))

        old_ha = '127.0.0.5'
        new_ha = '127.0.0.1'
        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=beta_remote.nuid,
                                             ha=(old_ha, beta.local.ha[1]),
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

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
        self.assertEqual(alpha_remote.ha[0], old_ha)
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['ha'] = (new_ha, keep['ha'][1])
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewFuid(self):
        '''
        Test joinent accept vacuous join with an updated fuid (D4)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))

        old_fuid = 33
        new_fuid = beta_remote.nuid

        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=old_fuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: New: alpha_remote has uid=33 that is 'old', beta_remote has uid=2
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['fuid'] = new_fuid
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

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
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))

        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=beta_remote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

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
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['verhex'] = beta.local.signer.verhex
        keep['keyhex'] = beta.local.priver.pubhex
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

        # Keys: New
        beta.local.priver = nacling.Privateer()
        beta_remote.fuid = 0
        beta_remote.sid = 0

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
        alpha, beta = self.getAutoAcceptedStacks()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        beta_remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alpha_remote = estating.RemoteEstate(stack=alpha,
                                             fuid=beta_remote.nuid,
                                             ha=beta.local.ha,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alpha_remote)

        old_role = 'beta'
        new_role = 'beta_new'
        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: New
        self.assertIs(beta.local.role, old_role)
        beta.local.role = new_role
        # Keys: Either
        # Sameness: Not sameall
        keep = self.sameAllKeep(alpha_remote)

        # Test
        self.join(beta, alpha, deid=beta_remote.nuid)

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
        keep['role'] = new_role
        self.sameAllCheck(alpha_remote, keep)
        self.assertEqual(alpha_remote.acceptance, raeting.acceptances.accepted)

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
    names = ['testJoinBasic',
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
