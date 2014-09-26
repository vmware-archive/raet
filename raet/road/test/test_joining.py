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

    def bootstrapRemotes(self):
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
                remote.fuid == data['fuid'] and
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

    def testJoinentVacuousImmutableRejectNewMain(self):
        '''
        Test immutable joinent reject vacuous join with an updated main (A1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        self.assertIs(alphaRemote.acceptance, None)
        self.assertIs(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousImmutableRejectNewKind(self):
        '''
        Test immutable joinent reject vacuous join with an updated kind (A2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

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

        oldKind = None
        newKind = 33
        # Name: Old
        # Main: Either
        # Appl: New
        self.assertIs(beta.kind, oldKind)
        beta.kind = newKind
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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousImmutableRejectNewRha(self):
        '''
        Test immutable joinent reject vacuous join with an updated remote host address (A3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewRha.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Simulate: alpha already know beta with ha='127.0.0.5'
        #           beta connects with ha='127.0.0.1'
        oldHa = ('127.0.0.5', beta.local.ha[1])
        newHa = ('127.0.0.1', beta.local.ha[1])

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                          fuid=0, # vacuous join
                                                          sid=0, # always 0 for join
                                                          ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=oldHa,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  New: alpha remote ha is set to 127.0.0.5, new ha received from beta is 127.0.0.1
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        self.assertEqual(alphaRemote.ha, oldHa)
        self.assertEqual(beta.local.ha, newHa)
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousImmutableRejectNewFuid(self):
        '''
        Test immutable joinent reject vacuous join with an updated fuid (A4)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                          fuid=0, # vacuous join
                                                          sid=0, # always 0 for join
                                                          ha=alpha.local.ha))

        # Simulate: alpha already know beta with fuid=33
        #           beta connects with a new fuid=newFuid
        oldFuid = 33
        newFuid = betaRemote.nuid

        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=oldFuid,
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
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousImmutableRejectNewKeys(self):
        '''
        Test immutable joinent reject vacuous join with an updated keys (A5)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

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
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousImmutableRejectNewRole(self):
        '''
        Test immutable joinent reject vacuous join with an updated role (A6)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousImmutableRejectNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

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
        alpha, beta = self.bootstrapRemotes()
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
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.main, newMain)

        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewKind(self):
        '''
        Test joinent accept vacuous join with updated application kind (D2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
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

        oldKind = None
        newKind = 33
        # Name: Old
        # Main: Either
        # Appl: New
        self.assertIs(beta.kind, oldKind)
        beta.kind = newKind
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
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.kind, newKind)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewRha(self):
        '''
        Test joinent accept vacuous join with updated remote host address (D3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewRha.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Simulate: alpha already know beta with ha='127.0.0.5'
        #           beta connects with ha='127.0.0.1'
        oldHa = ('127.0.0.5', beta.local.ha[1])
        newHa = ('127.0.0.1', beta.local.ha[1])

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))
        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=betaRemote.nuid,
                                             ha=oldHa,
                                             name=beta.name,
                                             verkey=beta.local.signer.verhex,
                                             pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  New: alpha remote ha is set to 127.0.0.5, new ha received from is 127.0.0.1
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        self.assertEqual(alphaRemote.ha, oldHa)
        self.assertEqual(beta.local.ha, newHa)
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.ha, newHa)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

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
        alpha, beta = self.bootstrapRemotes()
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: Yes
        betaRemote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                           fuid=0, # vacuous join
                                                           sid=0, # always 0 for join
                                                           ha=alpha.local.ha))

        # Simulate: alpha already know beta with fuid=33
        #           beta connects with a new fuid=newFuid
        oldFuid = 33
        newFuid = betaRemote.nuid

        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                             fuid=oldFuid,
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
        # Reid: New
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
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.fuid, newFuid)
        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

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
        alpha, beta = self.bootstrapRemotes()
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
            self.assertEqual(len(stack.stats), 1)
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
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

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
        alpha, beta = self.bootstrapRemotes()
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
            self.assertEqual(len(stack.stats), 1)
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
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

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
                'testJoinentVacuousImmutableRejectNewMain',
                'testJoinentVacuousImmutableRejectNewAppl',
                'testJoinentVacuousImmutableRejectNewRha',
                'testJoinentVacuousImmutableRejectNewFuid',
                'testJoinentVacuousImmutableRejectNewKeys',
                'testJoinentVacuousImmutableRejectNewRole',
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
