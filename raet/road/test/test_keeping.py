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

    def createRoadStack(self, data, eid=0, main=False, auto=False, ha=None):
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
        keeping.clearAllKeepSafe(data['dirpath'])

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

    def testBasic(self):
        '''
        Basic keep setup for stack keep and safe persistence load and dump
        '''
        console.terse("{0}\n".format(self.testBasic.__doc__))
        base = '/tmp/raet/'
        auto = True
        data = self.createRoadData(name='main', base=base)
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


def runSome():
    """ Unittest runner """
    tests =  []
    names = []
    names.append('testBasic')
    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    runAll() #run all unittests

    #runSome()#only run some
