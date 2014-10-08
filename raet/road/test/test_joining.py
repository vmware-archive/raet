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
import sys
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
    console.reinit(verbosity=console.Wordage.verbose)

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

    def bootstrapRemotes(self, autoMode = raeting.autoModes.once):
        alphaData = self.createRoadData(base=self.base,
                                        name='alpha',
                                        ha=("", raeting.RAET_PORT),
                                        main=True,
                                        auto=autoMode)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=None,
                                       auto=autoMode)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, autoMode)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, autoMode)
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

    def testJoinentVacuousRejectedRejectNewKeys(self):
        '''
        Test joinent rejects vacuous join request with new keys from already rejected estate (B1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
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

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

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

        # Join with new keys
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, don't clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertIn('joinent_transaction_failure', alpha.stats.keys())
        self.assertIn('joiner_transaction_failure', beta.stats.keys())

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects vacuous join request with new role from already rejected estate (B2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
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

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

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

        # Join with a new role
        self.join(beta, alpha, deid=betaRemote.nuid)

        alpha.keep.rejectRemote(alphaRemote)

        # Action: Reject, don't clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joinent rejects vacuous join request with same role and keys but not sameall (C1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
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

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        # Name: Old
        # Main: Either
        self.assertIs(beta.main, None)
        beta.main = True
        # Appl: Either
        # RHA:  Either
        # Nuid: Computed
        # Fuid: Either
        # Leid: 0
        # Reid: Either
        # Role: Old
        # Keys: Old
        # Sameness: sameRoleKeys, not sameAll

        # Join with new main
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, clear remote data, don't touch role data
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.stats), 0)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)

        # Assert remote is cleared
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role/keys aren't touched
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectSameAll(self):
        '''
        Test joinent rejects vacuous join request with same all from already rejected estate (C2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
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

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        # Name: Old
        # Main: Old
        # Appl: Old
        # RHA:  Old
        # Nuid: Computed
        # Fuid: Old
        # Leid: 0
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: sameAll

        # Join with a new role
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, clear remote data, don't touch role data
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.stats), 0)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)

        # Assert remote is cleared
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role/keys aren't touched
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousEphemeralRejectedRejectSameall(self):
        '''
        Test joinent rejects vacuous ephemeral join from already rejected estate (C3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousEphemeralRejectedRejectSameall.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)

        self.join(beta, alpha)

        # Status: Rejected
        alpha.keep.rejectRemote(alpha.remotes.values()[0])
        self.serviceStacks([alpha, beta], duration=3.0)

        # Mutable: Yes
        alpha.mutable = True

        # Name: Body
        # Main: Body
        # Kind: Body
        # RHA:  Header
        # Nuid: Computed
        # Fuid: Header
        # Leid: 0
        # Reid: Header
        # Role: Body
        # Keys: Body
        # Sameness: sameAll

        alpha.clearStats()
        beta.clearStats()
        # Join with main = True
        self.join(beta, alpha)

        # Action: Reject, clear if Added
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 0)
            self.assertEqual(len(stack.nameRemotes), 0)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('joinent_transaction_failure', alpha.stats.keys())
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats.keys())
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote is cleared
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role/keys aren't touched
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)
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
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptSameAll(self):
        '''
        Test joinent accept vacuous non-ephemeral join with same all values (E1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptSameAll.__doc__))

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
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Computed
        # Fuid: Old
        # Leid: 0
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, No Change
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
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        self.assertEqual(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(betaRemote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousEphemeralAcceptSameall(self):
        '''
        Test joinent accept vacuous ephemeral join from already accepted estate with same all (E2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousEphemeralAcceptSameall.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()

        # Mutable: Yes
        alpha.mutable = True

        # Name: Body
        # Main: Body
        # Kind: Body
        # RHA:  Header
        # Nuid: Computed
        # Fuid: Header
        # Leid: 0
        # Reid: Header
        # Role: Body
        # Keys: Body
        # Sameness: sameAll

        # Join
        self.join(beta, alpha)

        # Action: Accept, Add, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats.keys())
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats.keys())
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alpha.remotes.values()[0], remoteData), True)
        # Check role/keys dumped
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewMain(self):
        '''
        Test joinent pend and dump vacuous join with an updated main from pending remote (F1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewMain.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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

        # Join with new main
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(alphaRemote.main, newMain)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewKind(self):
        '''
        Test mutable joinent pend vacuous join with an updated kind (F2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewKind.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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

        # Join with new kind
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.kind, newKind)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewRha(self):
        '''
        Test mutable joinent pend vacuous join with an updated remote host address (F3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewRha.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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

        # Join with updated Ha
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewFuid(self):
        '''
        Test mutable joinent pend vacuous join with an updated fuid (F4)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewFuid.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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
        # Nuid: Comuted
        # Fuid: New: alphaRemote has uid=33 that is 'old', betaRemote has uid=2
        # Leid: 0
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewKeys(self):
        '''
        Test mutable joinent pend vacuous join with an updated keys (F5)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewKeys.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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
        # Sameness: Not sameall, Not same role/keys
        keep = self.copyData(alphaRemote)

        # Join with updated keys
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewRole(self):
        '''
        Test mutable joinent pend vacuous join with an updated role (F6)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewRole.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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

        # Join with updated role
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendSameAll(self):
        '''
        Test joinent pend vacuous join with same all from pending remote (G1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendSameAll.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
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
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Computed
        # Fuid: Old
        # Leid: 0
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(alphaRemote)

        # Join
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousEphemeralPendingPendSameAll(self):
        '''
        Test joinent pend vacuous ephemeral join with same all from pending remote (G2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousEphemeralPendingPendSameAll.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never

        # Mutable: Yes
        alpha.mutable = True

        # Name: Body
        # Main: Body
        # Kind: Body
        # RHA:  Header
        # Nuid: Computed
        # Fuid: Header
        # Leid: 0
        # Reid: Header
        # Role: Body
        # Keys: Body
        # Sameness: SameAll

        # Join
        self.join(beta, alpha)

        # Action: Pend, Add, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.remotes.values()[0].acceptance, raeting.acceptances.pending)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Accept the transaction
        alphaRemote = alpha.remotes.values()[0]
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousImmutableRejectNewName(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated name (H1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: New
        beta.name = 'beta_new'
        # Main: Old
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

        # Action: Reject
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

    def testJoinentNonVacuousImmutableRejectNewMain(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated main (H2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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

        # Action: Reject
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

    def testJoinentNonVacuousImmutableRejectNewKind(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated kind (H3)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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

    def testJoinentNonVacuousImmutableRejectNewRha(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated remote host address (H4)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewRha.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Simulate: alpha already know beta with ha='127.0.0.5'
        #           beta connects with ha='127.0.0.1'
        oldHa = ('127.0.0.5', beta.local.ha[1])
        newHa = ('127.0.0.1', beta.local.ha[1])

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=oldHa,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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

    def testJoinentNonVacuousImmutableRejectNewFuid(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated fuid (H5)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)

        # Simulate: alpha already know beta with fuid=33
        #           beta connects with a new fuid=newFuid
        oldFuid = 33
        newFuid = betaRemote.nuid

        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=oldFuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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

    def testJoinentNonVacuousImmutableRejectNewKeys(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated keys (H6)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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
        # Assert alphaREmote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        self.assertEqual(alphaRemote.acceptance, None)
        self.assertEqual(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousImmutableRejectNewRole(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated role (H7)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapRemotes()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

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

    def testJoinentNonVacuousRejectedRejectNewKeys(self):
        '''
        Test joinent rejects non-vacuous join request with new keys from already rejected estate (I1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)

        # Ephemeral: No Name (the name is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        # Name: Old
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        beta.local.signer = nacling.Signer()
        beta.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Join with new keys
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, don't clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertIn('joinent_transaction_failure', alpha.stats.keys())
        self.assertIn('joiner_transaction_failure', beta.stats.keys())

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects non-vacuous join request with new role from already rejected estate (I2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        oldRole = 'beta'
        newRole = 'beta_new'
        # Name: Old
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        self.assertIs(beta.local.role, oldRole)
        beta.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Join with a new role
        self.join(beta, alpha, deid=betaRemote.nuid)

        alpha.keep.rejectRemote(alphaRemote)

        # Action: Reject, don't clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectSameAll(self):
        '''
        Test joinent rejects non-vacuous join request with same all from already rejected estate (J1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
        # Mutable: Either
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Old
        # Leid: Old
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: SameAll

        # Join with same all
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.stats), 0)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)

        # Assert remote is cleared
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role/keys aren't touched
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joinent rejects non-vacuous join request with same role/keys from already rejected estate (J2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapRemotes(autoMode=raeting.autoModes.never)
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        alpha.keep.rejectRemote(alphaRemote)

        # Name: Either
        # Main: Either
        self.assertIs(beta.main, None)
        beta.main = True
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: Old
        # Sameness: Same Role/Keys

        # Join with same role/keys
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, clear remote data, don't touch role data
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.stats), 0)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)

        # Assert remote is cleared
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role/keys aren't touched
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewName(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated name (K1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True
        # Name: New
        oldName = beta.name
        newName = '{0}_new'.format(oldName)
        beta.name = newName
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.name, newName)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        remoteData['ha'] = tuple(remoteData['ha'])
        # Assert updated alphaRemote is dumped
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewMain(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated main (K2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True
        oldMain = None
        newMain = True
        # Name: Either
        # Main: New
        self.assertIs(beta.main, oldMain)
        beta.main = newMain
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dumpt
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(alphaRemote.main, newMain)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewKind(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated kind (K3)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True

        oldKind = beta.kind
        newKind = oldKind + 10
        # Name: Either
        # Main: Either
        # Appl: New
        beta.kind = newKind
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(alphaRemote.kind, newKind)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewRha(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated remote host address (K4)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewRha.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True

        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  New
        oldHa = beta.local.ha
        newHa = ('127.0.0.5', beta.local.ha[1])
        self.assertNotEqual(oldHa, newHa)
        # update beta HA
        beta.server.close()
        beta.ha = newHa
        beta.local.ha = newHa
        # recreate beta server socket
        beta.server = beta.serverFromLocal()
        reopenResult = beta.server.reopen()
        self.assertIs(reopenResult, True)
        self.assertEqual(beta.server.ha, newHa)
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewFuid(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated fuid (K5)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True
        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: New
        oldFuid = betaRemote.nuid
        newFuid = oldFuid + 10
        betaRemote.nuid = newFuid
        beta.remotes[newFuid] = beta.remotes[oldFuid]
        del beta.remotes[oldFuid]
        # Leid: Old
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewKeys(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated keys (K6)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mode: Always
        alpha.keep.auto = raeting.autoModes.always
        # Mutable: Yes
        alpha.mutable = True
        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        beta.local.signer = nacling.Signer()
        beta.local.priver = nacling.Privateer()
        # Sameness: Not SameAll, Not Same Role/Keys
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptNewRole(self):
        '''
        Test mutable joinent accept non-vacuous join with an updated role (K7)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True
        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        oldRole = 'beta'
        newRole = 'beta_new'
        self.assertIs(beta.local.role, oldRole)
        beta.local.role = newRole
        # Keys: Either
        # Sameness: Not SameAll, Not Same Role/Keys
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptSameAll(self):
        '''
        Test joinent accept non-vacuous same all join (L1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Yes
        alpha.mutable = True
        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Old
        # Leid: Old
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, No change
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.stats), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote isn't modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewName(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated name (M1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewName.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: New
        oldName = beta.name
        newName = '{0}_new'.format(oldName)
        beta.name = newName
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.name, newName)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewMain(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated main (M2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewMain.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: New
        oldMain = None
        newMain = True
        self.assertIs(beta.main, oldMain)
        beta.main = newMain
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.main, newMain)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewKind(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated kind (M3)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewKind.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Appl: New
        oldKind = beta.kind
        newKind = 33
        self.assertNotEqual(oldKind, newKind)
        beta.kind = newKind
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.kind, newKind)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewRha(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated remote host address (M4)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewRha.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Simulate: alpha already know beta with ha='127.0.0.5'
        #           beta connects with ha='127.0.0.1'
        oldHa = ('127.0.0.5', beta.local.ha[1])
        newHa = ('127.0.0.1', beta.local.ha[1])

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=oldHa,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  New: alpha remote ha is set to 127.0.0.5, new ha received from beta is 127.0.0.1
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        self.assertEqual(alphaRemote.ha, oldHa)
        self.assertEqual(beta.local.ha, newHa)
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewFuid(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated fuid (M5)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewFuid.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)

        # Simulate: alpha already know beta with fuid=33
        #           beta connects with a new fuid=newFuid
        oldFuid = 33
        newFuid = betaRemote.nuid

        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=oldFuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: New: alphaRemote has uid=33 that is 'old', betaRemote has uid=2
        # Leid: Old
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), True)
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewKeys(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated keys (M6)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewKeys.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        beta.local.signer = nacling.Signer()
        beta.local.priver = nacling.Privateer()
        # Sameness: Not sameall, Not same role/keys
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewRole(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated role (M7)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewRole.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        oldRole = 'beta'
        newRole = 'beta_new'
        # Name: Either
        # Main: Either
        # Appl: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        self.assertIs(beta.local.role, oldRole)
        beta.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameAll(alphaRemote, keep), False)
        self.assertIs(self.sameRoleKeys(alphaRemote, keep), False)
        self.assertEqual(alphaRemote.role, newRole)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendSameAll(self):
        '''
        Test joinent pend non-vacuous same all join (N1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendSameAll.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapRemotes()
        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Either
        alpha.mutable = True

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha)
        # Ephemeral: No Nuid (the Nuid is known)
        alphaRemote = estating.RemoteEstate(stack=alpha,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Old
        # Main: Old
        # Appl: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Old
        # Leid: Old
        # Reid: Old
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(alphaRemote)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, No change
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.stats), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertIs(self.sameAll(alphaRemote, keep), True)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        # Allow beta to modify it's remote estate: set proper name and role for alpha remote estate on accept
        beta.mutable = True
        # Accept the transaction
        alpha.keep.acceptRemote(alphaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, True)
        self.assertIs(beta.mutable, True)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertIn('join_initiate_complete', beta.stats)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertIs(self.sameAll(alphaRemote, remoteData), True)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
                'testJoinentVacuousImmutableRejectNewKind',
                'testJoinentVacuousImmutableRejectNewRha',
                'testJoinentVacuousImmutableRejectNewFuid',
                'testJoinentVacuousImmutableRejectNewKeys',
                'testJoinentVacuousImmutableRejectNewRole',
                'testJoinentVacuousRejectedRejectNewKeys',
                'testJoinentVacuousRejectedRejectNewRole',
                'testJoinentVacuousRejectedRejectSameRoleKeys',
                'testJoinentVacuousRejectedRejectSameAll',
                'testJoinentVacuousEphemeralRejectedRejectSameall',
                'testJoinentVacuousAcceptNewMain',
                'testJoinentVacuousAcceptNewKind',
                'testJoinentVacuousAcceptNewRha',
                'testJoinentVacuousAcceptNewFuid',
                'testJoinentVacuousAcceptNewKeys',
                'testJoinentVacuousAcceptNewRole',
                'testJoinentVacuousAcceptSameAll',
                'testJoinentVacuousEphemeralAcceptSameall',
                'testJoinentVacuousPendingPendNewMain',
                'testJoinentVacuousPendingPendNewKind',
                'testJoinentVacuousPendingPendNewRha',
                'testJoinentVacuousPendingPendNewFuid',
                'testJoinentVacuousPendingPendNewKeys',
                'testJoinentVacuousPendingPendNewRole',
                'testJoinentVacuousPendingPendSameAll',
                'testJoinentVacuousEphemeralPendingPendSameAll',
                'testJoinentNonVacuousImmutableRejectNewName',
                'testJoinentNonVacuousImmutableRejectNewMain',
                'testJoinentNonVacuousImmutableRejectNewKind',
                'testJoinentNonVacuousImmutableRejectNewRha',
                'testJoinentNonVacuousImmutableRejectNewFuid',
                'testJoinentNonVacuousImmutableRejectNewKeys',
                'testJoinentNonVacuousImmutableRejectNewRole',
                'testJoinentNonVacuousRejectedRejectNewKeys',
                'testJoinentNonVacuousRejectedRejectNewRole',
                'testJoinentNonVacuousRejectedRejectSameAll',
                'testJoinentNonVacuousRejectedRejectSameRoleKeys',
                'testJoinentNonVacuousAcceptNewName',
                'testJoinentNonVacuousAcceptNewMain',
                'testJoinentNonVacuousAcceptNewKind',
                'testJoinentNonVacuousAcceptNewRha',
                'testJoinentNonVacuousAcceptNewFuid',
                'testJoinentNonVacuousAcceptNewKeys',
                'testJoinentNonVacuousAcceptNewRole',
                'testJoinentNonVacuousAcceptSameAll',
                'testJoinentNonVacuousPendingPendNewName',
                'testJoinentNonVacuousPendingPendNewMain',
                'testJoinentNonVacuousPendingPendNewKind',
                'testJoinentNonVacuousPendingPendNewRha',
                'testJoinentNonVacuousPendingPendNewFuid',
                'testJoinentNonVacuousPendingPendNewKeys',
                'testJoinentNonVacuousPendingPendNewRole',
                'testJoinentNonVacuousPendingPendSameAll',
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
