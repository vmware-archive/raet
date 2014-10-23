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
from raet.road import estating, keeping, stacking, packeting

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
                       sigkey=None,
                       prikey=None,
                       kind=None,
                       mutable=None, ):
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
        data['mutable'] = mutable
        data['dirpath'] = os.path.join(base, 'road', 'keep', name)
        signer = nacling.Signer(sigkey)
        data['sighex'] = signer.keyhex
        data['verhex'] = signer.verhex
        privateer = nacling.Privateer(prikey)
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
                        mutable=None, ):
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
                                   mutable=mutable if mutable is not None else data['mutable'],
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
        stack.rxes.clear()

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

    def bootstrapJoinedRemotes(self, autoMode=raeting.autoModes.once):
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

        console.terse("\nJoin from Beta to Alpha *********\n")

        self.assertTrue(alpha.main)
        self.assertIs(alpha.keep.auto, autoMode)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, autoMode)
        self.assertEqual(len(beta.remotes), 0)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, None)

        self.join(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        return alpha, beta

    def bootstrapStacks(self, autoMode = raeting.autoModes.once):
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

        self.assertTrue(alpha.main)
        self.assertIs(alpha.keep.auto, autoMode)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, autoMode)
        self.assertEqual(len(beta.remotes), 0)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.mutable, None)

        return alpha, beta

    def bootstrapStack(self,
                       name='',
                       ha=None,
                       main=None,
                       auto=raeting.autoModes.never,
                       role=None,
                       sigkey=None,
                       prikey=None,
                       kind=None,
                       mutable=None, ):

        data = self.createRoadData(base=self.base,
                                   name=name,
                                   ha=ha,
                                   main=main,
                                   auto=auto,
                                   role=role,
                                   sigkey=sigkey,
                                   prikey=prikey,
                                   kind=kind,
                                   mutable=mutable)
        keeping.clearAllKeep(data['dirpath'])
        stack = self.createRoadStack(data=data)

        self.assertIs(stack.main, main)
        self.assertIs(data['main'], main)
        self.assertIs(stack.keep.auto, auto)
        self.assertIs(data['auto'], auto)
        self.assertIs(stack.kind, kind)
        self.assertIs(data['kind'], kind)
        self.assertIs(stack.mutable, mutable)
        self.assertIs(data['mutable'], mutable)

        self.assertEqual(len(stack.remotes), 0)

        return (stack, data)


    def copyData(self, remote, fuid=None):
        keep = {}
        keep['role'] = remote.role
        keep['verhex'] = remote.verfer.keyhex
        keep['pubhex'] = remote.pubber.keyhex
        keep['name'] = remote.name
        keep['ha'] = remote.ha
        keep['fuid'] = fuid if fuid is not None else remote.fuid
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
        self.assertTrue(alpha.main)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        console.terse("\nAllow Beta to Alpha *********\n")
        self.allow(beta, alpha)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertTrue(remote.allowed)
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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIs(alphaRemote.acceptance, None)
        self.assertIs(betaRemote.acceptance, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: New
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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Simulate: alpha already know beta with ha=('127.0.0.1', 7532)
        #           beta connects with ha=('127.0.0.1', 7531)
        oldHa = (beta.local.ha[0], 7532)
        newHa = (beta.local.ha[0], beta.local.ha[1])

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
        # RHA:  New: alpha remote ha is set to (127.0.0.1, 7532)
        #             new ha received from beta is (127.0.0.1, 753
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
        self.join(beta, alpha, deid=betaRemote.nuid, duration=2.0)

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert role/keys aren't touched
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert role/keys aren't touched
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert role/keys aren't touched
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert role/keys aren't touched
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectNewKeys(self):
        '''
        Test joinent rejects vacuous join request with new keys from already rejected estate (B1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once

        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Kind: Either
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
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote isn't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role dump isn't changed
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects vacuous join request with new role from already rejected estate (B2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never

        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Kind: Either
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

        ## Join with a new role
        #self.join(beta, alpha, deid=betaRemote.nuid)

        #alpha.keep.rejectRemote(alphaRemote)

        ## Action: Reject, don't clear
        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 1)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertTrue(alpha.mutable)
        #self.assertIs(beta.mutable, None)
        #self.assertFalse(self.sameAll(alphaRemote, keep))
        #self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        #self.assertEqual(alphaRemote.role, newRole)
        #self.assertIn('joinent_transaction_failure', alpha.stats)
        #self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        #self.assertIn('joiner_transaction_failure', beta.stats)
        #self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        ## Check remote dump
        #remoteData = alpha.keep.loadRemoteData(beta.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = alpha.keep.loadRemoteRoleData(oldRole)
        #self.assertEqual(roleData['role'], oldRole)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        #self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)
        #roleData = alpha.keep.loadRemoteRoleData(newRole)
        #self.assertEqual(roleData['role'], beta.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        #self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joinent rejects vacuous join request with same role and keys but not sameall (C1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Kind: Either
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
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(alpha.mutable)
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
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Kind: Old
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
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(alpha.mutable)
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
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)

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
        self.assertTrue(alpha.mutable)
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.main, newMain)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: New
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
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.kind, newKind)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()
        # Mutable: Yes
        alpha.mutable = True


        # Simulate: alpha already know beta with ha=('127.0.0.1', 7532)
        #           beta connects with ha=('127.0.0.1', 7531)
        oldHa = (beta.local.ha[0], 7532)
        newHa = (beta.local.ha[0], beta.local.ha[1])

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
        # RHA:  New: alpha remote ha is set to (127.0.0.1, 7532)
        #             new ha received from beta is (127.0.0.1, 7531)
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
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.ha, newHa)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.fuid, newFuid)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

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
        alpha, beta = self.bootstrapStacks()
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
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(beta.mutable, None)
        self.assertTrue(alpha.mutable)
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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

        alpha, beta = self.bootstrapStacks()

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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats.keys())
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats.keys())
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alpha.remotes.values()[0], remoteData))
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

        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertIs(alphaRemote.main, newMain)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump of pended data
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['main'], beta.main) # new main value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)

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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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

        alpha, beta = self.bootstrapStacks()

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
        # Kind: New
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.kind, newKind)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['kind'], beta.kind) # new main value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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

        alpha, beta = self.bootstrapStacks()

        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Simulate: alpha already know beta with ha=('127.0.0.1', 7532)
        #           beta connects with ha=('127.0.0.1', 7531)
        oldHa = (beta.local.ha[0], 7532)
        newHa = (beta.local.ha[0], beta.local.ha[1])

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
        # RHA:  New: alpha remote ha is set to (127.0.0.1, 7532)
        #             new ha received from beta is (127.0.0.1, 7531)
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(tuple(remoteData['ha']), beta.local.ha) # new value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)
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
        alpha, beta = self.bootstrapStacks()
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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

        alpha, beta = self.bootstrapStacks()

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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIs(alpha.remotes.values()[0].acceptance, raeting.acceptances.pending)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        alpha, beta = self.bootstrapStacks()

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
        # Name: Either
        # Main: New
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

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()

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
        # Name: Either
        # Main: Either
        # Kind: New
        self.assertIs(beta.kind, oldKind)
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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        alpha, beta = self.bootstrapStacks()
        # Mutable: No
        self.assertIs(alpha.mutable, None)

        # Simulate: alpha already know beta with ha=('127.0.0.1', 7532)
        #           beta connects with ha=('127.0.0.1', 7531)
        oldHa = (beta.local.ha[0], 7532)
        newHa = (beta.local.ha[0], beta.local.ha[1])

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
        # RHA:  New: alpha remote ha is set to (127.0.0.1, 7532)
        #             new ha received from beta is (127.0.0.1, 7531)
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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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

        # Name: Either
        # Main: Either
        # Kind: Either
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

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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

        # Name: Either
        # Main: Either
        # Kind: Either
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

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaREmote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha, beta = self.bootstrapStacks()
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
        # Name: Either
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

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, nack
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectNewKeys(self):
        '''
        Test joinent rejects non-vacuous join request with new keys from already rejected estate (I1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Kind: Either
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
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Assert remote and role aren't dumped
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Assert role dump isn't changed
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects non-vacuous join request with new role from already rejected estate (I2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)
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
        # Name: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], alphaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectSameAll(self):
        '''
        Test joinent rejects non-vacuous join request with same all from already rejected estate (J1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)

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
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(alpha.mutable)
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

        alpha, beta = self.bootstrapStacks(autoMode=raeting.autoModes.never)

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
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(alpha.mutable)
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.name, newName)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        remoteData['ha'] = tuple(remoteData['ha'])
        # Assert updated alphaRemote is dumped
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertIs(alphaRemote.main, newMain)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        # Kind: New
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertIs(alphaRemote.kind, newKind)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        # Kind: Either
        # RHA:  New
        oldHa = beta.local.ha
        newHa = (beta.local.ha[0], 7532)

        self.assertNotEqual(oldHa, newHa)
        # update beta HA
        beta.server.close()
        beta.ha = newHa
        beta.local.ha = newHa
        # recreate beta server socket
        beta.server = beta.serverFromLocal()
        reopenResult = beta.server.reopen()
        self.assertTrue(reopenResult)
        self.assertEqual(beta.server.ha, newHa)
        self.assertEqual(beta.local.ha, newHa)

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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        Test mutable joinent accept non-vacuous join with an updated role (K6)
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        Test mutable joinent accept non-vacuous join with an updated keys (K7)
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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.name, newName)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['name'], beta.name) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.main, newMain)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['main'], beta.main) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: New
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.kind, newKind)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['kind'], beta.kind) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

        alpha.keep.auto = raeting.autoModes.never
        # Mutable: Yes
        alpha.mutable = True

        # Simulate: alpha already know beta with ha=('127.0.0.1', 7532)
        #           beta connects with ha=('127.0.0.1', 7531)
        oldHa = (beta.local.ha[0], 7532)
        newHa = (beta.local.ha[0], beta.local.ha[1])

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
        # RHA:  New: alpha remote ha is set to (127.0.0.1, 7532),
        #             new ha received from beta is (127.0.0.1, 7531)
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.ha, newHa)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(tuple(remoteData['ha']), beta.local.ha) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertTrue(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.fuid, newFuid)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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
        # Kind: Either
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
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.verfer.keyhex, beta.local.signer.verhex)
        self.assertEqual(alphaRemote.pubber.keyhex, beta.local.priver.pubhex)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()

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

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
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
        alpha, beta = self.bootstrapStacks()
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

        # Action: Pend, No change
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        # Assert alphaRemote is modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        self.assertIs(alphaRemote.acceptance, raeting.acceptances.pending)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], beta.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], beta.local.priver.pubhex)
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
            self.assertTrue(stack.mutable)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['verhex'], beta.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewName(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated name (A1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewName.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: New
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewMain(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated main (A2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewMain.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: New
        betaRemote.main = False
        self.assertTrue(alpha.main)
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewKind(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated kind (A3)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewKind.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: New
        oldKind = alpha.kind
        newKind = 33
        self.assertNotEqual(oldKind, newKind)
        alpha.kind = newKind
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewKeys(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated keys (A4)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewKeys.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewRole(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated role (A5)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewRole.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedRejectNewKeys(self):
        '''
        Test mutable joiner reject vacuous renewal join with updated keys (B1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.rejected)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedRejectNewRole(self):
        '''
        Test mutable joiner reject vacuous renewal join with updated role (B2)
        '''
        # FIXME: The test doesn't pass: status is pending
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: Yes
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)
        #beta.keep.rejectRemote(betaRemote)

        ## Action: Reject
        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.rejected)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIn('joinent_transaction_failure', alpha.stats)
        #self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        #self.assertIn('joiner_transaction_failure', beta.stats)
        #self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedRejectSameAll(self):
        '''
        Test joiner reject rejected vacuous renewal join with same all (C1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Either

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertNotIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedNorenewRejectSameAll(self):
        '''
        Test joiner reject rejected vacuous no renewal join with same all (C2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedNorenewRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Body
        # Main: Body
        # Kind: Body
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Body
        # Keys: Body
        # Sameness: SameAll
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Either

        # Test
        # Renew: No
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=False)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertNotIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joiner reject rejected vacuous renewal join with same role/keys (C3)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: Same Role/Keys
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Either

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptNewName(self):
        '''
        Test mutable joiner accept vacuous renewal join with updated name (D1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptNewName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: New
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.name, newName)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptNewMain(self):
        '''
        Test mutable joiner accept vacuous renewal join with updated main (D2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Main: New, it can only happen if old Main value is False (or None) it's because Joinent could only be main
        # to accept transaction. So bootstrap slave alpha joined to main beta. Then set alpha to be main and rejoin.
        beta, alpha = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: New
        oldMain = None
        newMain = True
        self.assertIs(alpha.main, oldMain)
        alpha.main = newMain
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.main, newMain)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptNewKind(self):
        '''
        Test mutable joiner accept vacuous renewal join with updated kind (D3)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: New
        oldKind = alpha.kind
        newKind = 33
        self.assertNotEqual(oldKind, newKind)
        alpha.kind = newKind
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.kind, newKind)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptNewKeys(self):
        '''
        Test mutable joiner accept vacuous renewal join with updated keys (D4)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Always
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.autoModes.always)
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.verfer.keyhex, alpha.local.signer.verhex)
        self.assertEqual(betaRemote.pubber.keyhex, alpha.local.priver.pubhex)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptNewRole(self):
        '''
        Test mutable joiner accept vacuous renewal join with updated role (D5)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptSameAll(self):
        '''
        Test joiner accept vacuous renewal join with sameall (E1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(betaRemote)

        # Mutable: Either
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertIs(beta.mutable, None)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousNorenewAcceptSameAll(self):
        '''
        Test joiner accept vacuous no renew join with sameall (E2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousNorenewAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Body
        # Keys: Body
        # Sameness: SameAll
        keep = self.copyData(betaRemote)

        # Mutable: Either
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Test
        # Renew: No
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=False)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertIs(beta.mutable, None)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewName(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated name (F1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewName.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                       ha=("", raeting.RAET_PORT),
                                       main=True,
                                       auto=raeting.autoModes.once,
                                       role=None,
                                       kind=None,
                                       mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.autoModes.once,
                                             role=None,
                                             kind=None,
                                             mutable=True, )

        self.assertIs(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))

        # Do initial join vacuous join to setup rejoin with renew
        # create remote to join to alpha
        remote =  beta.addRemote(estating.RemoteEstate(stack=beta,
                                                        fuid=0, # vacuous join
                                                        sid=0, # always 0 for join
                                                        ha=alpha.local.ha))
        self.join(beta, alpha, deid=remote.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        self.assertEqual(alphaRemoteBeta.name, 'beta')

        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertEqual(betaRemoteAlpha.name, 'alpha')

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Pending
        beta.keep.pendRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.acceptances.pending)
        beta.keep.auto = raeting.autoModes.never
        self.assertEqual(beta.keep.auto, raeting.autoModes.never)
        # Name: New # have to do this mid transaction below
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        # Mutable: Yes
        self.assertIs(beta.mutable, True)

        beta.clearStats()
        alpha.clearStats()

        # Test
        # Renew: Yes
        # Name change of Joinent on renew rejoin could occur several ways
        # One is Joinent is dynamically changing its name mid transaction
        # Another is Joinent name was changed between end of
        # Join where Joinent refused with nack renew transaction
        # and start of Joiner renew rejoin We implement the later
        # to do this we manually step through the transactions
        console.terse("\n Rejoin Failed with nack Renew Transaction **************\n")
        beta.join(uid=betaRemoteAlpha.uid) #join
        beta.serviceOneAllTx()
        self.store.advanceStamp(0.05)
        time.sleep(0.05)
        alpha.serviceOneAllRx()
        alpha.serviceOneAllTx() # Ack Renew
        self.store.advanceStamp(0.05)
        time.sleep(0.05)

        # Close down alpha stack
        alpha.server.close()
        alpha.clearAllKeeps()

        # now create new Joinent stack with new name but same role
        gamma, gammaData = self.bootstrapStack(name='gamma',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.autoModes.once,
                                               role='alpha',
                                               sigkey=alpha.local.signer.keyhex,
                                               prikey=alpha.local.priver.keyhex,
                                               kind=None,
                                               mutable=True, )


        self.assertEqual(gamma.name, 'gamma')
        self.assertEqual(gamma.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(gamma.local.ha, ('127.0.0.1', raeting.RAET_PORT))
        self.assertEqual(gamma.local.role, 'alpha')
        self.assertEqual(gamma.local.signer.keyhex, alpha.local.signer.keyhex)
        self.assertEqual(gamma.local.priver.keyhex, alpha.local.priver.keyhex)

        # now allow socket to send packet resume transaction
        console.terse("\n Renew Rejoin Transaction **************\n")
        self.serviceStacks([beta, gamma])

        # Action: Pend, Dump
        self.assertIn('joiner_rx_renew', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_renew'], 1)
        self.assertIn('join_renew_attempt', beta.stats)
        self.assertEqual(beta.stats['join_renew_attempt'], 1)

        self.assertIn('joinent_rx_pend', gamma.stats)
        self.assertEqual(gamma.stats['joinent_rx_pend'], 1)

        for stack in [gamma, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        gammaRemoteBeta = gamma.remotes.values()[0]
        self.assertIs(gammaRemoteBeta.acceptance, raeting.acceptances.accepted)

        self.assertIs(beta.mutable, True)
        betaRemoteGamma = beta.remotes.values()[0]
        self.assertIs(betaRemoteAlpha, betaRemoteGamma) # same remote on beta side
        self.assertFalse(self.sameAll(betaRemoteGamma, betaRemoteAlphaSave))
        self.assertTrue(self.sameRoleKeys(betaRemoteGamma, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteGamma.name, gamma.name)
        self.assertIs(betaRemoteGamma.acceptance, raeting.acceptances.pending)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(gamma.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['name'], gamma.name) # new name value
        self.assertEqual(remoteData['fuid'], gammaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], gamma.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], gamma.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], gamma.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(gamma.local.role)
        self.assertEqual(roleData['role'], gamma.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['verhex'], gamma.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], gamma.local.priver.pubhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemoteAlpha)
        self.serviceStacks([gamma, beta], duration=3.0)

        for stack in [gamma, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.assertTrue(beta.mutable)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)
        self.assertEqual(betaRemoteGamma.name, gamma.name) # new name value

        self.assertIn('join_correspond_complete', gamma.stats)
        self.assertEqual(gamma.stats['join_correspond_complete'], 1)


        # Check remote dump
        remoteData = beta.keep.loadRemoteData(gamma.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemoteGamma, remoteData))
        self.assertIs(remoteData['main'], True) # new main value
        self.assertIs(remoteData['fuid'], gammaRemoteBeta.uid) # value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(gamma.local.role)
        self.assertEqual(roleData['role'], gamma.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['verhex'], gamma.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], gamma.local.priver.pubhex)

        for stack in [gamma, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewMain(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated main (F2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewMain.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.autoModes.once,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.autoModes.once,
                                             role=None,
                                             kind=None,
                                             mutable=True, )

        self.assertIs(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))

        # Do initial join vacuous join to setup rejoin with renew
        # create remote to join to alpha
        remote =  beta.addRemote(estating.RemoteEstate(stack=beta,
                                                        fuid=0, # vacuous join
                                                        sid=0, # always 0 for join
                                                        ha=alpha.local.ha))
        self.join(beta, alpha, deid=remote.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        self.assertIs(alphaRemoteBeta.main, False)

        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertIs(betaRemoteAlpha.main, True)

        # now set the alpha.main to False and rejoin as the initial condition
        alpha.main = False
        self.assertIs(alpha.main, False)
        self.join(beta, alpha, deid=remote.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertIs(betaRemoteAlpha.main, False)

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Pending
        beta.keep.pendRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.acceptances.pending)
        beta.keep.auto = raeting.autoModes.never
        self.assertEqual(beta.keep.auto, raeting.autoModes.never)
        # Name: Either
        # Main: New  # old value was False now we change to True
        oldMain = alpha.main
        alpha.main = True
        self.assertIs(alpha.main, True)
        self.assertNotEqual(alpha.main, oldMain)
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        # Mutable: Yes
        self.assertIs(beta.mutable, True)

        beta.clearStats()
        alpha.clearStats()

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemoteAlpha.uid, duration=0.5)

        # Action: Pend, Dump
        self.assertIn('joiner_rx_renew', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_renew'], 1)
        self.assertIn('join_renew_attempt', beta.stats)
        self.assertEqual(beta.stats['join_renew_attempt'], 1)

        self.assertIn('stale_nuid', alpha.stats)
        self.assertEqual(alpha.stats['stale_nuid'], 1)
        self.assertIn('joinent_rx_pend', alpha.stats)
        self.assertEqual(alpha.stats['joinent_rx_pend'], 1)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.assertIs(beta.mutable, True)
        self.assertFalse(self.sameAll(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertTrue(self.sameRoleKeys(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteAlpha.main, alpha.main)
        self.assertIs(alphaRemoteBeta.acceptance, raeting.acceptances.accepted)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.acceptances.pending)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['main'], alpha.main) # new main value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemoteAlpha)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.assertTrue(beta.mutable)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)
        self.assertIs(betaRemoteAlpha.main, alpha.main) # new main value

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemoteAlpha, remoteData))
        self.assertIs(remoteData['main'], True) # new main value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.uid) # value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewKind(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated kind (F3)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewKind.__doc__))
        alpha, alphaData = self.bootstrapStack(name='alpha',
                                                       ha=("", raeting.RAET_PORT),
                                                       main=True,
                                                       auto=raeting.autoModes.once,
                                                       role=None,
                                                       kind=None,
                                                       mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.autoModes.once,
                                             role=None,
                                             kind=None,
                                             mutable=True, )

        self.assertIs(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))

        # Do initial join vacuous join to setup rejoin with renew
        # create remote to join to alpha
        remote =  beta.addRemote(estating.RemoteEstate(stack=beta,
                                                        fuid=0, # vacuous join
                                                        sid=0, # always 0 for join
                                                        ha=alpha.local.ha))
        self.join(beta, alpha, deid=remote.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        self.assertIs(alphaRemoteBeta.kind, 0)

        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertIs(betaRemoteAlpha.kind, 0)

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Pending
        beta.keep.pendRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.acceptances.pending)
        beta.keep.auto = raeting.autoModes.never
        self.assertEqual(beta.keep.auto, raeting.autoModes.never)
        # Name: Either
        # Main: Either
        # Kind: New # old value was None (0) now we change to 3
        oldKind = alpha.kind
        alpha.kind = 3
        self.assertIs(alpha.kind, 3)
        self.assertNotEqual(alpha.kind, oldKind)
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        # Mutable: Yes
        self.assertIs(beta.mutable, True)

        beta.clearStats()
        alpha.clearStats()

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemoteAlpha.uid, duration=0.5)

        # Action: Pend, Dump
        self.assertIn('joiner_rx_renew', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_renew'], 1)
        self.assertIn('join_renew_attempt', beta.stats)
        self.assertEqual(beta.stats['join_renew_attempt'], 1)

        self.assertIn('stale_nuid', alpha.stats)
        self.assertEqual(alpha.stats['stale_nuid'], 1)
        self.assertIn('joinent_rx_pend', alpha.stats)
        self.assertEqual(alpha.stats['joinent_rx_pend'], 1)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.assertIs(beta.mutable, True)
        self.assertFalse(self.sameAll(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertTrue(self.sameRoleKeys(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteAlpha.kind, alpha.kind)
        self.assertIs(alphaRemoteBeta.acceptance, raeting.acceptances.accepted)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.acceptances.pending)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['kind'], alpha.kind) # new kind value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(remoteData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(remoteData['pubhex'], alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemoteAlpha)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.assertTrue(beta.mutable)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)
        self.assertIs(betaRemoteAlpha.kind, alpha.kind) # new kind value

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemoteAlpha, remoteData))
        self.assertIs(remoteData['kind'], 3) # new main value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.uid) # value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewKeys(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated keys (F4)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewKeys.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: Yes
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=True, duration=0.10)
        ## FIXME: The pending role status returns 'rejected' for the new keys.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.verfer.keyhex, alpha.local.signer.verhex)
        #self.assertEqual(betaRemote.pubber.keyhex, alpha.local.priver.pubhex)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewRole(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated role (F5)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: Yes
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=True, duration=0.10)
        ## FIXME: The pending role status returns 'rejected' for the new keys.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.role, newRole)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendSameAll(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with same all (G1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendSameAll.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: Yes
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=True, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingNorenewPendSameAll(self):
        '''
        Test mutable joiner pend pending vacuous non renewal join with same all (G2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingNorenewPendSameAll.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Body
        # Main: Body
        # Kind: Body
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Body
        # Keys: Body
        # Sameness: SameAll
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: No
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=False, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewName(self):
        '''
        Test immutable joiner reject non vacuous join with updated name (H1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewName.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Name: New
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
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
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        self.join(beta, alpha)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewMain(self):
        '''
        Test immutable joiner reject non vacuous join with updated main (H2)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewMain.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: No
        # Main: New (set main to false in betaRemote)
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=False,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        self.assertIs(betaRemote.main, False)
        self.assertIs(alpha.main, True)
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        self.join(beta, alpha)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewKind(self):
        '''
        Test immutable joiner reject non vacuous join with updated kind (H3)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewKind.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        # Kind: New
        oldKind = None
        newKind = 33
        self.assertIs(alpha.kind, oldKind)
        alpha.kind = newKind
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewRha(self):
        '''
        Test immutable joiner reject non vacuous join with updated host address (H4)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewRha.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        oldHa = ('127.0.0.1', 7532)
        newHa = alpha.local.ha

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=oldHa,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        # Kind: Either
        # RHA:  New
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid)

        ## Action: Reject
        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertIs(stack.mutable, None)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertIs(remote.acceptance, None)
        #self.assertEqual(len(alpha.remotes), 0)
        #self.assertEqual(len(alpha.nameRemotes), 0)
        #self.assertEqual(len(beta.remotes), 1)
        #self.assertEqual(len(beta.nameRemotes), 1)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIn('joinent_transaction_failure', alpha.stats)
        #self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        #self.assertIn('joiner_transaction_failure', beta.stats)
        #self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], None)
        #self.assertEqual(roleData['verhex'], None)
        #self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewFuid(self):
        '''
        Test immutable joiner reject non vacuous join with updated fuid/reid (H5)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewFuid.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: New:
        #   1. Initiate join with initFuid
        #   2. Update betaRemote.fuid = fakeFuid
        #   3. Accept alpha responce:
        #       - alpha will respond with initFuid
        #       - beta will know fakeFuid
        initFuid = alphaRemote.nuid
        fakeFuid = initFuid + 10
        # Leid: Old
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        ## Test
        #console.terse("\nJoin Transaction **************\n")
        #beta.join(uid=betaRemote.nuid)
        #betaRemote.fuid = fakeFuid
        #self.serviceStacks([alpha, beta])

        ## Action: Reject
        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertIs(stack.mutable, None)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertIs(remote.acceptance, None)
        #self.assertEqual(len(alpha.remotes), 0)
        #self.assertEqual(len(alpha.nameRemotes), 0)
        #self.assertEqual(len(beta.remotes), 1)
        #self.assertEqual(len(beta.nameRemotes), 1)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIn('joinent_transaction_failure', alpha.stats)
        #self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        #self.assertIn('joiner_transaction_failure', beta.stats)
        #self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], None)
        #self.assertEqual(roleData['verhex'], None)
        #self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewKeys(self):
        '''
        Test immutable joiner reject non vacuous join with updated keys (H6)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewKeys.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()
        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousImmutableRejectNewRole(self):
        '''
        Test immutable joiner reject non vacuous join with updated name (H7)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousImmutableRejectNewRole.__doc__))

        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks()

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
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
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousRejectedRejectNewKeys(self):
        '''
        Test mutable joiner reject non vacuous join with updated keys (I1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousRejectedRejectNewKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.rejected)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousRejectedRejectNewRole(self):
        '''
        Test mutable joiner reject non vacuous renewal join with updated role (I2)
        '''
        # FIXME: The test doesn't pass: status is pending
        console.terse("{0}\n".format(self.testJoinerNonVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid)
        #beta.keep.rejectRemote(betaRemote)

        ## Action: Reject
        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.rejected)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIn('joinent_transaction_failure', alpha.stats)
        #self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        #self.assertIn('joiner_transaction_failure', beta.stats)
        #self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joiner reject rejected non vacuous renewal join with same role/keys (J1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Either
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: Same Role/Keys
        keep = self.copyData(betaRemote)

        # Mutable: Either

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousRejectedRejectSameAll(self):
        '''
        Test joiner reject rejected non vacuous renewal join with same all (J2)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: Yes
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)
        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemote)

        # Name: Old
        # Main: Old
        # Kind: Old
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Old
        # Keys: Old
        # Sameness: SameAll
        keep = self.copyData(betaRemote)

        # Mutable: Either

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertNotIn('joinent_transaction_failure', alpha.stats)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.rejected)
        self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewName(self):
        '''
        Test mutable joiner accept non vacuous renewal join with updated name (K1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: New
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
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
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.name, newName)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewMain(self):
        '''
        Test mutable joiner accept non vacuous join with updated main (K2)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewMain.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        # Main: New, it can only happen if old Main value is False (or None) it's because Joinent could only be main
        # to accept transaction. So bootstrap slave alpha joined to main beta. Then set alpha to be main and rejoin.
        beta, alpha = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: New
        oldMain = None
        newMain = True
        self.assertIs(alpha.main, oldMain)
        alpha.main = newMain
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.main, newMain)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewKind(self):
        '''
        Test mutable joiner accept non vacuous join with updated kind (K3)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: New
        oldKind = alpha.kind
        newKind = 33
        self.assertNotEqual(oldKind, newKind)
        alpha.kind = newKind
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.kind, newKind)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewRha(self):
        '''
        Test mutable joiner accept non vacuous join with updated host address (K4)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewRha.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Always
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.autoModes.always)
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  New
        #   1. Initiate join with initHa
        #   2. Set betaRemote.ha = fakeHa
        #   3. Accept alpha responce:
        #       - alpha will respond with initHa
        #       - beta will know fakeHa
        initHa = alpha.local.ha
        fakeHa = ('127.0.0.5', alpha.local.ha[1])
        self.assertNotEqual(initHa, fakeHa)
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        # Renew: No
        console.terse("\nJoin Transaction **************\n")
        beta.join(uid=betaRemote.nuid)
        betaRemote.ha = fakeHa
        # Keep beta values here, before accept. Accept will change it because not same all
        keep = self.copyData(betaRemote)
        self.serviceStacks([alpha, beta])

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.ha, alpha.local.ha)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewFuid(self):
        '''
        Test mutable joiner accept non vacuous join with updated host fuid/reid (K5)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewFuid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Always
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.autoModes.always)
        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: New:
        #   1. Initiate join with initFuid
        #   2. Update betaRemote.fuid = fakeFuid
        #   3. Accept alpha responce:
        #       - alpha will respond with initFuid
        #       - beta will know fakeFuid
        initFuid = alphaRemote.nuid
        fakeFuid = initFuid + 10
        # Leid: Old
        # Reid: New
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=fakeFuid)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        # Renew: No
        console.terse("\nJoin Transaction **************\n")
        beta.join(uid=betaRemote.nuid)
        betaRemote.fuid = fakeFuid
        self.serviceStacks([alpha, beta])

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.fuid, initFuid)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewRole(self):
        '''
        Test mutable joiner accept non vacuous join with updated role (K6)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.role, newRole)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptNewKeys(self):
        '''
        Test mutable joiner accept non vacuous join with updated keys (K7)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Always
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.autoModes.always)
        betaRemote = beta.remotes.values()[0]

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.verfer.keyhex, alpha.local.signer.verhex)
        self.assertEqual(betaRemote.pubber.keyhex, alpha.local.priver.pubhex)
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousAcceptSameAll(self):
        '''
        Test joiner accept non vacuous join with same all (L1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]

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
        keep = self.copyData(betaRemote)

        # Mutable: Either
        # Vacuous: No

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewName(self):
        '''
        Test mutable joiner pend pending vacuous join with updated name (M1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewName.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: New
        oldName = alpha.name
        newName = '{0}_new'.format(oldName)
        alpha.name = newName
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
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.name, newName)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewMain(self):
        '''
        Test mutable joiner pend pending non vacuous join with updated main (M2)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewMain.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        # Main: New (set main to false in betaRemote)
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=False,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: New
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.main, alpha.main)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewKind(self):
        '''
        Test mutable joiner pend pending non vacuous join with updated kind (M3)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewKind.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: New
        oldKind = alpha.kind
        newKind = 33
        self.assertIs(alpha.kind, oldKind)
        alpha.kind = newKind
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.kind, newKind)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewRha(self):
        '''
        Test mutable joiner pend pending vacuous join with updated host address (M4)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewName.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  New
        #   1. Initiate join with initHa
        #   2. Set betaRemote.ha = fakeHa
        #   3. Accept alpha responce:
        #       - alpha will respond with initHa
        #       - beta will know fakeHa
        initHa = alpha.local.ha
        fakeHa = ('127.0.0.5', alpha.local.ha[1])
        self.assertNotEqual(initHa, fakeHa)
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #console.terse("\nJoin Transaction **************\n")
        #beta.join(uid=betaRemote.nuid)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.
        #betaRemote.ha = fakeHa
        ## Keep beta values here, before accept. Accept will change it because not same all
        #keep = self.copyData(betaRemote)
        #self.serviceStacks([alpha, beta], duration=0.10)

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.ha, alpha.local.ha)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewFuid(self):
        '''
        Test mutable joiner pend pending vacuous join with updated fuid/reid (M5)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewFuid.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: New:
        #   1. Initiate join with initFuid
        #   2. Update betaRemote.fuid = fakeFuid
        #   3. Accept alpha responce:
        #       - alpha will respond with initFuid
        #       - beta will know fakeFuid
        initFuid = alphaRemote.nuid
        fakeFuid = initFuid + 10
        # Leid: Old
        # Reid: Either
        # Role: Either
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote, fuid=fakeFuid)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #console.terse("\nJoin Transaction **************\n")
        #beta.join(uid=betaRemote.nuid)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.
        #betaRemote.fuid = fakeFuid
        #self.serviceStacks([alpha, beta], duration=0.10)

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.fuid, initFuid)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewKeys(self):
        '''
        Test mutable joiner pend pending non vacuous join with updated keys (M6)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewKeys.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: Old
        # Keys: New
        alpha.local.signer = nacling.Signer()
        alpha.local.priver = nacling.Privateer()
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid, duration=0.10)
        ## FIXME: The pending role status returns 'rejected' for the new keys.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.verfer.keyhex, alpha.local.signer.verhex)
        #self.assertEqual(betaRemote.pubber.keyhex, alpha.local.priver.pubhex)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewRole(self):
        '''
        Test mutable joiner pend pending non vacuous join with updated role (M7)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Either
        # Nuid: Old
        # Fuid: Either
        # Leid: Old
        # Reid: Either
        # Role: New
        oldRole = alpha.local.role
        newRole = '{0}_new'.format(oldRole)
        alpha.local.role = newRole
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        #self.join(beta, alpha, deid=betaRemote.nuid, duration=0.10)
        ## FIXME: The pending role status returns 'rejected' for the new keys.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertFalse(self.sameAll(betaRemote, keep))
        #self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        #self.assertEqual(betaRemote.role, newRole)
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendSameAll(self):
        '''
        Test mutable joiner pend pending non vacuous join with same all (N1)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendSameAll.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.autoModes.never

        # Vacuous: No
        betaRemote = estating.RemoteEstate(stack=beta,
                                           fuid=0,
                                           sid=0, # always 0 for join
                                           ha=alpha.local.ha,
                                           main=True,
                                           name=alpha.name,
                                           verkey=alpha.local.signer.verhex,
                                           pubkey=alpha.local.priver.pubhex)

        alphaRemote = estating.RemoteEstate(stack=beta,
                                            fuid=betaRemote.nuid,
                                            ha=beta.local.ha,
                                            name=beta.name,
                                            verkey=beta.local.signer.verhex,
                                            pubkey=beta.local.priver.pubhex)
        betaRemote.fuid = alphaRemote.nuid
        alpha.addRemote(alphaRemote)
        beta.addRemote(betaRemote)

        # Status: Pending
        beta.keep.pendRemote(betaRemote)

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
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        ## Test
        ## Renew: Yes
        #self.join(beta, alpha, deid=betaRemote.nuid, renewal=True, duration=0.10)
        ## FIXME: The transaction is dropped here, right after pend from beta side.
        ##        After this all Redo Accepts from alpha become dropped by beta.

        ## Action: Pend, Dump
        #for stack in [alpha, beta]:
            ## self.assertEqual(len(stack.transactions), 1) #b=0
            #self.assertEqual(len(beta.remotes), 1)
            #self.assertEqual(len(beta.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertIs(remote.joined, None)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertTrue(self.sameAll(betaRemote, keep))
        #self.assertIs(alphaRemote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(betaRemote.acceptance, raeting.acceptances.pending)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #self.assertIs(remoteData, None)
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.pending)
        #self.assertEqual(roleData['verhex'], betaRemote.verfer.keyhex)
        #self.assertEqual(roleData['pubhex'], betaRemote.pubber.keyhex)

        ## Accept the transaction
        #console.terse("\nAccept Transaction **************\n")
        #beta.keep.acceptRemote(betaRemote)
        #self.serviceStacks([alpha, beta], duration=3.0)

        #for stack in [alpha, beta]:
            #self.assertEqual(len(stack.transactions), 0)
            #self.assertEqual(len(stack.remotes), 1)
            #self.assertEqual(len(stack.nameRemotes), 1)
            #for remote in stack.remotes.values():
                #self.assertTrue(remote.joined)
                #self.assertIs(remote.allowed, None)
                #self.assertIs(remote.alived, None)
                #self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        #self.assertIs(alpha.mutable, None)
        #self.assertTrue(beta.mutable)
        #self.assertIn('join_correspond_complete', alpha.stats)
        #self.assertEqual(alpha.stats['join_correspond_complete'], 1)
        #self.assertIn('join_initiate_complete', beta.stats)
        #self.assertEqual(beta.stats['join_initiate_complete'], 1)

        ## Check remote dump
        #remoteData = beta.keep.loadRemoteData(alpha.local.name)
        #remoteData['ha'] = tuple(remoteData['ha'])
        #self.assertTrue(self.sameAll(betaRemote, remoteData))
        ## Check role/keys dump
        #roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        #self.assertEqual(roleData['role'], alpha.local.role)
        #self.assertEqual(roleData['acceptance'], raeting.acceptances.accepted)
        #self.assertEqual(roleData['verhex'], alpha.local.signer.verhex)
        #self.assertEqual(roleData['pubhex'], alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    # TODO: Z1

    def testJoinentNonMainRejectJoin(self):
        '''
        Test non main joinent reject join (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentNonMainRejectJoin.__doc__))

        alpha, beta = self.bootstrapStacks()
        alpha.main = False

        # Test
        self.join(beta, alpha)

        # Action: nack reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alpha.mutable, None)
        self.assertIs(beta.mutable, None)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        allRemoteData = alpha.keep.loadAllRemoteData()
        self.assertEqual(len(allRemoteData), 0)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinRenameRemoteFail(self):
        '''
        Test joinent join renameRemote() call fail (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinRenameRemoteFail.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        alpha.mutable = True
        alpha.nameRemotes['beta_wrong'] = alpha.nameRemotes[beta.name]
        del alpha.nameRemotes[beta.name]
        beta.name = 'beta_new'

        # Test
        self.join(beta, alpha)

        # Action: nack reject
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinRejectNameConflict(self):
        '''
        Test joinent join non unique name fail (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinRejectNameConflict.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        # Create another one stack
        gammaData = self.createRoadData(base=self.base,
                                        name='gamma',
                                        ha=("", 7532),
                                        main=None,
                                        auto=raeting.autoModes.always)
        keeping.clearAllKeep(gammaData['dirpath'])
        gamma = self.createRoadStack(data=gammaData)
        self.join(gamma, alpha)
        self.assertTrue(gamma.remotes.values()[0].joined)

        # Rename gamma to 'beta'
        alpha.mutable = True
        gamma.name = 'beta'

        # Test
        self.join(gamma, alpha)

        # Action: nack reject
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptRejectNameConflict(self):
        '''
        Test joiner.join rejects rename if such name is already registered (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptRejectNameConflict.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]
        fakeRemote = beta.addRemote(
            estating.RemoteEstate(stack=beta,
                                  fuid=0, # vacuous join
                                  sid=0, # always 0 for join
                                  name='alpha_new',
                                  ha=(alpha.local.ha[0], alpha.local.ha[1] + 10)))

        alpha.name = 'alpha_new'
        beta.mutable = True

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: nack reject
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptRejectRenameFail(self):
        '''
        Test joiner reject rename if renameRemote() fail (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptRejectRenameFail.__doc__))

        # Status: Accepted (auto accept keys)
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemote = beta.remotes.values()[0]
        beta.mutable = True
        # Following will produce rename fail
        beta.nameRemotes['alpha_wrong'] = beta.nameRemotes[alpha.name]
        del beta.nameRemotes[alpha.name]
        alpha.name = 'alpha_new'

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: nack reject
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

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
                'testJoinentNonVacuousAcceptNewRole',
                'testJoinentNonVacuousAcceptNewKeys',
                'testJoinentNonVacuousAcceptSameAll',
                'testJoinentNonVacuousPendingPendNewName',
                'testJoinentNonVacuousPendingPendNewMain',
                'testJoinentNonVacuousPendingPendNewKind',
                'testJoinentNonVacuousPendingPendNewRha',
                'testJoinentNonVacuousPendingPendNewFuid',
                'testJoinentNonVacuousPendingPendNewKeys',
                'testJoinentNonVacuousPendingPendNewRole',
                'testJoinentNonVacuousPendingPendSameAll',
                'testJoinerVacuousImmutableRejectNewName',
                'testJoinerVacuousImmutableRejectNewMain',
                'testJoinerVacuousImmutableRejectNewKind',
                'testJoinerVacuousImmutableRejectNewKeys',
                'testJoinerVacuousImmutableRejectNewRole',
                'testJoinerVacuousRejectedRejectNewKeys',
                'testJoinerVacuousRejectedRejectNewRole',
                'testJoinerVacuousRejectedRejectSameAll',
                'testJoinerVacuousRejectedNorenewRejectSameAll',
                'testJoinerVacuousRejectedRejectSameRoleKeys',
                'testJoinerVacuousAcceptNewName',
                'testJoinerVacuousAcceptNewMain',
                'testJoinerVacuousAcceptNewKind',
                'testJoinerVacuousAcceptNewKeys',
                'testJoinerVacuousAcceptNewRole',
                'testJoinerVacuousAcceptSameAll',
                'testJoinerVacuousNorenewAcceptSameAll',
                'testJoinerVacuousPendingPendNewName',
                'testJoinerVacuousPendingPendNewMain',
                'testJoinerVacuousPendingPendNewKind',
                'testJoinerVacuousPendingPendNewKeys',
                'testJoinerVacuousPendingPendNewRole',
                'testJoinerVacuousPendingPendSameAll',
                'testJoinerVacuousPendingNorenewPendSameAll',
                'testJoinerNonVacuousImmutableRejectNewName',
                'testJoinerNonVacuousImmutableRejectNewMain',
                'testJoinerNonVacuousImmutableRejectNewKind',
                'testJoinerNonVacuousImmutableRejectNewRha',
                'testJoinerNonVacuousImmutableRejectNewFuid',
                'testJoinerNonVacuousImmutableRejectNewKeys',
                'testJoinerNonVacuousImmutableRejectNewRole',
                'testJoinerNonVacuousRejectedRejectNewKeys',
                'testJoinerNonVacuousRejectedRejectNewRole',
                'testJoinerNonVacuousRejectedRejectSameRoleKeys',
                'testJoinerNonVacuousRejectedRejectSameAll',
                'testJoinerNonVacuousAcceptNewName',
                'testJoinerNonVacuousAcceptNewMain',
                'testJoinerNonVacuousAcceptNewKind',
                'testJoinerNonVacuousAcceptNewRha',
                'testJoinerNonVacuousAcceptNewFuid',
                'testJoinerNonVacuousAcceptNewRole',
                'testJoinerNonVacuousAcceptNewKeys',
                'testJoinerNonVacuousAcceptSameAll',
                'testJoinerNonVacuousPendingPendNewName',
                'testJoinerNonVacuousPendingPendNewMain',
                'testJoinerNonVacuousPendingPendNewKind',
                'testJoinerNonVacuousPendingPendNewRha',
                'testJoinerNonVacuousPendingPendNewFuid',
                'testJoinerNonVacuousPendingPendNewKeys',
                'testJoinerNonVacuousPendingPendNewRole',
                'testJoinerNonVacuousPendingPendSameAll',
                'testJoinentNonMainRejectJoin',
                'testJoinentJoinRenameRemoteFail',
                'testJoinentJoinRejectNameConflict',
                'testJoinerAcceptRejectNameConflict',
                'testJoinerAcceptRejectRenameFail',
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

    #runOne('testJoinentVacuousRejectedRejectNewRole')
