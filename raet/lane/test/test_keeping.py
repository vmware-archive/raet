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
from raet.lane import yarding, keeping, stacking


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

    def createLaneData(self, name, yid, base, lanename, localname=''):
        '''
        Creates odict and populates with data to setup lane stack
        {
            name: stack name
            dirpath: dirpath for keep files
            lanename: name of yard
        }
        '''
        data = odict()
        data['name'] = name
        data['yid'] = yid
        data['basedirpath'] = os.path.join(base, 'lane', 'keep')
        data['dirpath'] = os.path.join(data['basedirpath'], name)
        data['lanename'] = lanename
        data['localname'] = localname or name

        return data

    def createLaneStack(self, data, main=None):
        '''
        Creates stack and local yard from data
        returns stack

        '''
        stack = stacking.LaneStack(name=data['name'],
                                   yid=data['yid'],
                                   localname=data['localname'],
                                   main=main,
                                   lanename=data['lanename'],
                                   basedirpath=data['basedirpath'],
                                   sockdirpath=data['dirpath'])

        return stack

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
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def serviceStack(self, stack, duration=1.0):
        '''
        Utility method to service queues for one stack. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            stack.serviceAll()
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
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def testBasic(self):
        '''
        Basic keep setup for stack keep persistence load and dump
        '''
        console.terse("{0}\n".format(self.testBasic.__doc__))
        mainData = self.createLaneData(name='main', yid=1, base=self.base, lanename='apple')
        keeping.clearAllKeep(mainData['dirpath'])
        stack = self.createLaneStack(data=mainData, main=True)

        console.terse("{0} keep dirpath = {1}\n".format(stack.name, stack.keep.dirpath))
        self.assertTrue(stack.keep.dirpath.endswith('/lane/keep/main'))
        self.assertTrue(stack.keep.localdirpath.endswith('/lane/keep/main/local'))
        self.assertTrue(stack.keep.remotedirpath.endswith('/lane/keep/main/remote'))
        self.assertTrue(stack.keep.localfilepath.endswith('/lane/keep/main/local/yard.json'))
        self.assertTrue(stack.local.ha.endswith('/lane/keep/main/apple.main.uxd'))

        # test round trip
        stack.clearLocal()
        stack.clearRemoteKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        localKeepData = stack.keep.loadLocalData()
        console.terse("Local keep data = '{0}'\n".format(localKeepData))

        validLocalKeepData = odict([
                                ('uid', 1),
                                ('name', 'main'),
                                ('ha', stack.local.ha),
                                ('main', True),
                                ('sid', 0),
                                ('lanename', 'apple'),
                                ('stack', 'main'),
                                ('nyid', 1),
                                ('accept', True)
                              ])

        self.assertDictEqual(localKeepData, validLocalKeepData)
        self.assertTrue(localKeepData['ha'].endswith('lane/keep/main/apple.main.uxd'))

        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        self.assertDictEqual(remoteKeepData, {})

        # test round trip with stack methods
        stack.loadLocal()
        localKeepData = odict([
                                ('uid', stack.local.uid),
                                ('name', stack.local.name),
                                ('ha', stack.local.ha),
                                ('main', stack.local.main),
                                ('sid', stack.local.sid),
                                ('lanename', stack.local.lanename),
                                ('stack', stack.name),
                                ('nyid', stack.nyid),
                                ('accept', stack.accept),
                              ])
        self.assertDictEqual(localKeepData, validLocalKeepData)
        self.assertTrue(stack.local.ha.endswith('lane/keep/main/apple.main.uxd'))

        #stack.removeAllRemotes()
        stack.remotes = odict()
        stack.uids = odict()
        stack.loadRemotes()
        self.assertDictEqual(stack.remotes, {})

        # round trip with non empty remote data
        other1Data = self.createLaneData(name='other1',
                                         yid=0,
                                         base=self.base,
                                         lanename=stack.local.lanename)
        stack.addRemote(yarding.RemoteYard(stack=stack,
                                           name=other1Data['name'],
                                           lanename=other1Data['lanename'],
                                           dirpath=other1Data['dirpath']))

        other2Data = self.createLaneData(name='other2',
                                         yid=0,
                                         base=self.base,
                                         lanename=stack.local.lanename)
        stack.addRemote(yarding.RemoteYard(stack=stack,
                                           name=other2Data['name'],
                                           lanename=other2Data['lanename'],
                                           dirpath=other2Data['dirpath']))

        stack.dumpRemotes()
        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        validRemoteKeepData = {'2':
                                    {'uid': 2,
                                     'name': 'other1',
                                     'ha': '',
                                     'sid': 0,
                                     'rsid': 0},
                                '3':
                                    {'uid': 3,
                                     'name': 'other2',
                                     'ha': '',
                                     'sid': 0,
                                     'rsid': 0}
                                }
        validRemoteKeepData['2']['ha'] = stack.remotes[2].ha
        validRemoteKeepData['3']['ha'] = stack.remotes[3].ha
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        # stack method
        #convert string uid keys into int uid keys
        temp = validRemoteKeepData
        validRemoteKeepData = odict()
        for uid in temp:
            validRemoteKeepData[int(uid)] = temp[uid]

        #stack.removeAllRemotes()
        stack.remotes = odict()
        stack.uids = odict()
        stack.loadRemotes()
        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.uid] = odict([
                                                ('uid', remote.uid),
                                                ('name', remote.name),
                                                ('ha', remote.ha),
                                                ('sid', remote.sid),
                                                ('rsid', remote.rsid),
                                               ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)
        stack.server.close()

        # bootstrap new stack from stored keepdata
        stack = stacking.LaneStack(name=mainData['name'],
                                   dirpath=mainData['dirpath'],
                                   store=self.store)
        localKeepData = odict([
                                ('uid', stack.local.uid),
                                ('name', stack.local.name),
                                ('ha', stack.local.ha),
                                ('main', stack.local.main),
                                ('sid', stack.local.sid),
                                ('lanename', stack.local.lanename),
                                ('stack', stack.name),
                                ('nyid', stack.nyid),
                                ('accept', stack.accept),
                              ])
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.uid] = odict([
                                                ('uid', remote.uid),
                                                ('name', remote.name),
                                                ('ha', remote.ha),
                                                ('sid', remote.sid),
                                                ('rsid', remote.rsid),
                                               ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()
        stack.clearLocal()
        stack.clearRemoteKeeps()




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
    names = ['testBasic',]

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

    runOne('testBasic')

