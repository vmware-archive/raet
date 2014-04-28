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

    def tearDown(self):
        pass

    def createRoadData(self, name='main', base='/tmp/raet/'):
        '''
        Creates odict and populates with data to setup road stack
        {
            name: stack name local estate name
            dirpath: dirpath for keep files
            sighex: signing key
            verhex: verify key
            prihex: private key
            pubhex: public key
        }
        '''
        data = odict()
        data['name'] = name
        data['dirpath'] = os.path.join(base, 'road', 'keep', name)
        signer = nacling.Signer()
        data['sighex'] = signer.keyhex
        data['verhex'] = signer.verhex
        privateer = nacling.Privateer()
        data['prihex'] = privateer.keyhex
        data['pubhex'] = privateer.pubhex

        return data

    def createRoadStack(self, data, eid=0, main=None, auto=None, ha=None):
        '''
        Clears any old keep data from data['dirpath']
        Creates stack and local estate from data with
        local estate.eid = eid
        stack.main = main
        stack.auto = auto
        stack.name = data['name']
        local estate.name = data['name']
        local estate.ha = ha

        returns stack

        '''
        local = estating.LocalEstate(eid=eid,
                                     name=data['name'],
                                     ha=ha,
                                     sigkey=data['sighex'],
                                     prikey=data['prihex'],)

        stack = stacking.RoadStack(name=data['name'],
                                   local=local,
                                   auto=auto,
                                   main=main,
                                   dirpath=data['dirpath'],
                                   store=self.store)

        return stack

    def join(self, other, main, duration=1.0):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        other.join()
        self.service(main, other, duration=duration)

    def allow(self, other, main, duration=1.0):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        other.allow()
        self.service(main, other, duration=duration)

    def message(self, main,  other, mains, others, duration=2.0):
        '''
        Utility to send messages both ways
        '''
        for msg in mains:
            main.transmit(msg)
        for msg in others:
            other.transmit(msg)

        self.service(main, other, duration=duration)

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

    def testBasic(self):
        '''
        Basic keep setup for stack keep and safe persistence load and dump
        '''
        console.terse("{0}\n".format(self.testBasic.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        stack = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                stack.name, stack.keep.dirpath, stack.safe.dirpath))
        self.assertEqual(stack.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(stack.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(stack.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        # test round trip
        stack.clearLocal()
        stack.clearRemoteKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        localKeepData = stack.keep.loadLocalData()
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        validLocalKeepData =  odict([
                                 ('eid', 1),
                                 ('name', 'main'),
                                 ('main', True),
                                 ('host', '0.0.0.0'),
                                 ('port', 7530),
                                 ('sid', 0),
                               ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        self.assertDictEqual(remoteKeepData, {})

        localSafeData = stack.safe.loadLocalData()
        console.terse("Local safe data = '{0}'\n".format(localSafeData))
        validLocalSafeData = odict([
                                ('eid', 1),
                                ('name', 'main'),
                                ('sighex', data['sighex']),
                                ('prihex', data['prihex']),
                              ])
        self.assertDictEqual(localSafeData, validLocalSafeData)

        remoteSafeData = stack.safe.loadAllRemoteData()
        console.terse("Remote safe data = '{0}'\n".format(remoteSafeData))
        self.assertDictEqual(remoteSafeData, {})

        # test round trip with stack methods
        stack.loadLocal()
        localKeepData = odict([
                                ('eid', stack.local.eid),
                                ('name', stack.local.name),
                                ('main', stack.local.main),
                                ('host', stack.local.host),
                                ('port', stack.local.port),
                                ('sid', stack.local.sid),
                              ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        localSafeData = odict([
                                ('eid', stack.local.eid),
                                ('name', stack.local.name),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        self.assertDictEqual(localSafeData, validLocalSafeData)

        stack.removeAllRemotes()
        stack.loadRemotes()
        self.assertDictEqual(stack.remotes, {})


        # round trip with non empty remote data
        other1Data = self.createRoadData(name='other1', base=base)
        stack.addRemote(estating.RemoteEstate(eid=2,
                                              name=other1Data['name'],
                                              ha=('127.0.0.1', 7531),
                                              verkey=other1Data['verhex'],
                                              pubkey=other1Data['pubhex'],))

        other2Data = self.createRoadData(name='other2', base=base)
        stack.addRemote(estating.RemoteEstate(eid=3,
                                              name=other2Data['name'],
                                              ha=('127.0.0.1', 7532),
                                              verkey=other2Data['verhex'],
                                              pubkey=other2Data['pubhex'],))

        stack.dumpRemotes()
        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        validRemoteKeepData = {'2':
                            {'eid': 2,
                             'name': other1Data['name'],
                             'host': '127.0.0.1',
                             'port': 7531,
                             'sid': 0,
                             'rsid': 0},
                         '3':
                            {'eid': 3,
                             'name': other2Data['name'],
                             'host': '127.0.0.1',
                             'port': 7532,
                             'sid': 0,
                             'rsid': 0}
                        }
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        remoteSafeData = stack.safe.loadAllRemoteData()
        console.terse("Remote safe data = '{0}'\n".format(remoteSafeData))
        validRemoteSafeData = {'2':
                            {'eid': 2,
                             'name': other1Data['name'],
                             'acceptance': None,
                             'verhex': other1Data['verhex'],
                             'pubhex': other1Data['pubhex']},
                         '3':
                            {'eid': 3,
                             'name': other2Data['name'],
                             'acceptance': None,
                             'verhex': other2Data['verhex'],
                             'pubhex': other2Data['pubhex']}
                        }
        self.assertDictEqual(remoteSafeData, validRemoteSafeData)

        # stack method

        #convert string uid keys into int uid keys
        temp = validRemoteKeepData
        validRemoteKeepData = odict()
        for uid in temp:
            validRemoteKeepData[int(uid)] = temp[uid]

        temp = validRemoteSafeData
        validRemoteSafeData = odict()
        for uid in temp:
            validRemoteSafeData[int(uid)] = temp[uid]

        stack.removeAllRemotes()
        stack.loadRemotes()
        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.uid] = odict([
                                                ('eid', remote.eid),
                                                ('name', remote.name),
                                                ('host', remote.host),
                                                ('port', remote.port),
                                                ('sid', remote.sid),
                                                ('rsid', remote.rsid),
                                               ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        remoteSafeData = odict()
        for remote in stack.remotes.values():
            remoteSafeData[remote.uid] = odict([
                                                ('eid', remote.eid),
                                                ('name', remote.name),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                               ])
        self.assertDictEqual(remoteSafeData, validRemoteSafeData)

        stack.server.close()

        # bootstrap new stack from stored keep and safe data
        stack = stacking.RoadStack(name=data['name'],
                                   auto=auto,
                                   dirpath=data['dirpath'],
                                   store=self.store)

        localKeepData = odict([
                                ('eid', stack.local.eid),
                                ('name', stack.local.name),
                                ('main', stack.local.main),
                                ('host', stack.local.host),
                                ('port', stack.local.port),
                                ('sid', stack.local.sid),
                              ])
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        self.assertDictEqual(localKeepData, validLocalKeepData)

        localSafeData = odict([
                                ('eid', stack.local.eid),
                                ('name', stack.local.name),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        console.terse("Local safe data = '{0}'\n".format(localSafeData))
        self.assertDictEqual(localSafeData, validLocalSafeData)

        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.uid] = odict([
                                                ('eid', remote.eid),
                                                ('name', remote.name),
                                                ('host', remote.host),
                                                ('port', remote.port),
                                                ('sid', remote.sid),
                                                ('rsid', remote.rsid),
                                               ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        remoteSafeData = odict()
        for remote in stack.remotes.values():
            remoteSafeData[remote.uid] = odict([
                                                ('eid', remote.eid),
                                                ('name', remote.name),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                               ])
        self.assertDictEqual(remoteSafeData, validRemoteSafeData)

        stack.server.close()
        stack.clearLocal()
        stack.clearRemoteKeeps()

    def testAltDirpath(self):
        '''
        Keep fallback path function when don't have permissions to directory
        fallback to ~user/.raet
        '''
        console.terse("{0}\n".format(self.testAltDirpath.__doc__))
        base = '/var/cache/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        stack = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                stack.name, stack.keep.dirpath, stack.safe.dirpath))
        self.assertTrue(".raet/keep/main" in stack.keep.dirpath)
        self.assertTrue(".raet/keep/main" in stack.safe.dirpath)
        self.assertEqual(stack.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        # test can write
        stack.clearLocal()
        stack.clearRemoteKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        stack.server.close()
        stack.clearLocal()
        stack.clearRemoteKeeps()

    def testPending(self):
        '''
        Test pending behavior when not auto accept by main
        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        base = '/tmp/raet/'
        auto = False #do not auto accept
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertFalse(main.safe.auto)

        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 1)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, raeting.acceptances.pending)
        self.assertEqual(len(other.transactions), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, None)

        for remote in main.remotes.values():
            if remote.acceptance == raeting.acceptances.pending:
                main.safe.acceptRemote(remote)

        self.service(main, other, duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)


        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

    def testPendingSavedKeep(self):
        '''
        Test pending behavior when not auto accept by main with saved keep data

        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        base = '/tmp/raet/'
        auto = False #do not auto accept
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        savedOtherData = data
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertFalse(main.safe.auto)

        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 1)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, raeting.acceptances.pending)
        self.assertEqual(len(other.transactions), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, None)

        #kill the transactions
        for index in main.transactions:
            main.removeTransaction(index)
        for index in other.transactions:
            other.removeTransaction(index)

        for remote in main.remotes.values():
            if remote.acceptance == raeting.acceptances.pending:
                main.safe.acceptRemote(remote)

        #now reload from keep data
        main.removeAllRemotes()
        main.loadRemotes()
        main.loadLocal()

        other.removeAllRemotes()
        other.loadRemotes()
        other.loadLocal()

        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.join(other, main, 5.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now change name of other to see if can still join with same ha
        other.local.name = "whowho"
        self.join(other, main, 5.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # now change ha to see if can still join
        other.server.close()
        data = savedOtherData
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", 7532))

        self.join(other, main, 5.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)


        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()



    def testLostOtherKeep(self):
        '''
        Test rejection when other attempts to join with keys that are different
        from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertTrue(main.safe.auto)

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now forget the other data
        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

        # reload with new data
        data = self.createRoadData(name='other', base=base)
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept enabled
        self.assertTrue(main.safe.auto)
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # now repeate with auto accept off on main
        # now forget the other data again
        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

        # reload with new data
        data = self.createRoadData(name='other', base=base)
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.safe.auto = False # turn off auto accept
        self.assertIs(main.safe.auto, False)
        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # unlost other remote still there
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) #unlost other remote still accepted
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None) # new other rejected by main so not joined
        self.assertEqual(remote.acceptance, None) # new other never been accepted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed) # unlost other still there
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 1) #didn't abort since duration too short
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0)
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

    def testLostOtherKeepLocal(self):
        '''
        Test rejection when other attempts to join with local keys that are different
        from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostOtherKeepLocal.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertTrue(main.safe.auto)

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now forget the other data local only to simulate just changing other keys
        other.server.close()
        other.clearLocal()
        #other.clearRemoteKeeps()

        # reload with new data
        data = self.createRoadData(name='other', base=base)
        savedOtherData = data
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept enabled
        self.assertTrue(main.safe.auto)
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # now repeate with auto accept off on main
        # now forget the other data again
        other.server.close()
        other.clearLocal()
        #other.clearRemoteKeeps()

        # reload with new data
        data = self.createRoadData(name='other', base=base)
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.safe.auto = False # turn off auto accept
        self.assertIs(main.safe.auto, False)
        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined) # unlost other remote still there
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) #unlost other remote still accepted
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None) # new other rejected by main so not joined
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # old remote was accepted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed) # unlost other still there
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertEqual(remote.allowed, None) # new other not joined so aborted allow

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 1) #didn't abort since duration too short
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0)
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        for index in main.transactions:
            main.removeTransaction(index)

        for index in other.transactions:
            other.removeTransaction(index)

        # now reload original local other data and see if works
        other.server.close()
        other.clearLocal()
        data = savedOtherData
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.safe.auto = False # turn off auto accept
        self.assertIs(main.safe.auto, False)
        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # so try to send messages
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

    def testLostMainKeep(self):
        '''
        Test rejection when other attempts to join to main where main's keys are
        different from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostMainKeep.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        savedMainData = data
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now forget the main data only to simulate main changing all data
        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        # reload with new data
        data = self.createRoadData(name='main', base=base)
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None) # joiner will reject so main never finishes
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined) # no lost main remote still there
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # no lost main still accepted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.allowed, None)
        self.assertEqual(len(other.transactions), 1) # not timed out yet so still there
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        for index in other.transactions:
            other.removeTransaction(index)

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        # now restore original main keys to see if works
        #now forget the new main data
        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        # reload with original saved data
        auto = True
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # so try to send messages should succeed
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg)
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

    def testLostMainKeepLocal(self):
        '''
        Test rejection when other attempts to join to main where main's local keys are
        different from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostMainKeepLocal.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        savedMainData = data
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now forget the main local data only to simulate main changing keys
        main.server.close()
        main.clearLocal()
        #main.clearRemoteKeeps()

        # reload with new local data and saved remote data
        auto = True
        data = self.createRoadData(name='main', base=base)
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None) # joiner will reject so main never finishes
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined) # no lost main remote still there
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # no lost main still accepted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.allowed, None)
        self.assertEqual(len(other.transactions), 1) # not timed out yet so still there
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        for index in other.transactions:
            other.removeTransaction(index)

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        # now restore original main keys to see if works
        #now forget the new main data
        main.server.close()
        main.clearLocal()
        #main.clearRemoteKeeps()

        # reload with original saved data
        auto = True
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # so try to send messages should succeed
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg)
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()


    def testLostBothKeepLocal(self):
        '''
        Test when both other and main lose local data to simulate both changing
        their local keys but keeping their remote data
        '''
        console.terse("{0}\n".format(self.testLostMainKeepLocal.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
        savedMainData = data
        keeping.clearAllKeepSafe(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other', base=base)
        savedOtherData = data
        keeping.clearAllKeepSafe(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now forget the local local data only to simulate main changing keys
        main.server.close()
        main.clearLocal()
        #main.clearRemoteKeeps()
        other.server.close()
        other.clearLocal()
        #other.clearRemoteKeeps()

        # reload with new local data and saved remote data
        auto = True
        data = self.createRoadData(name='main', base=base)
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        data = self.createRoadData(name='other', base=base)
        other = self.createRoadStack(data=data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                        other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        remote = other.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None) # joiner will reject so main never finishes
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None) # Joiner rejects main
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # no lost main still accepted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.allowed, None)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        # now restore original local keys to see if works
        #now forget the new main data
        main.server.close()
        main.clearLocal()
        other.server.close()
        other.clearLocal()

        # reload with original saved data
        auto = True
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     eid=1,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        data = savedOtherData
        other = self.createRoadStack(data=data,
                                    eid=0,
                                    main=None,
                                    auto=None,
                                    ha=("", raeting.RAET_TEST_PORT))

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                main.name, main.keep.dirpath, main.safe.dirpath))
        self.assertEqual(main.keep.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.safe.dirpath, '/tmp/raet/road/keep/main')
        self.assertEqual(main.local.ha, ("0.0.0.0", raeting.RAET_PORT))
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        console.terse("{0} keep dirpath = {1} safe dirpath = {0}\n".format(
                        other.name, other.keep.dirpath, other.safe.dirpath))
        self.assertEqual(other.keep.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.safe.dirpath, '/tmp/raet/road/keep/other')
        self.assertEqual(other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        remote = other.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # so try to send messages should succeed
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg)
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()


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
    names = ['testBasic',
             'testAltDirpath',
             'testPending',
             'testPendingSavedKeep',
             'testLostOtherKeep',
             'testLostOtherKeepLocal',
             'testLostMainKeep',
             'testLostMainKeepLocal',
             'testLostBothKeepLocal',]

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

    #runOne('testPendingSavedKeep')

