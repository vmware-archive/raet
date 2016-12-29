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
from collections import deque

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.aid.aiding import packByte
from ioflo.base.storing import Store
from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import estating, keeping, stacking, packeting, transacting

if sys.platform == 'win32':
    TEMPDIR = 'c:\\temp'
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

    def serviceStacksDropRx(self, stacks, drop=[], duration=1.0):
        '''
        Utility method to service queues for list of stacks. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            for stack in stacks:
                stack.serviceReceives()
                if stack in drop:
                    stack.rxes.clear()
                stack.serviceRxes()
                stack.process()
                stack.serviceAllTx()
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.05)
            time.sleep(0.05)

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

    def bootstrapJoinedRemotes(self, autoMode=raeting.AutoMode.once.value):
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

    def bootstrapStacks(self, autoMode=raeting.AutoMode.once.value):
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
                       auto=raeting.AutoMode.never.value,
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
        keep['verhex'] = str(remote.verfer.keyhex.decode('ISO-8859-1'))
        keep['pubhex'] = str(remote.pubber.keyhex.decode('ISO-8859-1'))
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
                remote.verfer.keyhex == ns2b(data['verhex']) and
                remote.pubber.keyhex == ns2b(data['pubhex']))

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
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=None,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin from Beta to Alpha *********\n")
        self.assertTrue(alpha.main)
        self.assertIs(alpha.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, None)
        self.assertIs(beta.keep.auto, raeting.AutoMode.once.value)
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
                self.assertIs(remote.alived, True)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()


    def testJoinJointVacuuousMain(self):
        '''
        Test join vacuous,initiated by main both sides
        '''
        console.terse("{0}\n".format(self.testJoinJointVacuuousMain.__doc__))

        alphaData = self.createRoadData(base=self.base,
                                        name='alpha',
                                        ha=("", raeting.RAET_PORT),
                                        main=True,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=True,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin Joint Alpha and Beta *********\n")
        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, True)
        self.assertIs(beta.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(len(beta.remotes), 0)

        console.terse("\nJoint Join Transaction **************\n")
        remote = alpha.addRemote(estating.RemoteEstate(stack=alpha,
                                                    fuid=0, # vacuous join
                                                    sid=0, # always 0 for join
                                                    ha=beta.local.ha))
        alpha.join(uid=remote.uid, cascade=False, renewal=False)
        remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                       fuid=0, # vacuous join
                                                       sid=0, # always 0 for join
                                                       ha=alpha.local.ha))
        beta.join(uid=remote.uid, cascade=False, renewal=False)

        self.serviceStacks([alpha, beta], duration=2.0)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        console.terse("\nAllow Joint Beta and Alpha *********\n")
        self.allow(beta, alpha)
        self.allow(alpha, beta)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertTrue(remote.allowed)
                self.assertIs(remote.alived, True)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinJointVacuuousMainWithMain(self):
        '''
        Test join vacuous,initiated by main both sides with main kind set
        to True in remotes before join
        '''
        console.terse("{0}\n".format(self.testJoinJointVacuuousMainWithMain.__doc__))

        alphaData = self.createRoadData(base=self.base,
                                        name='alpha',
                                        ha=("", raeting.RAET_PORT),
                                        main=True,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(alphaData['dirpath'])
        alpha = self.createRoadStack(data=alphaData)

        betaData = self.createRoadData(base=self.base,
                                       name='beta',
                                       ha=("", raeting.RAET_TEST_PORT),
                                       main=True,
                                       auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(betaData['dirpath'])
        beta = self.createRoadStack(data=betaData)

        console.terse("\nJoin Joint Alpha and Beta *********\n")
        self.assertIs(alpha.main, True)
        self.assertIs(alpha.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertIs(beta.main, True)
        self.assertIs(beta.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(len(beta.remotes), 0)

        console.terse("\nJoint Join Transaction **************\n")
        remote = alpha.addRemote(estating.RemoteEstate(stack=alpha,
                                                       fuid=0, # vacuous join
                                                       sid=0, # always 0 for join
                                                       ha=beta.local.ha,
                                                       main=True))
        alpha.join(uid=remote.uid, cascade=False, renewal=False)
        remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=alpha.local.ha,
                                                      main=True))
        beta.join(uid=remote.uid, cascade=False, renewal=False)

        self.serviceStacks([alpha, beta], duration=2.0)
        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        console.terse("\nAllow Joint Beta and Alpha *********\n")
        self.allow(beta, alpha)
        self.allow(alpha, beta)
        for stack in [beta, alpha]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertTrue(remote.allowed)
                self.assertIs(remote.alived, True)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        beta.dumpLocalRole()
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Ensure remote status is None
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

        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)
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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
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
        beta.dumpLocalRole()
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects vacuous join request with new role from already rejected estate (B2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never

        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)
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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Join with a new role
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, dump
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
        self.assertIn('joiner_rx_pend', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_pend'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(alphaRemote, remoteData))
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)

        # Reject the new role
        alpha.keep.rejectRemote(alphaRemote)
        self.serviceStacks([alpha, beta])

        # Action: Reject, don't clear
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(alpha.nameRemotes), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertTrue(alpha.mutable)
        self.assertIs(beta.mutable, None)
        self.assertFalse(self.sameAll(alphaRemote, keep))
        self.assertFalse(self.sameRoleKeys(alphaRemote, keep))
        self.assertEqual(alphaRemote.role, newRole)
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joinent rejects vacuous join request with same role and keys but not sameall (C1)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)
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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousRejectedRejectSameAll(self):
        '''
        Test joinent rejects vacuous join request with same all from already rejected estate (C2)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)
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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousEphemeralRejectedRejectSameall(self):
        '''
        Test joinent rejects vacuous ephemeral join from already rejected estate (C3)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousEphemeralRejectedRejectSameall.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)

        self.join(beta, alpha)

        # Status: Rejected
        alpha.keep.rejectRemote(alpha.remotes.values()[0])
        self.serviceStacks([alpha, beta], duration=3.0)

        # Ensure the next join would be ephemeral
        self.assertIs(len(alpha.remotes), 0)
        self.assertIs(len(alpha.nameRemotes), 0)

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        # Mutable: Either (use Yes, as most loyal)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousAcceptNewKeys(self):
        '''
        Test joinent accept vacuous join with an updated keys (D5)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousAcceptNewKeys.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Always
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)
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

        # Accept and dump the remote role to achieve the following:
        #   Status: Accepted
        #   Role: Old
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        beta.dumpLocalRole()
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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.acceptRemote(alphaRemote)

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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Ensure old remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Ensure alpha knows nothing about the new remote role
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        # Mutable: Either (use No)
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
        alpha.keep.acceptRemote(alphaRemote)
        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        # Set to most strict auto mode
        alpha.keep.auto = raeting.AutoMode.never.value

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
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha, beta = self.bootstrapJoinedRemotes()
        alpha.removeRemote(alpha.remotes.values()[0])
        beta.removeRemote(beta.remotes.values()[0])

        # Mutable: Either (use No as most strict)
        self.assertIs(alpha.mutable, None)
        # AutoMode: Any (use Never as most strict)
        alpha.keep.auto = raeting.AutoMode.never.value

        # Ensure the next join would be ephemeral
        self.assertIs(len(alpha.remotes), 0)
        self.assertIs(len(alpha.nameRemotes), 0)

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        # Join
        self.join(beta, alpha)

        # Action: Accept, Add, Dump
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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
        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump of pended data
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['main'], beta.main) # new main value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)

        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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
        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['kind'], beta.kind) # new main value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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
        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(tuple(remoteData['ha']), beta.local.ha) # new value
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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
        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentVacuousPendingPendNewRole(self):
        '''
        Test mutable joinent pend vacuous join with an updated role (F5)
        '''
        console.terse("{0}\n".format(self.testJoinentVacuousPendingPendNewRole.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapStacks()

        alpha.keep.auto = raeting.AutoMode.never.value
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
        alpha.keep.pendRemote(alphaRemote)

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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Ensure alpha knows nothing about the new role
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.auto = raeting.AutoMode.never.value
        # Mutable: Either
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
        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        # Assert alphaRemote isn't modified
        self.assertTrue(self.sameAll(alphaRemote, keep))

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha, beta = self.bootstrapJoinedRemotes()
        alpha.keep.pendRemote(alpha.remotes.values()[0])
        alpha.removeRemote(alpha.remotes.values()[0])
        beta.removeRemote(beta.remotes.values()[0])

        # Mutable: Either
        alpha.mutable = True
        # AutoMode: Never
        alpha.keep.auto = raeting.AutoMode.never.value

        # Ensure the next join would be ephemeral
        self.assertIs(len(alpha.remotes), 0)
        self.assertIs(len(alpha.nameRemotes), 0)

        # Ensure remote role is pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.clearStats()
        beta.clearStats()
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
        self.assertIs(alpha.remotes.values()[0].acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousImmutableRejectNewName(self):
        '''
        Test immutable joinent reject non-vacuous join with an updated name (H1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousImmutableRejectNewName.__doc__))

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always (use Always as most loyal
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always (use always as most loyal)

        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Status: None (auto accept keys)
        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is None
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        beta.dumpLocalRole()
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
        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is None
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

        # Mode: Never, Once (use once as more loyal)
        alpha, beta = self.bootstrapStacks()
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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        beta.dumpLocalRole()
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectNewRole(self):
        '''
        Test joinent rejects non-vacuous join request with new role from already rejected estate (I2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)
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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(alphaRemote)

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Ensure alpha knows nothing about the new role
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alphaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), alphaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectSameAll(self):
        '''
        Test joinent rejects non-vacuous join request with same all from already rejected estate (J1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)

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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joinent rejects non-vacuous join request with same role/keys from already rejected estate (J2)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never, Once

        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.never.value)

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

        # Ensure remote role is rejected
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        beta.dumpLocalRole()
        # Keys: Either
        # Sameness: Not SameAll, Not Same Role/Keys
        keep = self.copyData(alphaRemote)

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Ensure alpha knows nothing about the new role
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        # Mode: Always
        alpha.keep.auto = raeting.AutoMode.always.value
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
        beta.dumpLocalRole()
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousAcceptSameAll(self):
        '''
        Test joinent accept non-vacuous same all join (L1)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always (Use never as most strict)
        # Vacuous: No
        # Ephemeral: No Nuid (the Nuid is known)
        # Perform an auto-accepted join
        alpha, beta = self.bootstrapJoinedRemotes()

        alphaRemote = alpha.remotes.values()[0]
        betaRemote = beta.remotes.values()[0]

        # Mutable: Either (use No as more strict)
        self.assertIs(alpha.mutable, None)
        alpha.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote role is accepted
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Accept, No change
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(oldName)
        self.assertIs(remoteData, None)
        remoteData = alpha.keep.loadRemoteData(newName)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['name'], beta.name) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['main'], beta.main) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['kind'], beta.kind) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(tuple(remoteData['ha']), beta.local.ha) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['fuid'], betaRemote.nuid) # new value
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNonVacuousPendingPendNewRole(self):
        '''
        Test mutable joinent pend non-vacuous join with an updated role (M6)
        '''
        console.terse("{0}\n".format(self.testJoinentNonVacuousPendingPendNewRole.__doc__))

        # Status: Pending
        # Mode: Never
        alpha, beta = self.bootstrapStacks()

        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

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

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)
        # Ensure alpha knows nothing about the new role
        roleData = alpha.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
        alpha.keep.auto = raeting.AutoMode.never.value
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

        alpha.keep.pendRemote(alphaRemote)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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

        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.pending.value)
        self.assertIs(betaRemote.acceptance, None)

        # Check remote dump
        remoteData = alpha.keep.loadRemoteData(beta.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['role'], beta.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), beta.local.priver.pubhex)
        # Check role/keys dump
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertEqual(ns2b(roleData['verhex']), beta.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), beta.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRejectNewName(self):
        '''
        Test immutable joiner reject vacuous renewal join with updated name (A1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRejectNewName.__doc__))

        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha.dumpLocalRole()
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

        # Mode: Never, Once, Always (use always as most loyal)
        alpha, beta = self.bootstrapStacks(autoMode=raeting.AutoMode.always.value)

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
        alpha.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote, fuid=alphaRemote.nuid)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertIs(remote.acceptance, raeting.Acceptance.rejected.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedRejectNewRole(self):
        '''
        Test mutable joiner reject vacuous renewal join with updated role (B2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectNewRole.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.AutoMode.once.value,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertIs(beta.local.role, 'beta')

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Rejected
        beta.keep.rejectRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.rejected.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
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
        alpha.local.role = 'alpha_new'
        self.assertIs(alpha.local.role, 'alpha_new')
        self.assertNotEqual(alpha.local.role, oldRole)
        # Keys: Either
        # Sameness: Not sameall
        # Mutable: Yes
        self.assertIs(beta.mutable, True)

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        # Ensure beta knows nothing about the new role
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        self.assertEqual(alpha.stats['joinent_rx_pend'], 2)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.assertIs(beta.mutable, True)
        self.assertFalse(self.sameAll(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertFalse(self.sameRoleKeys(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteAlpha.role, alpha.local.role)
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Reject the transaction
        alpha.clearStats()
        beta.clearStats()
        console.terse("\nAccept Transaction **************\n")
        beta.keep.rejectRemote(betaRemoteAlpha)
        self.serviceStacks([alpha, beta], duration=6.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertTrue(beta.mutable)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 2)
        self.assertEqual(betaRemoteAlpha.role, alpha.local.role)

        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Mutable: Either (use Yes as more loyal)
        beta.mutable = True

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()


    def testJoinerVacuousRejectedRejectSameRoleKeys(self):
        '''
        Test joiner reject rejected vacuous renewal join with same role/keys (C2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedRejectSameRoleKeys.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousRejectedNorenewRejectSameAll(self):
        '''
        Test joiner reject rejected vacuous no renewal join with same all (C3)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousRejectedNorenewRejectSameAll.__doc__))

        # Mode: Never, Once
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Mutable: Either (use Yes as more loyal)
        beta.mutable = True

        # Test
        # Renew: No
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=False)

        # Action: Reject, Remove Clear
        for stack in [alpha, beta]:
            self.assertTrue(len(stack.stats) > 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.AutoMode.always.value)
        betaRemote = beta.remotes.values()[0]

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha.dumpLocalRole()
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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        # Ensure beta knows nothing about new role
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousAcceptSameAll(self):
        '''
        Test joiner accept vacuous renewal join with sameall (E1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always (use never as most strict)
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

        # Mutable: Either (use false as more strict)
        self.assertIs(beta.mutable, None)
        beta.keep.auto = raeting.AutoMode.never.value
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousNorenewAcceptSameAll(self):
        '''
        Test joiner accept vacuous no renew join with sameall (E2)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousNorenewAcceptSameAll.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always (use never as most strict)
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

        # Mutable: Either (use No as more strict)
        self.assertIs(beta.mutable, None)
        beta.keep.auto = raeting.AutoMode.never.value
        # Vacuous: Yes
        betaRemote.fuid = 0
        betaRemote.sid = 0

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                                       auto=raeting.AutoMode.once.value,
                                       role=None,
                                       kind=None,
                                       mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                                               auto=raeting.AutoMode.once.value,
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
        self.assertEqual(gamma.stats['joinent_rx_pend'], 2)

        for stack in [gamma, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        gammaRemoteBeta = gamma.remotes.values()[0]
        self.assertIs(gammaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)

        self.assertIs(beta.mutable, True)
        betaRemoteGamma = beta.remotes.values()[0]
        self.assertIs(betaRemoteAlpha, betaRemoteGamma) # same remote on beta side
        self.assertFalse(self.sameAll(betaRemoteGamma, betaRemoteAlphaSave))
        self.assertTrue(self.sameRoleKeys(betaRemoteGamma, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteGamma.name, gamma.name)
        self.assertIs(betaRemoteGamma.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(gamma.local.name)
        self.assertIsNot(remoteData, None)
        self.assertEqual(remoteData['name'], gamma.name) # new name value
        self.assertEqual(remoteData['fuid'], gammaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], gamma.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), gamma.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), gamma.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(gamma.local.role)
        self.assertEqual(roleData['role'], gamma.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), gamma.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), gamma.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), gamma.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), gamma.local.priver.pubhex)

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
                                               auto=raeting.AutoMode.once.value,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertEqual(alpha.stats['joinent_rx_pend'], 2)

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
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['main'], alpha.main) # new main value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                                                       auto=raeting.AutoMode.once.value,
                                                       role=None,
                                                       kind=None,
                                                       mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertEqual(alpha.stats['joinent_rx_pend'], 2)

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
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['kind'], alpha.kind) # new kind value
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendNewRole(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with updated role (F4)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendNewRole.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.AutoMode.once.value,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        self.assertEqual(alphaRemoteBeta.role, 'beta')

        betaRemoteAlpha = beta.remotes.values()[0]
        self.assertEqual(betaRemoteAlpha.role, 'alpha')

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Pending
        beta.keep.pendRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
        # Name: Either
        # Main: Old
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: New
        oldRole = alpha.local.role
        alpha.local.role = 'alpha_new'
        self.assertIs(alpha.local.role, 'alpha_new')
        self.assertNotEqual(alpha.local.role, oldRole)
        alpha.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        # Mutable: Yes
        self.assertIs(beta.mutable, True)

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        self.assertEqual(alpha.stats['joinent_rx_pend'], 2)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 1)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        self.assertIs(beta.mutable, True)
        self.assertFalse(self.sameAll(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertFalse(self.sameRoleKeys(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertEqual(betaRemoteAlpha.role, alpha.local.role)
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role) # new value
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role) # new value
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

        self.assertTrue(beta.mutable)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)
        self.assertEqual(betaRemoteAlpha.role, alpha.local.role) # new role value

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemoteAlpha, remoteData))
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.uid) # value
        self.assertEqual(remoteData['role'], 'alpha_new') # new role value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousPendingPendSameAll(self):
        '''
        Test mutable joiner pend pending vacuous renewal join with same all (G1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousPendingPendSameAll.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.AutoMode.once.value,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        betaRemoteAlpha = beta.remotes.values()[0]

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Pending
        beta.keep.pendRemote(betaRemoteAlpha)
        self.assertEqual(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)
        beta.keep.auto = raeting.AutoMode.never.value
        self.assertEqual(beta.keep.auto, raeting.AutoMode.never.value)
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
        # Sameness: Sameall
        # Mutable: Either
        self.assertIs(beta.mutable, True)

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertEqual(alpha.stats['joinent_rx_pend'], 2)

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
        self.assertEqual(betaRemoteAlpha.fuid, alphaRemoteBeta.nuid)
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.nuid) # new value
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

        self.assertTrue(beta.mutable)
        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 1)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemoteAlpha, remoteData))
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.uid) # value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        # Renew: No
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=False, duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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

        # Simulate: beta already know alpha with ha=('127.0.0.1', 7532)
        #           alpha responds with ha=('127.0.0.1', 7530)
        fakeHa = (alpha.local.ha[0], 7532)
        realHa = (alpha.local.ha[0], alpha.local.ha[1])

        # Vacuous: No
        betaRemoteAlpha = estating.RemoteEstate(stack=beta,
                                                fuid=0,
                                                sid=0, # always 0 for join
                                                ha=realHa,
                                                main=True,
                                                name=alpha.name,
                                                verkey=alpha.local.signer.verhex,
                                                pubkey=alpha.local.priver.pubhex)
        alphaRemoteBeta = estating.RemoteEstate(stack=beta,
                                                fuid=betaRemoteAlpha.nuid,
                                                ha=beta.local.ha,
                                                name=beta.name,
                                                verkey=beta.local.signer.verhex,
                                                pubkey=beta.local.priver.pubhex)
        betaRemoteAlpha.fuid = alphaRemoteBeta.nuid
        alpha.addRemote(alphaRemoteBeta)
        beta.addRemote(betaRemoteAlpha)

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
        self.assertEqual(betaRemoteAlpha.ha, realHa)
        self.assertEqual(alpha.local.ha, realHa)

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        # Test
        console.terse("\n Rejoin with new host address **************\n")
        beta.join(uid=betaRemoteAlpha.uid)
        beta.serviceOneAllTx()
        self.store.advanceStamp(0.05)
        time.sleep(0.05)
        alpha.serviceOneAllRx()
        alpha.serviceOneAllTx() # Join ack
        self.store.advanceStamp(0.05)
        time.sleep(0.05)

        # Change betaRemoteAlpha Rha value to make beta think alpha respond from new HA
        betaRemoteAlpha.ha = fakeHa
        keep = self.copyData(betaRemoteAlpha)
        # Finish join
        self.serviceStacks([beta, alpha])

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertIs(stack.mutable, None)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 1)
        self.assertEqual(len(beta.nameRemotes), 1)
        self.assertIs(betaRemoteAlpha.acceptance, None)
        # Assert betaRemote isn't modified
        self.assertTrue(self.sameAll(betaRemoteAlpha, keep))
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

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        # Test
        console.terse("\nJoin Transaction **************\n")
        beta.join(uid=betaRemote.nuid)
        betaRemote.fuid = fakeFuid
        keep = self.copyData(betaRemote)
        self.serviceStacks([alpha, beta])

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

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        alpha.dumpLocalRole()
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
        alpha.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: No
        self.assertIs(beta.mutable, None)

        # Ensure remote status is None
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)
        # Check beta knows nothing about new role
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha.dumpLocalRole()
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
                self.assertIs(remote.acceptance, raeting.Acceptance.rejected.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousRejectedRejectNewRole(self):
        '''
        Test mutable joiner reject non vacuous join with updated role (I2)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousRejectedRejectNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.AutoMode.never.value

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
        alpha.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        # Check beta knows nothing about new role
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)
        beta.keep.rejectRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=6.0)

        # Action: Reject
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(len(alpha.nameRemotes), 1)
        self.assertEqual(len(beta.remotes), 0)
        self.assertEqual(len(beta.nameRemotes), 0)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.rejected.value)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIs(remoteData, None)
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Rejected
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.rejected.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.AutoMode.always.value)
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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha.dumpLocalRole()
        # Keys: Either
        # Sameness: Not sameall, not same role/keys
        keep = self.copyData(betaRemote)

        # Mutable: Yes
        beta.mutable = True
        # Vacuous: No

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertEqual(roleData['verhex'], None)
        self.assertEqual(roleData['pubhex'], None)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha, beta = self.bootstrapJoinedRemotes(autoMode=raeting.AutoMode.always.value)
        betaRemote = beta.remotes.values()[0]

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        alpha.dumpLocalRole()
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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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

        # Ensure remote status is Accepted
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
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
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid, duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.name, newName)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid, duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.main, alpha.main)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.kind, newKind)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNonVacuousPendingPendNewRha(self):
        '''
        Test mutable joiner pend pending vacuous join with updated host address (M4)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewRha.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.AutoMode.never.value

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
        initHa = (alpha.local.ha[0], alpha.local.ha[1])
        fakeHa = (alpha.local.ha[0], 7532)
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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        console.terse("\nJoin Transaction **************\n")
        beta.join(uid=betaRemote.nuid)
        betaRemote.ha = fakeHa
        # Keep beta values here, before accept. Accept will change it because not same all
        keep = self.copyData(betaRemote)
        self.serviceStacks([alpha, beta], duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.ha, alpha.local.ha)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        console.terse("\nJoin Transaction **************\n")
        beta.join(uid=betaRemote.nuid)
        betaRemote.fuid = fakeFuid
        self.serviceStacks([alpha, beta], duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertTrue(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.fuid, initFuid)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()


    def testJoinerNonVacuousPendingPendNewRole(self):
        '''
        Test mutable joiner pend pending non vacuous join with updated role (M6)
        '''
        console.terse("{0}\n".format(self.testJoinerNonVacuousPendingPendNewRole.__doc__))

        # Mode: Never
        alpha, beta = self.bootstrapStacks()
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(oldRole)
        self.assertEqual(roleData['role'], oldRole)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)
        # Ensure beta knows nothing about the newRole
        roleData = beta.keep.loadRemoteRoleData(newRole)
        self.assertEqual(roleData['role'], newRole)
        self.assertIs(roleData['acceptance'], None)
        self.assertIs(roleData['verhex'], None)
        self.assertIs(roleData['pubhex'], None)

        # Test
        self.join(beta, alpha, deid=betaRemote.nuid, duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertFalse(self.sameAll(betaRemote, keep))
        self.assertFalse(self.sameRoleKeys(betaRemote, keep))
        self.assertEqual(betaRemote.role, newRole)
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

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
        beta.keep.auto = raeting.AutoMode.never.value

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

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemote.nuid, renewal=True, duration=0.50)

        # Action: Pend, Dump
        for stack in [alpha, beta]:
            # self.assertEqual(len(stack.transactions), 1) #b=0
            self.assertEqual(len(beta.remotes), 1)
            self.assertEqual(len(beta.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, None)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
        self.assertTrue(self.sameAll(betaRemote, keep))
        self.assertIs(alphaRemote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemote.acceptance, raeting.Acceptance.pending.value)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(betaRemote, remoteData))
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.pending.value)
        self.assertEqual(ns2b(roleData['verhex']), betaRemote.verfer.keyhex)
        self.assertEqual(ns2b(roleData['pubhex']), betaRemote.pubber.keyhex)

        # Accept the transaction
        console.terse("\nAccept Transaction **************\n")
        beta.keep.acceptRemote(betaRemote)
        self.serviceStacks([alpha, beta], duration=3.0)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(alpha.mutable, None)
        self.assertTrue(beta.mutable)
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
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerVacuousImmutableRefuseRenew(self):
        '''
        Test immutable joiner don't start (refuse) vacuous renew (Z1)
        '''
        console.terse("{0}\n".format(self.testJoinerVacuousImmutableRefuseRenew.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.AutoMode.always.value,
                                               role=None,
                                               kind=None,
                                               mutable=True, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.always.value,
                                             role=None,
                                             kind=None,
                                             mutable=True, )

        self.assertIs(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))

        # Do initial join vacuous join to setup rejoin with renew
        # create remote to join to alpha
        remote = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=alpha.local.ha))
        self.join(beta, alpha, deid=remote.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.joined, True)
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        betaRemoteAlpha = beta.remotes.values()[0]

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        # move alpha stack remote for beta to different uid (nuid) to force renew
        oldUid = alphaRemoteBeta.uid
        alpha.moveRemote(alphaRemoteBeta, alphaRemoteBeta.uid + 1)
        self.assertNotEqual(alphaRemoteBeta.uid, oldUid)
        self.assertIs(alpha.remotes[alphaRemoteBeta.uid], alphaRemoteBeta)

        # Status: Accepted
        # Name: Either
        # Main: Either
        # Kind: Either
        # RHA:  Old
        # Nuid: Old
        # Fuid: Body
        # Leid: Old
        # Reid: 0
        # Role: Either
        # Keys: Either
        # Sameness: Any
        # Mutable: No
        beta.mutable = False

        beta.clearStats()
        alpha.clearStats()

        # Test
        # Renew: Yes
        self.join(beta, alpha, deid=betaRemoteAlpha.uid, duration=0.5)

        # Action: Refuse
        self.assertIn('joiner_rx_renew', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_renew'], 1)
        self.assertIn('join_renew_unallowed', beta.stats)
        self.assertEqual(beta.stats['join_renew_unallowed'], 1)

        self.assertIn('stale_nuid', alpha.stats)
        self.assertEqual(alpha.stats['stale_nuid'], 1)

        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
        self.assertIs(alphaRemoteBeta.joined, True) # Alpha got no response after renew request
        self.assertIs(betaRemoteAlpha.joined, None)
        self.assertIs(beta.mutable, False)
        self.assertTrue(self.sameAll(betaRemoteAlpha, betaRemoteAlphaSave))
        self.assertIs(alphaRemoteBeta.acceptance, raeting.Acceptance.accepted.value)
        self.assertIs(betaRemoteAlpha.acceptance, raeting.Acceptance.accepted.value)

        # Check remote dump with pended data
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        self.assertIsNot(remoteData, None)
        self.assertIs(remoteData['fuid'], oldUid) # renew was refused
        self.assertEqual(remoteData['role'], alpha.local.role)
        self.assertEqual(remoteData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(remoteData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(remoteData['pubhex']), alpha.local.priver.pubhex)

        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
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
                                        auto=raeting.AutoMode.always.value)
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

    def testJoinerAcceptErrorParseInner(self):
        '''
        Test joiner.accept got error on parsing packet inner (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept parseInner error *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set incorrect coat kind
        data['ck'] = -1
        # skip actual joinent.join, it's not needed for test
        joinent.ackAccept()
        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('parsing_inner_error', beta.stats)
        self.assertEqual(beta.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingName(self):
        '''
        Test joiner.accept packet has no name (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing name *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set stack name to None
        alpha.local.name = None
        # Skip actual join, it's not needed for test
        joinent.ackAccept()
        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingMode(self):
        '''
        Test joiner.accept packet has no mode (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingMode.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing mode *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Skip actual join, it's not needed for test
        # ack accept
        if alpha.kind is None:
            alpha.kind = 0
        # Hack: set mode to none
        body = odict([ ('name', alpha.local.name),
                       ('mode', None),
                       ('kind', alpha.kind),
                       ('uid', remote.uid),
                       ('verhex', str(alpha.local.signer.verhex.decode('ISO-8859-1'))),
                       ('pubhex', str(alpha.local.priver.pubhex.decode('ISO-8859-1'))),
                       ('role', alpha.local.role)])
        packet = packeting.TxPacket(stack=alpha,
                                    kind=raeting.PcktKind.response.value,
                                    embody=body,
                                    data=joinent.txData)
        packet.pack()
        console.concise("Joinent {0}. Do Accept of {1} at {2}\n".format(
            alpha.name, alpha.name, alpha.store.stamp))
        joinent.transmit(packet)

        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingKind(self):
        '''
        Test joiner.accept packet has no kind (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing kind *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set stack name to None
        flags = [0, 0, 0, 0, 0, 0, 0, alpha.main] # stack operation mode flags
        operation = packByte(fmt=b'11111111', fields=flags)
        # Skip actual join, it's not needed for test
        # Hack: set mode to none
        body = odict([ ('name', alpha.local.name),
                       ('mode', operation),
                       ('kind', None),
                       ('uid', remote.uid),
                       ('verhex', str(alpha.local.signer.verhex.decode('ISO-8859-1'))),
                       ('pubhex', str(alpha.local.priver.pubhex.decode('ISO-8859-1'))),
                       ('role', alpha.local.role)])
        packet = packeting.TxPacket(stack=alpha,
                                    kind=raeting.PcktKind.response.value,
                                    embody=body,
                                    data=joinent.txData)
        packet.pack()
        console.concise("Joinent {0}. Do Accept of {1} at {2}\n".format(
            alpha.name, alpha.name, alpha.store.stamp))
        joinent.transmit(packet)

        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingUid(self):
        '''
        Test joiner.accept packet has no uid (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingUid.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing uid *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Skip actual join, it's not needed for test
        flags = [0, 0, 0, 0, 0, 0, 0, alpha.main] # stack operation mode flags
        operation = packByte(fmt=b'11111111', fields=flags)
        # Skip actual join, it's not needed for test
        # Hack: set remote uid to None
        body = odict([ ('name', alpha.local.name),
                       ('mode', operation),
                       ('kind', alpha.kind),
                       ('uid', None),
                       ('verhex', str(alpha.local.signer.verhex.decode('ISO-8859-1'))),
                       ('pubhex', str(alpha.local.priver.pubhex.decode('ISO-8859-1'))),
                       ('role', alpha.local.role)])
        packet = packeting.TxPacket(stack=alpha,
                                    kind=raeting.PcktKind.response.value,
                                    embody=body,
                                    data=joinent.txData)
        packet.pack()
        console.concise("Joinent {0}. Do Accept of {1} at {2}\n".format(
            alpha.name, alpha.name, alpha.store.stamp))
        joinent.transmit(packet)

        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingVerhex(self):
        '''
        Test joiner.accept packet has no verhex (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingVerhex.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing verhex *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set stack name to None
        alpha.local.signer.verhex = None
        # Skip actual join, it's not needed for test
        joinent.ackAccept()
        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingPubhex(self):
        '''
        Test joiner.accept packet has no pubhex (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingPubhex.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing pubhex *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set stack name to None
        alpha.local.priver.pubhex = None
        # Skip actual join, it's not needed for test
        joinent.ackAccept()
        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAcceptMissingRole(self):
        '''
        Test joiner.accept packet has no role (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAcceptMissingRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner accept missing role *********\n")
        beta.join()
        self.serviceStacks([beta], duration=0.1)

        # service alpha, reply
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: set stack name to None
        alpha.local.role = None
        # Skip actual join, it's not needed for test
        joinent.ackAccept()
        self.serviceStacks([alpha], duration=0.1)
        self.serviceStacks([beta], duration=0.1)

        self.assertIn('invalid_accept', beta.stats)
        self.assertEqual(beta.stats['invalid_accept'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testVacuousJoinerAcceptConflictNames(self):
        '''
        Test joiner.accept with name conflict (coverage)
        '''
        console.terse("{0}\n".format(self.testVacuousJoinerAcceptConflictNames.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        alphaRemoteBeta = alpha.remotes.values()[0]
        betaRemoteAlpha = beta.remotes.values()[0]

        gammaData = self.createRoadData(base=self.base,
                                        name='gamma',
                                        ha=("", raeting.RAET_TEST_PORT+1),
                                        main=True,
                                        auto=raeting.AutoMode.once.value)
        keeping.clearAllKeep(gammaData['dirpath'])
        gamma = self.createRoadStack(data=gammaData)

        console.terse("\nJoin Transaction **************\n")
        betaRemoteGamma = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                               fuid=0, # vacuous join
                                                               sid=0, # always 0 for join
                                                               ha=gamma.local.ha))
        beta.join(uid=betaRemoteGamma.uid)
        self.serviceStacks([beta, gamma])

        # Test:
        console.terse("\nTest joiner accept name conflict *********\n")
        beta.mutable = True
        alpha.local.name = 'gamma'
        # Vacuous
        betaRemoteAlpha.fuid = 0
        self.join(beta, alpha)

        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testVacuousJoinerAcceptRenameFail(self):
        '''
        Test joiner.accept fail rename remote (coverage)
        '''
        console.terse("{0}\n".format(self.testVacuousJoinerAcceptRenameFail.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        beta.clearStats()
        console.terse("\nTest joiner accept rename fail *********\n")
        beta.mutable = True
        # Rename alpha to beta so:
        # - this would produce name conflict on rename
        # - this wouldn't be covered by pre-checks before call renameRemote
        alpha.local.name = 'beta'
        # Vacuous
        beta.remotes.values()[0].fuid = 0
        self.join(beta, alpha)

        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerPendErrorParseInner(self):
        '''
        Test joiner.pend got error on parsing packet inner (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerPendErrorParseInner.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        alpha.keep.auto = raeting.AutoMode.never.value
        alpha.mutable = True
        alphaRemoteBeta = alpha.remotes.values()[0]
        alpha.keep.pendRemote(alphaRemoteBeta)

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        # service alpha
        alpha.serviceReceives()
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=self, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        remote = alpha.remotes.get(packet.data['de'], None)
        # reply join
        timeout = alpha.JoinentTimeout
        data = odict(hk=alpha.Hk, bk=alpha.Bk)
        joinent = transacting.Joinent(stack=alpha,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        # Hack: break packet inner
        data['ck'] = -1
        # Skip actual join, it's not needed for test
        joinent.ackPend()
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        self.serviceStacks([beta], duration=0.1) # receive response

        # Checks
        self.assertIn('parsing_inner_error', beta.stats)
        self.assertEqual(beta.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNackErrorPack(self):
        '''
        Test joiner.nack packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerNackErrorPack.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        beta.keep.auto = raeting.AutoMode.never.value
        beta.mutable = True
        betaRemoteAlpha = beta.remotes.values()[0]
        beta.keep.rejectRemote(betaRemoteAlpha) # force nack the next join request

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.rejected.value)

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([beta], duration=0.1) # receive response, pend
        raeting.UDP_MAX_PACKET_SIZE = default_size

        # Checks
        self.assertIn('packing_error', beta.stats)
        self.assertEqual(beta.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerNackIncorrectPacketKind(self):
        '''
        Test joiner.nack packet not expected packet type (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerNackIncorrectPacketKind.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        beta.clearStats()
        beta.join()
        beta.transactions[0].nack(kind=raeting.PcktKind.unknown.value)

        # Checks
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAckPendErrorPack(self):
        '''
        Test joiner.ackPend packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAckPendErrorPack.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        beta.keep.auto = raeting.AutoMode.never.value
        beta.mutable = True
        betaRemoteAlpha = beta.remotes.values()[0]
        beta.keep.pendRemote(betaRemoteAlpha)

        # Ensure remote status is Pending
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([beta], duration=0.1) # receive response, pend
        raeting.UDP_MAX_PACKET_SIZE = default_size

        # Checks
        self.assertIn('packing_error', beta.stats)
        self.assertEqual(beta.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAckAcceptErrorPack(self):
        '''
        Test joiner.ackAccept packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAckAcceptErrorPack.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([beta], duration=0.1) # receive response, pend
        raeting.UDP_MAX_PACKET_SIZE = default_size

        # Checks
        self.assertIn('packing_error', beta.stats)
        self.assertEqual(beta.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerAckAcceptCascade(self):
        '''
        Test joiner.ackAccept cascade (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerAckAcceptCascade.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        # Test
        beta.join(cascade=True)
        self.serviceStacks([alpha, beta])

        # Checks
        for stack in [alpha, beta]:
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined, True)
            self.assertTrue(remote.allowed, True)
            self.assertTrue(remote.alived, True)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerRefuseErrorParseInner(self):
        '''
        Test joiner.refuse error parse inner (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerRefuseErrorParseInner.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.keep.auto = raeting.AutoMode.never.value
        alpha.keep.pendRemote(alpha.remotes.values()[0])

        # Test
        beta.join(cascade=True)
        self.serviceStacks([beta], duration=0.1) # process, send join
        self.serviceStacks([alpha], duration=0.1) # process join, add pend transaction
        # Do malformed nack from alpha
        alpha.transactions[0].txData['ck'] = -1
        self.store.advanceStamp(stacking.RoadStack.JoinerTimeout) # set timeout expiresd
        self.serviceStacks([alpha], duration=0.1) # handle timeout, send nack
        self.store.advanceStamp(0.05)
        time.sleep(0.05)
        self.serviceStacks([beta], duration=0.1) # receive and handle

        # Checks
        self.assertIn('parsing_inner_error', beta.stats)
        self.assertEqual(beta.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerRejectErrorParseInner(self):
        '''
        Test joiner.reject error parse inner (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerRejectErrorParseInner.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.keep.auto = raeting.AutoMode.never.value
        alpha.keep.pendRemote(alpha.remotes.values()[0])

        # Test
        beta.join(cascade=True)
        self.serviceStacks([beta], duration=0.1) # process, send join
        self.serviceStacks([alpha], duration=0.1) # process join, add pend transaction
        # Do malformed nack from alpha
        alpha.transactions[0].txData['ck'] = -1
        alpha.transactions[0].nack(kind=raeting.PcktKind.reject.value)
        self.serviceStacks([alpha], duration=0.1) # process join, add pend transaction
        self.serviceStacks([beta], duration=0.1) # receive and handle

        # Checks
        self.assertIn('parsing_inner_error', beta.stats)
        self.assertEqual(beta.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerClearJoinentNotClear(self):
        '''
        Test joiner join after Joiner loses its remotes but Joinent did not. (coverage)
        This is a coverage test to verify common use case
        '''
        console.terse("{0}\n".format(self.testJoinerClearJoinentNotClear.__doc__))

        alpha, alphaData = self.bootstrapStack(name='alpha',
                                               ha=("", raeting.RAET_PORT),
                                               main=True,
                                               auto=raeting.AutoMode.once.value,
                                               role=None,
                                               kind=None,
                                               mutable=False, )

        self.assertIs(alpha.local.role, 'alpha')
        self.assertEqual(alpha.ha, ('0.0.0.0', raeting.RAET_PORT))
        self.assertEqual(alpha.local.ha, ('127.0.0.1', raeting.RAET_PORT))

        beta, betaData = self.bootstrapStack(name='beta',
                                             ha=("", raeting.RAET_TEST_PORT),
                                             main=None,
                                             auto=raeting.AutoMode.once.value,
                                             role=None,
                                             kind=None,
                                             mutable=False, )

        self.assertIs(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))

        # Do initial join vacuous join to setup losss
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
                self.assertIs(remote.acceptance, raeting.Acceptance.accepted.value)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)

        alphaRemoteBeta = alpha.remotes.values()[0]
        betaRemoteAlpha = beta.remotes.values()[0]

        # save the current state of beta stack remote for alpha
        betaRemoteAlphaSave = self.copyData(betaRemoteAlpha)

        self.assertEqual(beta.puid, 2)
        data = beta.keep.loadLocalData()

        # now lose all beta remotes and reboot beta stack
        for remote in beta.remotes.values():
            beta.removeRemote(remote, clear=True)

        # Close down beta stack
        beta.server.close()

        # reboot beta stack
        beta = self.createRoadStack(data=betaData)
        self.assertIs(beta.main, betaData['main'])
        self.assertIs(beta.keep.auto, betaData['auto'])
        self.assertIs(beta.kind, betaData['kind'])
        self.assertIs(beta.mutable, betaData['mutable'])
        self.assertEqual(beta.local.role, 'beta')
        self.assertEqual(beta.ha, ('0.0.0.0', raeting.RAET_TEST_PORT))
        self.assertEqual(beta.local.ha, ('127.0.0.1', raeting.RAET_TEST_PORT))
        self.assertEqual(len(beta.remotes), 0)

        self.assertEqual(beta.keep.dirpath, betaData['dirpath'])
        data = beta.keep.loadRemoteRoleData(role= alpha.local.role)
        self.assertEqual(data['role'], alpha.local.role)
        self.assertEqual(data['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(data['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(data['pubhex']), alpha.local.priver.pubhex)
        self.assertEqual(beta.keep.auto, raeting.AutoMode.once.value)
        self.assertEqual(beta.puid, 2)

        # create remote to join to alpha
        newBetaRemoteAlpha = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                    fuid=0, # vacuous join
                                                    sid=0, # always 0 for join
                                                    ha=alpha.local.ha))

        # will reject since nuid changed for newBetaRemoteAlphs
        self.assertNotEqual(newBetaRemoteAlpha.nuid, betaRemoteAlpha.nuid)
        self.assertIs(beta.mutable, False)
        self.assertIs(alpha.mutable, False)
        self.join(beta, alpha, deid=newBetaRemoteAlpha.uid)

        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 1)
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertIs(remote.allowed, None)
        self.assertIs(remote.alived, None)
        self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

        self.assertEqual(len(beta.transactions), 0)
        self.assertEqual(len(beta.remotes), 0)
        self.assertIn('joiner_rx_reject', beta.stats)
        self.assertEqual(beta.stats['joiner_rx_reject'], 1)
        self.assertIn('joiner_transaction_failure', beta.stats)
        self.assertEqual(beta.stats['joiner_transaction_failure'], 1)
        self.assertEqual(beta.puid, 3)

        # redo after resetting beta.puid to 1
        beta.puid = 1
        self.assertEqual(beta.puid, 1)
        newBetaRemoteAlpha = beta.addRemote(estating.RemoteEstate(stack=beta,
                                                            fuid=0, # vacuous join
                                                            sid=0, # always 0 for join
                                                            ha=alpha.local.ha))
        self.assertEqual(beta.puid, 2)
        self.assertIs(beta.mutable, False)
        self.assertIs(alpha.mutable, False)
        self.join(beta, alpha, deid=newBetaRemoteAlpha.uid)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            for remote in stack.remotes.values():
                self.assertTrue(remote.joined)
                self.assertIs(remote.allowed, None)
                self.assertIs(remote.alived, None)
                self.assertEqual(remote.acceptance, raeting.Acceptance.accepted.value)

        self.assertTrue(self.sameAll(newBetaRemoteAlpha, betaRemoteAlphaSave))
        self.assertTrue(self.sameRoleKeys(newBetaRemoteAlpha, betaRemoteAlphaSave))
        self.assertEqual(newBetaRemoteAlpha.nuid, alphaRemoteBeta.fuid)
        self.assertEqual(newBetaRemoteAlpha.fuid, alphaRemoteBeta.nuid)

        self.assertIn('join_initiate_complete', beta.stats)
        self.assertEqual(beta.stats['join_initiate_complete'], 1)

        self.assertIn('join_correspond_complete', alpha.stats)
        self.assertEqual(alpha.stats['join_correspond_complete'], 2)

        # Check remote dump
        remoteData = beta.keep.loadRemoteData(alpha.local.name)
        remoteData['ha'] = tuple(remoteData['ha'])
        self.assertTrue(self.sameAll(newBetaRemoteAlpha, remoteData))
        self.assertIs(remoteData['fuid'], alphaRemoteBeta.uid) # value
        # Check role/keys dump
        roleData = beta.keep.loadRemoteRoleData(alpha.local.role)
        self.assertEqual(roleData['role'], alpha.local.role)
        self.assertEqual(roleData['acceptance'], raeting.Acceptance.accepted.value)
        self.assertEqual(ns2b(roleData['verhex']), alpha.local.signer.verhex)
        self.assertEqual(ns2b(roleData['pubhex']), alpha.local.priver.pubhex)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerJoinInProcess(self):
        '''
        Test joiner.join do nothing if there is a join in process. (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerJoinInProcess.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]

        # Test 1: another joiner transaction in process
        console.terse("\nTest joiner in process *********\n")
        beta.join()
        self.assertEqual(len(beta.transactions), 1) # 1 transaction is created
        beta.join()
        self.assertEqual(len(beta.transactions), 1) # nothing is created
        self.serviceStacks([beta, alpha])

        # Check join is done
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(beta.remotes.values()[0].joined)
        self.assertTrue(alpha.remotes.values()[0].joined)

        # Test 2: another joinent transaction in process
        console.terse("\nTest joinent in process *********\n")
        alpha.join()
        self.serviceStacks([alpha]) # send
        self.serviceStacks([beta], duration=0.1) # receive
        self.assertEqual(len(beta.transactions), 1) # 1 transaction is created
        self.assertEqual(len(beta.txes), 0) # Ensure there is no tx packets
        beta.join()
        self.assertEqual(len(beta.transactions), 1) # no new transaction is created
        self.assertEqual(len(beta.txes), 0) # Ensure no packet added
        self.serviceStacks([beta, alpha])

        # Check join is done
        self.assertEqual(len(beta.transactions), 0)
        self.assertTrue(beta.remotes.values()[0].joined)
        self.assertTrue(alpha.remotes.values()[0].joined)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerJoinInvalidKind(self):
        '''
        Test joiner.join do nothing if stack kind is invalid (<0 or >255) (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerJoinInvalidKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]

        # Test:
        console.terse("\nTest joiner join invalid kind *********\n")
        beta.kind = -1
        beta.join()
        self.assertEqual(len(beta.transactions), 0) # no transaction is created
        self.assertEqual(len(beta.txes), 0) # Ensure no packet was sent
        beta.kind = 256
        beta.join()
        self.assertEqual(len(beta.transactions), 0) # nothing is created
        self.assertEqual(len(beta.txes), 0) # Ensure no packet was sent

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerJoinPackError(self):
        '''
        Test joiner.join handles pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerJoinPackError.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]

        # Test:
        self.assertEqual(len(beta.txes), 0)
        beta.clearStats()
        console.terse("\nTest joiner join pack error *********\n")
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        beta.join() # will fail with packing error
        raeting.UDP_MAX_PACKET_SIZE = default_size

        self.assertEqual(len(beta.transactions), 0) # transaction is removed
        self.assertIn('packing_error', beta.stats) # transaction failed
        self.assertEqual(beta.stats['packing_error'], 1)
        self.assertEqual(len(beta.txes), 0) # Ensure no packet was sent

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerProcessNoPacketTimeout(self):
        '''
        Test joiner.process timeout when no tx packets (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinerProcessNoPacketTimeout.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        console.terse("\nTest joiner process timeout when no tx packet *********\n")
        beta.join() # create join transaction
        self.assertEqual(len(beta.transactions), 1) # ensure there is only one transaction
        beta.transactions[0].txPacket = None # make txPacket None
        self.store.advanceStamp(stacking.RoadStack.JoinerTimeout) # set timeout expiresd

        self.assertEqual(len(beta.transactions), 1)
        self.serviceStacks([beta]) # Process
        self.assertEqual(len(beta.transactions), 0)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinErrorParseInner(self):
        '''
        Test joinent.join handles parseInner error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        beta.clearStats()
        console.terse("\nTest joinent join parseInner error *********\n")
        # join beta to alpha with broken packet inner
        remote = beta.retrieveRemote()
        self.assertIsNotNone(remote)
        timeout = beta.JoinerTimeout
        data = odict(hk=beta.Hk, bk=beta.Bk)
        joiner = transacting.Joiner(stack=beta,
                                    remote=remote,
                                    timeout=timeout,
                                    txData=data)
        data['ck'] = -1
        joiner.join()
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('parsing_inner_error', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['parsing_inner_error'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        # redo the broken packet then drop it
        self.serviceStacks([alpha, beta], duration=10.0)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
        self.assertTrue(alpha.remotes.values()[0].joined)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingName(self):
        '''
        Test joinent.join handles body data missing required name field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingName.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]

        # Test: no name
        alpha.clearStats()
        console.terse("\nTest joinent join missing name *********\n")
        orig_name = beta.local.name
        beta.local.name = None
        beta.join()
        beta.local.name = orig_name
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingVerhex(self):
        '''
        Test joinent.join handles body data missing required verhex field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingVerhex.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]
        # Test: no verhex
        alpha.clearStats()
        console.terse("\nTest joinent join missing verhex *********\n")
        orig_verhex = beta.local.signer.verhex
        beta.local.signer.verhex = None
        beta.join()
        beta.local.signer.verhex = orig_verhex
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingPubhex(self):
        '''
        Test joinent.join handles body data missing required pubhex field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingPubhex.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]
        # Test: no verhex
        alpha.clearStats()
        console.terse("\nTest joinent join missing pubhex *********\n")
        orig_pubhex = beta.local.priver.pubhex
        beta.local.priver.pubhex = None
        beta.join()
        beta.local.priver.pubhex = orig_pubhex
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingRole(self):
        '''
        Test joinent.join handles body data missing required role field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingRole.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]
        # Test: no verhex
        alpha.clearStats()
        console.terse("\nTest joinent join missing role *********\n")
        orig_role = beta.local.role
        beta.local.role = None
        beta.join()
        beta.local.role = orig_role
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingMode(self):
        '''
        Test joinent.join handles body data missing required mode field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingMode.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        betaRemoteAlpha = beta.remotes.values()[0]
        # Test: no verhex
        alpha.clearStats()
        console.terse("\nTest joinent join missing mode *********\n")
        orig_role = beta.local.role
        beta.local.role = None
        # stack join
        remote = beta.retrieveRemote()
        self.assertIsNotNone(remote)
        joiner = transacting.Joiner(stack=beta,
                                    remote=remote,
                                    timeout=beta.JoinerTimeout,
                                    txData=odict(hk=beta.Hk, bk=beta.Bk))
        # joiner join
        remote.joined = None
        if beta.kind is None:
            beta.kind = 0
        # Hack: Set mode to None here
        body = odict([('name', beta.local.name),
                      ('mode', None),
                      ('kind', beta.kind),
                      ('verhex', str(beta.local.signer.verhex.decode('ISO-8859-1'))),
                      ('pubhex', str(beta.local.priver.pubhex.decode('ISO-8859-1'))),
                      ('role', beta.local.role)])
        packet = packeting.TxPacket(stack=beta,
                                    kind=raeting.PcktKind.request.value,
                                    embody=body,
                                    data=joiner.txData)
        packet.pack()
        console.concise("Joiner {0}. Do Join with {1} at {2}\n".format(
            beta.name, beta.name, beta.store.stamp))
        joiner.transmit(packet)
        joiner.add(index=joiner.txPacket.index)
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinMissingKind(self):
        '''
        Test joinent.join handles body data missing required kind field (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinMissingKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.clearStats()
        console.terse("\nTest joinent join missing kind *********\n")
        # stack join
        remote = beta.retrieveRemote()
        self.assertIsNotNone(remote)
        joiner = transacting.Joiner(stack=beta,
                                    remote=remote,
                                    timeout=beta.JoinerTimeout,
                                    txData=odict(hk=beta.Hk, bk=beta.Bk))
        # joiner join
        remote.joined = None
        flags = [0, 0, 0, 0, 0, 0, 0, beta.main] # stack operation mode flags
        operation = packByte(fmt=b'11111111', fields=flags)
        # Hack: Set kind to None here
        body = odict([('name', beta.local.name),
                      ('mode', operation),
                      ('kind', None),
                      ('verhex', str(beta.local.signer.verhex.decode('ISO-8859-1'))),
                      ('pubhex', str(beta.local.priver.pubhex.decode('ISO-8859-1'))),
                      ('role', beta.local.role)])
        packet = packeting.TxPacket(stack=beta,
                                    kind=raeting.PcktKind.request.value,
                                    embody=body,
                                    data=joiner.txData)
        packet.pack()
        console.concise("Joiner {0}. Do Join with {1} at {2}\n".format(
            beta.name, beta.name, beta.store.stamp))
        joiner.transmit(packet)
        joiner.add(index=joiner.txPacket.index)
        self.serviceStacks([beta], duration=0.1)
        self.serviceStacks([alpha], duration=0.1)
        self.assertEqual(len(alpha.transactions), 0) # transaction wasn't added
        self.assertIn('invalid_join', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['invalid_join'], 1)
        self.assertEqual(len(beta.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertTrue(remote.joined) # didn't touched

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinDuplicateJoinent(self):
        '''
        Test joinent.join handles duplications (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinDuplicateJoinent.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        console.terse("\nTest joinent join duplicate joinent *********\n")
        beta.join() # join beta to alpha
        self.assertEqual(len(beta.transactions), 1)
        beta.remotes.values()[0].transactions.values()[0].remove() # drop first transaction
        beta.join() # join beta to alpha again

        self.serviceStacks([beta], duration=0.1) # send 2 transactions
        self.serviceStacks([alpha], duration=0.1) # receive and handle 2 transactions
        self.assertEqual(len(alpha.transactions), 1) # the only first request is added to alpha
        self.assertEqual(len(beta.transactions), 1) # the only 2nd transaction is on beta
        self.assertIn('redundant_join_attempt', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['redundant_join_attempt'], 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertIsNone(remote.joined)

        # redo the broken transactions then drop them
        self.serviceStacks([alpha, beta], duration=10.0)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertIsNone(stack.remotes.values()[0].joined)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testVacuousJoinentJoinDuplicateNonVacuousJoiner(self):
        '''
        Test joinent.join handles duplications (coverage)
        Vacuous joinent found existing non-vacuous joiner
        Nack itself
        '''
        console.terse("{0}\n".format(self.testVacuousJoinentJoinDuplicateNonVacuousJoiner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        console.terse("\nTest vacuous joinent join duplicate non vacuous joiner *********\n")
        # Initiate 2 transactions
        orig_fuid = alpha.remotes.values()[0].fuid
        alpha.remotes.values()[0].fuid = 0
        alpha.join() # vacuous join alpha to beta
        alpha.remotes.values()[0].fuid = orig_fuid
        self.assertEqual(len(alpha.transactions), 1)
        # This step is incorrect from the logic viewpoint but good enough for coverage test.
        alpha.transactions[0].vacuous = False # imitate non-vacuous
        beta.remotes.values()[0].fuid = 0
        beta.join() # vacuous join beta to alpha
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 1)

        self.serviceStacks([beta], duration=0.1) # send beta join to alpha
        self.serviceStacks([alpha], duration=0.1) # receive and handle beta join to alpha
                                                # send alpha join to beta and the response
        self.assertEqual(len(alpha.transactions), 1) # the only first request is added to alpha
        self.assertEqual(len(beta.transactions), 1) # the only 2nd transaction is on beta
        self.assertIn('redundant_join_attempt', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['redundant_join_attempt'], 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertIsNone(remote.joined)

        # redo the broken transactions then drop them
        self.serviceStacks([alpha, beta], duration=10.0)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testNonVacuousJoinentJoinDuplicateVacuousJoiner(self):
        '''
        Test joinent.join handles duplications (coverage)
        Non-vacuous joinent found existing vacuous joiner
        Nack joiner, continue itself
        '''
        console.terse("{0}\n".format(self.testNonVacuousJoinentJoinDuplicateVacuousJoiner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        alpha.mutable = True
        console.terse("\nTest non vacuous joinent join duplicate vacuous joiner *********\n")
        # Initiate 2 transactions
        alpha.remotes.values()[0].fuid = 0
        alpha.join() # vacuous join alpha to beta
        self.assertEqual(len(alpha.transactions), 1)

        beta.join() # non-vacuous join beta to alpha
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 1)

        self.serviceStacks([beta], duration=0.1) # send beta join to alpha
        self.serviceStacks([alpha], duration=0.1) # receive and handle beta join to alpha
                                                # send alpha join to beta and the response
        self.assertEqual(len(alpha.transactions), 1) # joiner removed, joinent refused as changing immutable
        self.assertEqual(len(beta.transactions), 1) # the only 2nd transaction is on beta
        self.assertIn('joiner_transaction_failure', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joiner_transaction_failure'], 1)
        self.assertEqual(len(alpha.remotes), 1) # remote wasn't removed
        remote = alpha.remotes.values()[0]
        self.assertIsNone(remote.joined)

        # redo the broken transactions then drop them
        self.serviceStacks([alpha, beta], duration=10.0)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertTrue(stack.remotes.values()[0].joined)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinDuplicateJoinerMatchNames(self):
        '''
        Test joinent.join handles duplications (coverage)
        Non-vacuous joinent found existing non-vacuous joiner
        Joinent name < joiner name
        Nack joinent transaction
        Joinent name >= joiner name
        Nack joiner transaction
        '''
        console.terse("{0}\n".format(self.testJoinentJoinDuplicateJoinerMatchNames.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        console.terse("\nTest joinent join duplicate joiner local name less than remote *********\n")
        # Initiate 2 transactions
        alpha.join() # non-vacuous join alpha to beta
        beta.join() # non-vacuous join beta to alpha
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 1)

        # redo the broken transactions then drop them
        self.serviceStacks([alpha, beta], duration=10.0)
        self.assertIn('redundant_join_attempt', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['redundant_join_attempt'], 1)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertTrue(stack.remotes.values()[0].joined)

        # Test:
        alpha.clearStats()
        console.terse("\nTest joinent join duplicate joiner remote name less than local *********\n")
        alpha.name = 'gamma' # 'gamma' > 'beta'
        beta.mutable = True
        # Initiate 2 transactions
        alpha.join() # non-vacuous join alpha to beta
        beta.join() # non-vacuous join beta to alpha
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(beta.transactions), 1)

        # redo the broken transactions then drop them
        self.serviceStacks([alpha, beta], duration=10.0)
        self.assertIn('joiner_transaction_failure', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joiner_transaction_failure'], 1)
        for stack in [alpha, beta]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertTrue(stack.remotes.values()[0].joined)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testVacuousEphemeralJoinentJoinIncorrectRemoteId(self):
        '''
        Test vacuous ephemeral joinent.join with remote id don't match (coverage)
        '''
        console.terse("{0}\n".format(self.testVacuousEphemeralJoinentJoinIncorrectRemoteId.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test conditions:
        # 1. Vacuous
        beta.remotes.values()[0].fuid = 0
        # 2. Ephemeral
        alpha.removeRemote(alpha.remotes.values()[0])
        # 3. remote.fuid != packet data eid
        # Would be hacked in the test.

        # Test:
        alpha.clearStats()
        console.terse("\nTest remote id don't match *********\n")
        # Initiate transaction
        beta.join() # vacuous join beta to alpha
        self.serviceStacks([beta], duration=0.1)

        # Service alpha receive and call join
        alpha.serviceReceives()
        # service rxes
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=alpha, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        fuid = packet.data['se'] + 1 # hack fuid
        remote = estating.RemoteEstate(stack=alpha,
                                       fuid=fuid,
                                       sid=packet.data['si'],
                                       ha=(packet.data['sh'], packet.data['sp']))
        alpha.correspond(packet, remote)
        alpha.process()

        self.assertIn('joinent_transaction_failure', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testNonVacuousJoinentJoinNoDestinationIdMatch(self):
        '''
        Test non vacuous joinent.join with remote id absent in stack (coverage)
        '''
        console.terse("{0}\n".format(self.testNonVacuousJoinentJoinNoDestinationIdMatch.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        console.terse("\nTest absent remote id *********\n")
        # Initiate transaction
        beta.join() # non-vacuous join beta to alpha
        self.serviceStacks([beta], duration=0.1)

        # Service alpha receive and call join
        alpha.serviceReceives()
        # service rxes
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=alpha, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        # hack: create new remote that doesn't the same as on in stack.remotes[de/leid]
        remote = estating.RemoteEstate(stack=alpha,
                                       fuid=packet.data['se'],
                                       sid=packet.data['si'],
                                       ha=(packet.data['sh'], packet.data['sp']))
        alpha.correspond(packet, remote)
        alpha.process()

        self.assertIn('joinent_transaction_failure', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentJoinErrorAddRemote(self):
        '''
        Test joinent.join got error on add remote (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentJoinErrorAddRemote.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        alpha.clearStats()
        console.terse("\nTest remote id don't match *********\n")
        # Initiate non vacuous transaction
        beta.join() # vacuous join beta to alpha
        self.serviceStacks([beta], duration=0.1)

        # Service alpha receive and call join
        alpha.serviceReceives()
        # service rxes
        raw, sa = alpha.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(alpha.name, raw))
        packet = packeting.RxPacket(stack=alpha, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        # process rx
        # Hack: change stack uid
        # Joinent will not find remote by uid in the stack and will try to re-add.
        # Add will fail by name unique check
        remote = alpha.remotes.values()[0]
        remote.uid += 1
        self.assertNotIn(remote.uid, alpha.remotes)
        alpha.correspond(packet, remote)
        alpha.process()

        self.assertIn('joinent_transaction_failure', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentReceiveRefuse(self):
        '''
        Test joinent.join got error on add remote (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentReceiveRefuse.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Pend transaction
        alpha.keep.auto = raeting.AutoMode.never.value
        alpha.keep.pendRemote(alpha.remotes.values()[0])

        alpha.clearStats()
        # Test:
        console.terse("\nTest joinent recieve refuse *********\n")
        # Initiate non vacuous transaction
        beta.join() # initiate transaction
        beta.transactions[0].nack(kind=raeting.PcktKind.refuse.value)

        self.serviceStacks([beta], duration=0.1) # send 2 packets
        # receive 2 packets on alpha
        # 1. Create transaction, pend join
        # 2. Handle refuse
        self.serviceStacks([alpha], duration=0.1)

        self.assertIn('joinent_rx_refuse', alpha.stats) # Error handled
        self.assertEqual(alpha.stats['joinent_rx_refuse'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentAckPendErrorPack(self):
        '''
        Test joinent.ackPend packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentAckPendErrorPack.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        # Pend beta on alpha
        alpha.keep.auto = raeting.AutoMode.never.value
        alpha.keep.pendRemote(alpha.remotes.values()[0])

        # Ensure remote status is Pending
        roleData = alpha.keep.loadRemoteRoleData(beta.local.role)
        self.assertEqual(roleData['role'], beta.local.role)
        self.assertIs(roleData['acceptance'], raeting.Acceptance.pending.value)

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        raeting.UDP_MAX_PACKET_SIZE = default_size

        # Checks
        self.assertIn('packing_error', alpha.stats)
        self.assertEqual(alpha.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentAckAcceptErrorPack(self):
        '''
        Test joinent.ackAccept packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentAckAcceptErrorPack.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        # Test
        beta.join()
        self.serviceStacks([beta], duration=0.1) # send join
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([alpha], duration=0.1) # handle and respond
        raeting.UDP_MAX_PACKET_SIZE = default_size

        # Checks
        self.assertIn('packing_error', alpha.stats)
        self.assertEqual(alpha.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentAckAcceptIncorrectKind(self):
        '''
        Test joinent.ackAccept incorrect kind (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentAckAcceptIncorrectKind.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.clearStats()
        console.terse("\nTest joinent ackAccept missing kind *********\n")
        # stack join
        alpha.kind = -1
        self.join(beta, alpha, duration=10.0)
        self.assertIn('joinent_transaction_failure', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentPendErrorParseInner(self):
        '''
        Test joinent.pend handles parseInner error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentPendErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()
        beta.keep.auto = raeting.AutoMode.never.value
        # Test:
        beta.clearStats()
        console.terse("\nTest joinent pend parseInner error *********\n")
        beta.join() # Join
        self.serviceStacks([beta], duration=0.1) # beta send join
        self.serviceStacks([alpha], duration=0.1) # alpha read responce, send ack

        # Pend from beta to alpha with broken data
        beta.serviceReceives()
        raw, sa = beta.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(beta.name, raw))
        packet = packeting.RxPacket(stack=beta, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        self.assertEqual(len(beta.transactions), 1)
        joiner = beta.transactions[0]
        joiner.rxPacket = packet
        # Break packet Inner
        joiner.txData['ck'] = -1
        joiner.ackPend() # Pend
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # read join, handle

        self.assertIn('parsing_inner_error', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentCompleteErrorParseInner(self):
        '''
        Test joinent.complete handles parseInner error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentCompleteErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        beta.clearStats()
        console.terse("\nTest joinent complete parseInner error *********\n")
        beta.join() # Join
        self.serviceStacks([beta], duration=0.1) # beta send join
        self.serviceStacks([alpha], duration=0.1) # alpha read responce, send ack

        # Complete from beta to alpha with broken data
        beta.serviceReceives()
        raw, sa = beta.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(beta.name, raw))
        packet = packeting.RxPacket(stack=beta, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        self.assertEqual(len(beta.transactions), 1)
        joiner = beta.transactions[0]
        joiner.rxPacket = packet
        # Break packet Inner
        joiner.txData['ck'] = -1
        joiner.ackAccept() # Complete
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # read join, handle

        self.assertIn('parsing_inner_error', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentRejectErrorParseInner(self):
        '''
        Test joinent.reject handles parseInner error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentRejectErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        beta.clearStats()
        console.terse("\nTest joinent reject parseInner error *********\n")
        beta.join() # Join
        self.serviceStacks([beta], duration=0.1) # beta send join
        self.serviceStacks([alpha], duration=0.1) # alpha read responce, send ack

        # Complete from beta to alpha with broken data
        beta.serviceReceives()
        raw, sa = beta.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(beta.name, raw))
        packet = packeting.RxPacket(stack=beta, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        self.assertEqual(len(beta.transactions), 1)
        joiner = beta.transactions[0]
        joiner.rxPacket = packet
        # Break packet Inner
        joiner.txData['ck'] = -1
        joiner.nack(kind=raeting.PcktKind.reject.value) # Reject
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # read join, handle

        self.assertIn('parsing_inner_error', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentRefuseErrorParseInner(self):
        '''
        Test joinent.refuse handles parseInner error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentRefuseErrorParseInner.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test:
        beta.clearStats()
        console.terse("\nTest joinent refuse parseInner error *********\n")
        beta.join() # Join
        self.serviceStacks([beta], duration=0.1) # beta send join
        self.serviceStacks([alpha], duration=0.1) # alpha read responce, send ack

        # Complete from beta to alpha with broken data
        beta.serviceReceives()
        raw, sa = beta.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(beta.name, raw))
        packet = packeting.RxPacket(stack=beta, packed=raw)
        packet.parseOuter()
        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        self.assertEqual(len(beta.transactions), 1)
        joiner = beta.transactions[0]
        joiner.rxPacket = packet
        # Break packet Inner
        joiner.txData['ck'] = -1
        joiner.nack(kind=raeting.PcktKind.refuse.value) # Refuse
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.1) # read join, handle

        self.assertIn('parsing_inner_error', alpha.stats) # Error occured
        self.assertEqual(alpha.stats['parsing_inner_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNackErrorPack(self):
        '''
        Test joinent.nack handles packet.pack error (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentNackErrorPack.__doc__))

        # Status: Accepted (auto accept keys)
        # Mode: Never, Once, Always
        alpha, beta = self.bootstrapJoinedRemotes()

        # Test goal; Nack from joinent side
        # Test conditions: vacuous join to non-main joinent
        alpha.remotes.values()[0].fuid = 0 # vacuous

        # Test:
        alpha.clearStats()
        console.terse("\nTest joinent nack packet pack error *********\n")
        alpha.join() # Join
        self.serviceStacks([alpha], duration=0.1) # alpha send join
        # Update max packet size to make packet.pack fail
        default_size = raeting.UDP_MAX_PACKET_SIZE
        raeting.UDP_MAX_PACKET_SIZE = 10 # packet.pack() will throw PacketError
        self.serviceStacks([beta], duration=0.1) # beta read responce, nack
        raeting.UDP_MAX_PACKET_SIZE = default_size

        self.assertIn('packing_error', beta.stats)
        self.assertEqual(beta.stats['packing_error'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNackRenew(self):
        '''
        Test joiner.nack with 'renew' kind (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentNackRenew.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.clearStats()
        beta.join()
        self.serviceStacks([beta], duration=0.1) # request join
        self.serviceStacks([alpha], duration=0.1) # handle, responce
        self.assertEqual(len(alpha.transactions), 1)
        alpha.transactions[0].nack(kind=raeting.PcktKind.renew.value)

        # Checks
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentNackUnknown(self):
        '''
        Test joiner.nack with 'unknown' kind (cover 'else' case) (coverage)
        '''
        console.terse("{0}\n".format(self.testJoinentNackUnknown.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()

        alpha.clearStats()
        beta.join()
        self.serviceStacks([beta], duration=0.1) # request join
        self.serviceStacks([alpha], duration=0.1) # handle, responce
        self.assertEqual(len(alpha.transactions), 1)
        alpha.transactions[0].nack(kind=raeting.PcktKind.unknown.value)

        # Checks
        self.assertIn('joinent_transaction_failure', alpha.stats)
        self.assertEqual(alpha.stats['joinent_transaction_failure'], 1)

        for stack in [alpha, beta]:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstJoinRequestDropped(self):
        '''
        Test network dropped first join request (redo timeout)
        '''
        console.terse("{0}\n".format(self.testFirstJoinRequestDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent didn't received first packet, redo timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # send alive
        self.flushReceives(alpha)
        self.serviceStacks(stacks, duration=2.0) # timeout, redo, alive

        self.assertIn('joiner_tx_join_redo', beta.stats)
        self.assertEqual(beta.stats['joiner_tx_join_redo'], 1) # 1 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllJoinRequestsDropped(self):
        '''
        Test network dropped all join requests (transaction timeout)
        '''
        console.terse("{0}\n".format(self.testAllJoinRequestsDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent didn't received any request, transaction timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacksDropRx(stacks, drop=[alpha], duration=10.0) # redo timeout, transaction timeout, drop

        self.assertIn('joiner_tx_join_redo', beta.stats)
        self.assertEqual(beta.stats['joiner_tx_join_redo'], 2) # 2 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIsNone(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstJoinAcceptDropped(self):
        '''
        Test network dropped first join ack response (redo timeout)
        '''
        console.terse("{0}\n".format(self.testFirstJoinAcceptDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner didn't received first accept, redo timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # beta: send join
        self.serviceStacks([alpha], duration=0.1) # alpha: process join, send ack
        self.flushReceives(beta)
        self.serviceStacks(stacks, duration=2.0) # alpha: timeout, redo ack

        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 1) # 1 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllJoinAcceptDropped(self):
        '''
        Test network dropped all join accepts (transaction timeout)
        '''
        console.terse("{0}\n".format(self.testAllJoinAcceptDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner didn't received any accept, transaction timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacksDropRx(stacks, drop=[beta], duration=10.0) # both ends timed out, drop transactions

        self.assertIn('joiner_tx_join_redo', beta.stats)
        self.assertEqual(beta.stats['joiner_tx_join_redo'], 2) # 2 redo
        self.assertIn('duplicate_join_attempt', alpha.stats)
        self.assertEqual(alpha.stats['duplicate_join_attempt'], 2) # 2 redo join received
        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 5) # 5 redo accept
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIsNone(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstJoinAckAcceptDropped(self):
        '''
        Test network dropped first join ack accept response (redo timeout, stale refuse)
        '''
        console.terse("{0}\n".format(self.testFirstJoinAckAcceptDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent didn't received ack accept, redo timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # beta: send join
        self.serviceStacks([alpha], duration=0.1) # alpha: process join, send ack
        self.serviceStacks([beta], duration=0.1) # beta: send ack accept, remove
        self.flushReceives(alpha)
        self.serviceStacks(stacks, duration=2.0) # alpha: timeout, redo ack; beta: stale, refuse
        self.serviceStacks(stacks, duration=2.0) # alpha: timeout, redo ack; beta: stale, refuse

        self.assertIn('stale_correspondent_nack', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_nack'], 1) # 1 stale refuse
        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 1) # 1 redo
        self.assertIn('joinent_rx_nack', alpha.stats)
        self.assertEqual(alpha.stats['joinent_rx_nack'], 1) # 1 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
        self.assertTrue(beta.remotes.values()[0].joined)
        self.assertIsNone(alpha.remotes.values()[0].joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllJoinAckAcceptDropped(self):
        '''
        Test network dropped all join ack accepts (transaction timeout)
        '''
        console.terse("{0}\n".format(self.testAllJoinAckAcceptDropped.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent didn't received any ack accept, transaction timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # beta: send join
        self.serviceStacks([alpha], duration=0.1) # alpha: process join, send ack
        self.serviceStacks([beta], duration=0.1) # beta: send ack accept, remove
        self.serviceStacksDropRx(stacks, drop=[alpha], duration=10.0)
        # alpha: redo timeout, transaction timeout, drop
        # beta: nack refuse since transaction is already removed

        self.assertIn('stale_correspondent_nack', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_nack'], 5) # 5 redo received
        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 5) # 5 redo accept
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
        self.assertTrue(beta.remotes.values()[0].joined)
        self.assertIsNone(alpha.remotes.values()[0].joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstJoinRequestDelayed(self):
        '''
        Test network delayed request so ack has been received after redo was sent.
        '''
        console.terse("{0}\n".format(self.testFirstJoinRequestDelayed.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent received both request and redo *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=1.5) # send join and redo
        self.serviceStacks(stacks) # service delayed messages

        self.assertIn('joiner_tx_join_redo', beta.stats)
        self.assertEqual(beta.stats['joiner_tx_join_redo'], 1) # 1 redo
        self.assertIn('duplicate_join_attempt', alpha.stats)
        self.assertEqual(alpha.stats['duplicate_join_attempt'], 1) # 1 duplicate on alpha
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllJoinRequestsDelayed(self):
        '''
        Test network delayed all join requests (joiner receive response after transaction dropped)
        '''
        console.terse("{0}\n".format(self.testAllJoinRequestsDelayed.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner received ack after transaction timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=10.0) # redo timeout, packet timeout, drop
        self.serviceStacks(stacks) # alpha: 1 ack, 2 drop; beta: stale nack; alpha: refuse
        for stack in stacks:
            self.assertEqual(len(stack.txes), 0) # ensure both stacks done

        self.assertIn('joiner_tx_join_redo', beta.stats)
        self.assertEqual(beta.stats['joiner_tx_join_redo'], 2) # 2 redo
        self.assertIn('stale_correspondent_attempt', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_attempt'], 1) # 1 stale attempt
        self.assertIn('stale_correspondent_nack', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_nack'], 1) # 1 stale nack answer


        self.assertIn('duplicate_join_attempt', alpha.stats)
        self.assertEqual(alpha.stats['duplicate_join_attempt'], 2) # 2 redo
        self.assertIn('joinent_rx_nack', alpha.stats)
        self.assertEqual(alpha.stats['joinent_rx_nack'], 1) # 1 stale nack on other
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIsNone(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testFirstJoinAcceptDelayed(self):
        '''
        Test network delayed response so it has been received after redo.
        '''
        console.terse("{0}\n".format(self.testFirstJoinAcceptDelayed.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner received both accept and redo *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=0.2) # send ack and redo
        self.serviceStacks(stacks) # service delayed messages

        self.assertIn('stale_correspondent_nack', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_nack'], 1) # 1 stale refuse
        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 1) # 1 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testAllJoinAcceptsDelayed(self):
        '''
        Test network delayed all join accepts (joinent receive ack accept after transaction dropped)
        '''
        console.terse("{0}\n".format(self.testAllJoinAcceptsDelayed.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent received ack accept after transaction timeout *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # send join
        self.serviceStacks([alpha], duration=10.0) # alpha: redo, remove
        self.serviceStacks(stacks)
        for stack in stacks:
            self.assertEqual(len(stack.txes), 0) # ensure both stacks done

        self.assertIn('stale_correspondent_nack', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_nack'], 5) # 5 stale nack answer
        self.assertIn('joinent_tx_accept_redo', alpha.stats)
        self.assertEqual(alpha.stats['joinent_tx_accept_redo'], 5) # 5 redo
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
        self.assertIsNone(alpha.remotes.values()[0].joined)
        self.assertTrue(beta.remotes.values()[0].joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinRequestDuplicated(self):
        '''
        Test network duplicated join request (joiner ack both, joinent drop second)
        '''
        console.terse("{0}\n".format(self.testJoinRequestDuplicated.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner received the same request twice *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # send join
        self.dupReceives(alpha)
        self.serviceStacks(stacks) # beta: 1 req; alpha: 1 ack, 1 drop; beta: ack

        self.assertIn('duplicate_join_attempt', alpha.stats)
        self.assertEqual(alpha.stats['duplicate_join_attempt'], 1) # 1 dup
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinAcceptDuplicated(self):
        '''
        Test network duplicated join ack response (stale nack the second one)
        '''
        console.terse("{0}\n".format(self.testJoinAcceptDuplicated.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joiner received response twice *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # Send join
        self.serviceStacks([alpha], duration=0.1) # Send ack
        self.dupReceives(beta) # duplicate response
        self.serviceStacks([beta, alpha]) # beta: 1st accept, 2nd stale nack

        self.assertIn('stale_correspondent_attempt', beta.stats)
        self.assertEqual(beta.stats['stale_correspondent_attempt'], 1) # 1 stale attempt (dup)
        self.assertIn('stale_packet', alpha.stats)
        self.assertEqual(alpha.stats['stale_packet'], 1) # 1 stale nack on alpha (dup)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinAckAcceptDuplicated(self):
        '''
        Test network duplicated join ack accept (stale drop the second one)
        '''
        console.terse("{0}\n".format(self.testJoinAckAcceptDuplicated.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nTest joinent received ack accept twice *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta], duration=0.1) # Send join
        self.serviceStacks([alpha], duration=0.1) # Send ack
        self.serviceStacks([beta], duration=0.1) # Send ack accept
        self.dupReceives(alpha) # duplicate response
        self.serviceStacks(stacks) # alpha: 1st accept, 2nd stale drop

        self.assertIn('stale_packet', alpha.stats)
        self.assertEqual(alpha.stats['stale_packet'], 1) # 1 stale drop on alpha (dup)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerRestartNothingTransmitted(self):
        '''
        Test joiner dies before the message is transmitted (die)
        '''
        console.terse("{0}\n".format(self.testJoinerRestartNothingTransmitted.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nSend join request *********\n")
        beta.join() # join from beta to alpha

        console.terse("\nRestart beta *********\n")
        # shutdown beta
        beta.server.close()
        beta.clearAllKeeps()

        beta, betaData = self.bootstrapStack(name='beta', ha=('', raeting.RAET_TEST_PORT), auto=raeting.AutoMode.once.value)
        stacks = [alpha, beta]

        self.serviceStacks(stacks)

        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(alpha.remotes.values()[0].joined, None)
        self.assertEqual(len(beta.transactions), 0)
        self.assertEqual(len(beta.remotes), 0)

        console.terse("\nJoin beta again *********\n")
        alpha.keep.auto = raeting.AutoMode.always.value
        alpha.mutable = True
        self.join(beta, alpha)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerRestartRequestTransmitted(self):
        '''
        Test joiner dies after a message transmitted (die)
        '''
        console.terse("{0}\n".format(self.testJoinerRestartRequestTransmitted.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nSend join request *********\n")
        beta.join() # join from beta to alpha
        self.serviceStacks([beta]) # transmit

        console.terse("\nRestart beta *********\n")
        # shutdown beta
        beta.server.close()
        beta.clearAllKeeps()

        beta, betaData = self.bootstrapStack(name='beta', ha=('', raeting.RAET_TEST_PORT), auto=raeting.AutoMode.once.value)
        stacks = [alpha, beta]

        self.serviceStacks(stacks)

        # transaction still alive on alpha
        self.assertEqual(len(alpha.transactions), 1)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertEqual(alpha.remotes.values()[0].joined, None)
        self.assertEqual(len(beta.transactions), 0)
        self.assertEqual(len(beta.remotes), 0)

        console.terse("\nJoin beta again *********\n")
        alpha.keep.auto = raeting.AutoMode.always.value
        alpha.mutable = True
        self.join(beta, alpha)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinerRestartAckAcceptTransmitted(self):
        '''
        Test joiner dies after join done (die)
        '''
        console.terse("{0}\n".format(self.testJoinerRestartRequestTransmitted.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nSend join request *********\n")
        beta.join()  # join from beta to alpha
        self.serviceStacks([beta])  # transmit request
        self.serviceStacks([alpha])  # ack
        self.serviceStacks([beta])  # ack accept

        console.terse("\nRestart beta *********\n")
        # shutdown beta
        beta.server.close()
        beta.clearAllKeeps()

        beta, betaData = self.bootstrapStack(name='beta', ha=('', raeting.RAET_TEST_PORT), auto=raeting.AutoMode.once.value)
        stacks = [alpha, beta]

        self.serviceStacks(stacks)

        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 1)
        self.assertTrue(alpha.remotes.values()[0].joined)
        self.assertEqual(len(beta.transactions), 0)
        self.assertEqual(len(beta.remotes), 0)

        console.terse("\nJoin beta again *********\n")
        alpha.keep.auto = raeting.AutoMode.always.value
        alpha.mutable = True
        self.join(beta, alpha)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentRestartBeforeAck(self):
        '''
        Test joinent dies before send ack (die)
        '''
        console.terse("{0}\n".format(self.testJoinentRestartBeforeAck.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nSend join request *********\n")
        beta.join()  # join from beta to alpha
        self.serviceStacks([beta])  # transmit request
        alpha.serviceAllRx()  # receive and handle, not send

        console.terse("\nRestart alpha *********\n")
        # shutdown alpha
        alpha.server.close()
        alpha.clearAllKeeps()

        alpha, alphaData = self.bootstrapStack(name='alpha', ha=('', raeting.RAET_PORT),
                                               auto=raeting.AutoMode.always.value, mutable=True, main=True)
        stacks = [alpha, beta]
        beta.keep.auto = raeting.AutoMode.always.value
        beta.mutable = True

        self.serviceStacks(stacks)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
            stack.server.close()
            stack.clearAllKeeps()

    def testJoinentRestartAckSent(self):
        '''
        Test joinent dies after ack sent (die)
        '''
        console.terse("{0}\n".format(self.testJoinentRestartAckSent.__doc__))

        alpha, beta = self.bootstrapJoinedRemotes()
        stacks = [alpha, beta]
        for stack in stacks:
            stack.remotes.values()[0].joined = None # force unjoin both
            stack.clearStats()

        console.terse("\nSend join request *********\n")
        beta.join()  # join from beta to alpha
        self.serviceStacks([beta])  # transmit request
        self.serviceStacks([alpha])  # receive and handle, send ack

        console.terse("\nRestart alpha *********\n")
        # shutdown alpha
        alpha.server.close()
        alpha.clearAllKeeps()

        alpha, alphaData = self.bootstrapStack(name='alpha', ha=('', raeting.RAET_PORT),
                                               auto=raeting.AutoMode.always.value, mutable=True, main=True)
        stacks = [alpha, beta]
        beta.keep.auto = raeting.AutoMode.always.value
        beta.mutable = True

        self.serviceStacks(stacks)

        self.assertEqual(len(alpha.transactions), 0)
        self.assertEqual(len(alpha.remotes), 0)
        self.assertEqual(len(beta.transactions), 0)
        self.assertEqual(len(beta.remotes), 1)
        self.assertTrue(beta.remotes.values()[0].joined)

        console.terse("\nJoin beta again *********\n")
        alpha.keep.auto = raeting.AutoMode.always.value
        alpha.mutable = True
        self.join(beta, alpha)

        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertTrue(remote.joined)

        for stack in stacks:
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
                'testJoinJointVacuuousMain',
                'testJoinJointVacuuousMainWithMain',
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
                'testJoinerVacuousRejectedRejectSameRoleKeys',
                'testJoinerVacuousRejectedNorenewRejectSameAll',
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
                'testJoinerNonVacuousPendingPendNewRole',
                'testJoinerNonVacuousPendingPendSameAll',
                'testJoinerVacuousImmutableRefuseRenew',
                'testJoinentNonMainRejectJoin',
                'testJoinentJoinRenameRemoteFail',
                'testJoinentJoinRejectNameConflict',
                'testJoinerAcceptRejectNameConflict',
                'testJoinerAcceptRejectRenameFail',
                'testJoinerAcceptErrorParseInner',
                'testJoinerAcceptMissingName',
                'testJoinerAcceptMissingMode',
                'testJoinerAcceptMissingKind',
                'testJoinerAcceptMissingUid',
                'testJoinerAcceptMissingVerhex',
                'testJoinerAcceptMissingPubhex',
                'testJoinerAcceptMissingRole',
                'testVacuousJoinerAcceptConflictNames',
                'testVacuousJoinerAcceptRenameFail',
                'testJoinerPendErrorParseInner',
                'testJoinerNackErrorPack',
                'testJoinerNackIncorrectPacketKind',
                'testJoinerAckPendErrorPack',
                'testJoinerAckAcceptErrorPack',
                'testJoinerAckAcceptCascade',
                'testJoinerRefuseErrorParseInner',
                'testJoinerRejectErrorParseInner',
                'testJoinerClearJoinentNotClear',
                'testJoinerJoinInProcess',
                'testJoinerJoinInvalidKind',
                'testJoinerJoinPackError',
                'testJoinerProcessNoPacketTimeout',
                'testJoinentJoinErrorParseInner',
                'testJoinentJoinMissingName',
                'testJoinentJoinMissingVerhex',
                'testJoinentJoinMissingPubhex',
                'testJoinentJoinMissingRole',
                'testJoinentJoinMissingMode',
                'testJoinentJoinMissingKind',
                'testJoinentJoinDuplicateJoinent',
                'testVacuousJoinentJoinDuplicateNonVacuousJoiner',
                'testNonVacuousJoinentJoinDuplicateVacuousJoiner',
                'testJoinentJoinDuplicateJoinerMatchNames',
                'testVacuousEphemeralJoinentJoinIncorrectRemoteId',
                'testNonVacuousJoinentJoinNoDestinationIdMatch',
                'testJoinentJoinErrorAddRemote',
                'testJoinentReceiveRefuse',
                'testJoinentAckPendErrorPack',
                'testJoinentAckAcceptErrorPack',
                'testJoinentAckAcceptIncorrectKind',
                'testJoinentPendErrorParseInner',
                'testJoinentCompleteErrorParseInner',
                'testJoinentRejectErrorParseInner',
                'testJoinentRefuseErrorParseInner',
                'testJoinentNackErrorPack',
                'testJoinentNackRenew',
                'testJoinentNackUnknown',
                'testFirstJoinRequestDropped',
                'testAllJoinRequestsDropped',
                'testFirstJoinAcceptDropped',
                'testAllJoinAcceptDropped',
                'testFirstJoinAckAcceptDropped',
                'testAllJoinAckAcceptDropped',
                'testFirstJoinRequestDelayed',
                'testAllJoinRequestsDelayed',
                'testFirstJoinAcceptDelayed',
                'testAllJoinAcceptsDelayed',
                'testJoinRequestDuplicated',
                'testJoinAcceptDuplicated',
                'testJoinAckAcceptDuplicated',
                'testJoinerRestartNothingTransmitted',
                'testJoinerRestartRequestTransmitted',
                'testJoinerRestartAckAcceptTransmitted',
                'testJoinentRestartBeforeAck',
                'testJoinentRestartAckSent',
            ]

    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2,  failfast=True).run(suite)

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

    #runOne('testAllJoinAcceptDropped')
    #runOne('testJoinerAcceptMissingMode')
