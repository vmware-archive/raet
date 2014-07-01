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

    def message(self, main,  other, mains, others, duration=1.0):
        '''
        Utility to send messages both ways
        '''
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])

        self.service(main, other, duration=duration)

        self.assertEqual(len(main.rxMsgs), len(others))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg)

        self.assertEqual(len(other.rxMsgs), len(mains))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

    def serviceStackOneTx(self, stack):
        '''
        Utility method to service one packet on Tx queues. Call from test method.
        '''
        stack.serviceOneAllTx()
        time.sleep(0.1)
        self.store.advanceStamp(0.1)

    def serviceStackOneRx(self, stack):
        '''
        Utility method to service one packet on Rx queues. Call from test method.
        '''
        stack.serviceOneAllRx()
        time.sleep(0.1)
        self.store.advanceStamp(0.1)

    def serviceOneTx(self, main, other):
        '''
        Utility method to service one packet on Tx queues. Call from test method.
        '''
        other.serviceOneAllTx()
        main.serviceOneAllTx()
        time.sleep(0.1)
        self.store.advanceStamp(0.1)

    def serviceOneRx(self, main, other):
        '''
        Utility method to service one packet on Rx queues. Call from test method.
        '''
        other.serviceOneAllRx()
        main.serviceOneAllRx()
        time.sleep(0.1)
        self.store.advanceStamp(0.1)

    def serviceOneAll(self, main, other):
        '''
        Utility method to service one packet on all queues. Call from test method.
        '''
        self.serviceOneTx(main=main, other=other)
        self.serviceOneRx(main=main, other=other)

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
        stack.restoreRemotes()
        self.assertDictEqual(stack.remotes, {})

        # round trip with non empty remote data
        other1Data = self.createLaneData(name='other1',
                                         yid=0,
                                         base=self.base,
                                         lanename=stack.local.lanename)
        stack.addRemote(yarding.RemoteYard(stack=stack,
                                           name=other1Data['name'],
                                           lanename=other1Data['lanename'],
                                           dirpath=self.base)) #other1Data['dirpath']

        other2Data = self.createLaneData(name='other2',
                                         yid=0,
                                         base=self.base,
                                         lanename=stack.local.lanename)
        stack.addRemote(yarding.RemoteYard(stack=stack,
                                           name=other2Data['name'],
                                           lanename=other2Data['lanename'],
                                           dirpath=self.base )) #other2Data['dirpath']

        stack.dumpRemotes()
        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        validRemoteKeepData = {'2':
                                    {'uid': 2,
                                     'name': 'other1',
                                     'ha': '',
                                     'sid': 0},
                                '3':
                                    {'uid': 3,
                                     'name': 'other2',
                                     'ha': '',
                                     'sid': 0,}
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
        stack.restoreRemotes()
        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.uid] = odict([
                                                ('uid', remote.uid),
                                                ('name', remote.name),
                                                ('ha', remote.ha),
                                                ('sid', remote.sid),
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
                                               ])
            validRemoteKeepData[remote.uid]['sid'] += 1 # on load stack increments
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()
        stack.clearAllDir()
        #stack.clearLocal()
        #stack.clearRemoteKeeps()

    def testRestart(self):
        '''
        Test messaging after restart with saved data
        '''
        console.terse("{0}\n".format(self.testRestart.__doc__))

        stacking.LaneStack.Pk = raeting.packKinds.json

        mainData = self.createLaneData(name='main', yid=1, base=self.base, lanename='apple')
        keeping.clearAllKeep(mainData['dirpath'])
        main = self.createLaneStack(data=mainData, main=True)
        self.assertTrue(main.keep.dirpath.endswith('/lane/keep/main'))
        self.assertTrue(main.keep.localdirpath.endswith('/lane/keep/main/local'))
        self.assertTrue(main.keep.remotedirpath.endswith('/lane/keep/main/remote'))
        self.assertTrue(main.keep.localfilepath.endswith('/lane/keep/main/local/yard.json'))
        self.assertTrue(main.local.ha.endswith('/lane/keep/main/apple.main.uxd'))
        self.assertTrue(main.local.main)

        otherData = self.createLaneData(name='other', yid=1, base=self.base, lanename='apple')
        keeping.clearAllKeep(otherData['dirpath'])
        other = self.createLaneStack(data=otherData)
        self.assertTrue(other.keep.dirpath.endswith('/lane/keep/other'))
        self.assertTrue(other.keep.localdirpath.endswith('/lane/keep/other/local'))
        self.assertTrue(other.keep.remotedirpath.endswith('/lane/keep/other/remote'))
        self.assertTrue(other.keep.localfilepath.endswith('/lane/keep/other/local/yard.json'))
        self.assertTrue(other.local.ha.endswith('/lane/keep/other/apple.other.uxd'))

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.local.ha))
        self.assertTrue('other' in main.uids)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.local.ha))
        self.assertTrue('main' in other.uids)

        src = ['mayor', main.local.name, None] # (house, yard, queue)
        dst = ['citizen', other.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = "This is my command"
        mains = []
        mains.append(odict([('route', route), ('content', stuff)]))

        src = ['citizen', other.local.name, None]
        dst = ['mayor', main.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = "This is my reply."
        others = []
        others.append(odict([('route', route), ('content', stuff)]))

        self.message(main,  other, mains, others, duration=1.0)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertEqual(other.remotes[other.uids['main']].sid, 0)
        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        main.dumpRemotes()
        other.dumpRemotes()

        #now close down and reload data, make new stacks with saved data
        main.server.close()
        other.server.close()
        main = stacking.LaneStack(dirpath=mainData['dirpath'], store=self.store)
        other = stacking.LaneStack(dirpath=otherData['dirpath'], store=self.store)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertEqual(main.remotes[main.uids['other']].sid, 1)
        self.assertEqual(other.remotes[other.uids['main']].sid, 1)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 0)

        self.message(main,  other, mains, others, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down and reload data, make new stacks with saved data
        main.server.close()
        other.server.close()
        main = stacking.LaneStack(dirpath=mainData['dirpath'], store=self.store)
        other = stacking.LaneStack(dirpath=otherData['dirpath'], store=self.store)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertEqual(main.remotes[main.uids['other']].sid, 2)
        self.assertEqual(other.remotes[other.uids['main']].sid, 2)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 0)

        # now send paginated messages
        src = ['mayor', main.local.name, None] # (house, yard, queue)
        dst = ['citizen', other.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = ["Do as I say."]
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        mains = []
        mains.append(odict([('route', route), ('content', stuff)]))

        src = ['citizen', other.local.name, None]
        dst = ['mayor', main.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = ["As you wish."]
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        others = []
        others.append(odict([('route', route), ('content', stuff)]))

        self.message(main,  other, mains, others, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down and reload data, make new stacks with saved data
        main.server.close()
        other.server.close()
        main = stacking.LaneStack(dirpath=mainData['dirpath'], store=self.store)
        other = stacking.LaneStack(dirpath=otherData['dirpath'], store=self.store)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertEqual(main.remotes[main.uids['other']].sid, 3)
        self.assertEqual(other.remotes[other.uids['main']].sid, 3)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 0)

        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])


        self.assertEqual(len(main.txMsgs), 1)
        self.assertEqual(len(other.txMsgs), 1)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 0)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # Now only send and receive one page to/from each side
        self.serviceOneAll(main, other)

        self.assertEqual(len(main.txMsgs), 0)
        self.assertEqual(len(other.txMsgs), 0)
        self.assertEqual(len(main.txes), 1)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 1)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down one side only and reload data, make new stack with saved data
        main.server.close()
        main = stacking.LaneStack(dirpath=mainData['dirpath'], store=self.store)


        self.assertEqual(main.remotes[main.uids['other']].sid, 4)
        self.assertEqual(other.remotes[other.uids['main']].sid, 3)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 3)
        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # Now remaining page from other (there should be no pages from main)
        self.serviceOneAll(main, other)

        self.assertEqual(main.remotes[main.uids['other']].sid, 4)
        self.assertEqual(other.remotes[other.uids['main']].sid, 3)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 3)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 3)
        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)
        self.assertEqual(main.stats['missed_page'], 1)


        #send a new message from main and reap stale book from other
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])

        self.service(main, other, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].sid, 4)
        self.assertEqual(other.remotes[other.uids['main']].sid, 3)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 3)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 4)
        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 0)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 1)
        self.assertEqual(other.stats['stale_book'], 1)

        self.assertEqual(len(other.rxMsgs), len(mains))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg)


        # setup to test reset sid numbering by sending single pages to create stale books

        other.rxMsgs.pop()
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])

        self.serviceOneAll(main, other)

        self.assertEqual(main.remotes[main.uids['other']].sid, 4)
        self.assertEqual(other.remotes[other.uids['main']].sid, 3)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 3)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 4)
        self.assertEqual(len(main.txes), 1)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 1)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # simulate restart that loses msg in queue
        main.txes.pop()
        other.txes.pop()

        src = ['mayor', main.local.name, None] # (house, yard, queue)
        dst = ['citizen', other.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = "This is my command"
        mains = []
        mains.append(odict([('route', route), ('content', stuff)]))

        src = ['citizen', other.local.name, None]
        dst = ['mayor', main.local.name, None]
        route = odict([('src', src), ('dst', dst)])
        stuff = "This is my reply."
        others = []
        others.append(odict([('route', route), ('content', stuff)]))

        main.remotes[main.uids['other']].sid = 0 #set to zero to reset
        other.remotes[other.uids['main']].sid = 0 #set to zero to reset
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])

        self.serviceOneAll(main, other)

        self.assertEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertEqual(other.remotes[other.uids['main']].sid, 0)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 0)
        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 0)
        self.assertEqual(len(main.rxMsgs), 1)
        self.assertEqual(len(other.rxMsgs), 1)
        self.assertEqual(main.stats['stale_book'], 1)
        self.assertEqual(other.stats['stale_book'], 2)

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
             'testRestart', ]

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

    runAll() #run all unittests

    #runSome()#only run some

    #runOne('testRestart')

