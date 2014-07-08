# -*- coding: utf-8 -*-
'''
Tests to try out stacking. Potentially ephemeral

'''
# pylint: skip-file
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import time
import tempfile
import shutil
from collections import deque

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting
from raet.lane import yarding, stacking

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass



class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.tempDirPath = tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')
        self.baseDirpath = os.path.join(self.tempDirPath, 'lane', 'keep')

        # main stack
        self.main = stacking.LaneStack(name='main',
                                       yid=1,
                                       lanename='cherry',
                                       sockdirpath=self.baseDirpath)

        #other stack
        self.other = stacking.LaneStack(name='other',
                                        yid=1,
                                        lanename='cherry',
                                        sockdirpath=self.baseDirpath)

    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

    def service(self, duration=1.0, real=True):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            self.other.serviceAll()
            self.main.serviceAll()
            self.store.advanceStamp(0.1)
            if real:
                time.sleep(0.1)

    def serviceOther(self, duration=1.0, real=True):
        '''
        Utility method to only service other queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            self.other.serviceAll()
            self.store.advanceStamp(0.1)
            if real:
                time.sleep(0.1)

    def serviceMain(self, duration=1.0, real=True):
        '''
        Utility method to only service main queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            self.main.serviceAll()
            self.store.advanceStamp(0.1)
            if real:
                time.sleep(0.1)

    def bootstrap(self, kind=raeting.packKinds.json):
        '''
        Basic messaging
        '''
        self.main.addRemote(yarding.RemoteYard(stack=self.main, ha=self.other.local.ha))
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.local.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.local.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 1)
        remote = self.main.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(remote.name, 'other')
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(remote.name in self.main.uids)
        self.assertIs(self.main.remotes[self.main.uids[remote.name]], remote)


        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.local.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.uids)
        self.assertIs(self.other.remotes[self.other.uids[remote.name]], remote)

        stacking.LaneStack.Pk = kind

    def message(self, mains, others, duration=1.0):
        '''
        Transmit and receive messages in mains and others lists
        '''
        for msg in mains:
            self.main.transmit(msg=msg)

        for msg in others:
            self.other.transmit(msg=msg)

        self.service(duration=duration)

        self.assertEqual(len(self.main.rxMsgs), len(others))
        for i, msg in enumerate(self.main.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(self.main.local.name, msg))
            self.assertDictEqual(others[i], msg)

        self.assertEqual(len(self.other.rxMsgs), len(mains))
        for i, msg in enumerate(self.other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(self.other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

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
        data['sockdirpath'] = os.path.join(base, name)
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
                                   main=main,
                                   lanename=data['lanename'],
                                   sockdirpath=data['sockdirpath'])

        return stack

    def serviceMainOther(self, main, other, duration=1.0):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            other.serviceAll()
            main.serviceAll()
            self.store.advanceStamp(0.1)
            time.sleep(0.1)


    def messageMainOther(self, main,  other, mains, others, duration=1.0):
        '''
        Utility to send messages both ways
        '''
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])

        self.serviceMainOther(main, other, duration=duration)

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

    def testMessageJson(self):
        '''
        Basic messaging with json packing
        '''
        console.terse("{0}\n".format(self.testMessageJson.__doc__))
        self.bootstrap(kind=raeting.packKinds.json)

        mains = []
        mains.append(odict(what="This is a message to the serf. Get to Work", extra="Fix the fence."))

        others = []
        others.append(odict(what="This is a message to the lord. Let me be", extra="Go away."))

        self.message(mains=mains, others=others)

    def testMessageMsgpack(self):
        '''
        Basic messaging with msgpack packing
        '''
        console.terse("{0}\n".format(self.testMessageMsgpack.__doc__))
        self.bootstrap(kind=raeting.packKinds.pack)

        mains = []
        mains.append(odict(what="This is a message to the serf. Get to Work", extra="Fix the fence."))

        others = []
        others.append(odict(what="This is a message to the lord. Let me be", extra="Go away."))

        self.message(mains=mains, others=others)

    def testMessageMultipleJson(self):
        '''
        Multiple messages with json packing
        '''
        console.terse("{0}\n".format(self.testMessageMultipleJson.__doc__))
        self.bootstrap(kind=raeting.packKinds.json)

        mains = []
        mains.append(odict([('house', "Mama mia1"), ('queue', "fix me")]))
        mains.append(odict([('house', "Mama mia2"), ('queue', "stop me")]))
        mains.append(odict([('house', "Mama mia3"), ('queue', "help me")]))
        mains.append(odict([('house', "Mama mia4"), ('queue', "run me")]))


        others = []
        others.append(odict([('house', "Papa pia1"), ('queue', "fix me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "stop me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "help me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "run me")]))

        self.message(mains=mains, others=others)

    def testMessageMultipleMsgpack(self):
        '''
        multiple messages with msgpack packing
        '''
        console.terse("{0}\n".format(self.testMessageMultipleMsgpack.__doc__))
        self.bootstrap(kind=raeting.packKinds.pack)

        mains = []
        mains.append(odict([('house', "Mama mia1"), ('queue', "fix me")]))
        mains.append(odict([('house', "Mama mia2"), ('queue', "stop me")]))
        mains.append(odict([('house', "Mama mia3"), ('queue', "help me")]))
        mains.append(odict([('house', "Mama mia4"), ('queue', "run me")]))


        others = []
        others.append(odict([('house', "Papa pia1"), ('queue', "fix me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "stop me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "help me")]))
        others.append(odict([('house', "Papa pia1"), ('queue', "run me")]))
        self.message(mains=mains, others=others)

    def testMessageSectionedJson(self):
        '''
        Sectioned messages with json packing
        '''
        console.terse("{0}\n".format(self.testMessageSectionedJson.__doc__))

        self.bootstrap(kind=raeting.packKinds.json)

        #big packets
        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])


        mains = []
        mains.append(odict([('route', route), ('content', stuff)]))

        src = ['citizen', self.other.local.name, None]
        dst = ['mayor', self.main.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        others = []
        others.append(odict([('route', route), ('content', stuff)]))

        self.message(mains=mains, others=others, duration=2.0)

    def testMessageSectionedMsgpack(self):
        '''
        Sectioned messages with msgpack packing
        '''
        console.terse("{0}\n".format(self.testMessageSectionedMsgpack.__doc__))

        self.bootstrap(kind=raeting.packKinds.pack)

        #big packets
        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])


        mains = []
        mains.append(odict([('route', route), ('content', stuff)]))

        src = ['citizen', self.other.local.name, None]
        dst = ['mayor', self.main.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        others = []
        others.append(odict([('route', route), ('content', stuff)]))

        self.message(mains=mains, others=others, duration=2.0)

    def testAutoAccept(self):
        '''
        Basic send auto accept message
        '''
        console.terse("{0}\n".format(self.testAutoAccept.__doc__))

        self.assertTrue(self.main.accept)

        # Don't add remote yard to main so only way to get message from other is
        # if auto acccept works
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.local.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.local.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 0)

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.local.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.uids)
        self.assertIs(self.other.remotes[self.other.uids[remote.name]], remote)

        stacking.LaneStack.Pk = raeting.packKinds.pack

        others = []
        others.append(odict(what="This is a message to the lord. Let me be", extra="Go away."))

        self.message(mains=[], others=others)

        self.assertEqual(len(self.main.remotes), 1)
        remote = self.main.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(remote.name, 'other')
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(remote.name in self.main.uids)
        self.assertIs(self.main.remotes[self.main.uids[remote.name]], remote)

        self.main.rxMsgs = deque()
        self.other.rxMsgs = deque()

        mains = []
        mains.append(odict(what="This is a message to the serf. Get to Work", extra="Fix the fence."))

        self.message(mains=mains, others=[])

    def testAutoAcceptNot(self):
        '''
        Basic send non auto accept message
        '''
        console.terse("{0}\n".format(self.testAutoAcceptNot.__doc__))
        self.main.accept =  False
        self.assertIs(self.main.accept, False)

        # Don't add remote yard to main so only way to get message from other is
        # if auto acccept works
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.local.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.local.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 0)

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.local.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.uids)
        self.assertIs(self.other.remotes[self.other.uids[remote.name]], remote)

        stacking.LaneStack.Pk = raeting.packKinds.pack

        others = []
        others.append(odict(what="This is a message to the lord. Let me be", extra="Go away."))

        for msg in others:
            self.other.transmit(msg=msg)

        self.service()

        self.assertEqual(len(self.main.rxMsgs), 0)
        self.assertEqual(len(self.main.remotes), 0)
        self.assertEqual(self.main.stats['unaccepted_source_yard'], 1)

    def testFetchRemoteFromHa(self):
        '''
        Fetching remote yard by HA
        '''
        console.terse("{0}\n".format(self.testFetchRemoteFromHa.__doc__))
        self.bootstrap(kind=raeting.packKinds.json)

        for remote in self.main.remotes.values():
            fetched = self.main.fetchRemoteFromHa(remote.ha)
            self.assertIs(remote, fetched)


        for remote in self.other.remotes.values():
            fetched = self.other.fetchRemoteFromHa(remote.ha)
            self.assertIs(remote, fetched)

    def testRestart(self):
        '''
        Test messaging after restart
        '''
        console.terse("{0}\n".format(self.testRestart.__doc__))

        stacking.LaneStack.Pk = raeting.packKinds.json

        mainData = self.createLaneData(name='main',
                                       yid=1,
                                       base=self.baseDirpath,
                                       lanename='apple')
        main = self.createLaneStack(data=mainData, main=True)
        self.assertTrue(main.local.ha.endswith('/lane/keep/main/apple.main.uxd'))
        self.assertTrue(main.local.main)

        otherData = self.createLaneData(name='other',
                                        yid=1,
                                        base=self.baseDirpath,
                                        lanename='apple')
        other = self.createLaneStack(data=otherData)
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

        self.messageMainOther(main,  other, mains, others, duration=1.0)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertNotEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertNotEqual(other.remotes[other.uids['main']].sid, 0)
        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down  make new stacks
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.local.ha))
        self.assertTrue('other' in main.uids)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.local.ha))
        self.assertTrue('main' in other.uids)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertNotEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertNotEqual(other.remotes[other.uids['main']].sid, 0)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, 0)

        self.messageMainOther(main, other, mains, others, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down  make new stacks
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.local.ha))
        self.assertTrue('other' in main.uids)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.local.ha))
        self.assertTrue('main' in other.uids)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertNotEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertNotEqual(other.remotes[other.uids['main']].sid, 0)
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

        self.messageMainOther(main, other, mains, others, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)

        #now close down  make new stacks send page at a time
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.local.ha))
        self.assertTrue('other' in main.uids)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.local.ha))
        self.assertTrue('main' in other.uids)

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertNotEqual(main.remotes[main.uids['other']].sid, 0)
        self.assertNotEqual(other.remotes[other.uids['main']].sid, 0)
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

        # save sids
        mainSid = main.remotes[main.uids['other']].sid
        otherSid = other.remotes[other.uids['main']].sid

        #now close down one side only, make new stack
        main.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        main.addRemote(yarding.RemoteYard(stack=main, ha=other.local.ha))

        self.assertEqual(len(main.remotes), 1)
        self.assertTrue('other' in main.uids)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.uids)

        self.assertNotEqual(main.remotes[main.uids['other']].sid, mainSid)
        self.assertEqual(other.remotes[other.uids['main']].sid, otherSid)
        self.assertEqual(main.remotes[main.uids['other']].rsid, 0)
        self.assertEqual(other.remotes[other.uids['main']].rsid, mainSid)

        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # Now remaining page from other (there should be no pages from main)
        self.serviceOneAll(main, other)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertNotEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)


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

        self.serviceMainOther(main, other, duration=1.0)

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)
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

        self.assertEqual(main.remotes[main.uids['other']].rsid,
                         other.remotes[other.uids['main']].sid)
        self.assertEqual(other.remotes[other.uids['main']].rsid,
                         main.remotes[main.uids['other']].sid)


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

        mainSid = main.local.nextSid()
        otherSid = other.local.nextSid()
        main.remotes[main.uids['other']].sid = mainSid
        other.remotes[other.uids['main']].sid = otherSid
        for msg in mains:
            main.transmit(msg, duid=main.uids[other.local.name])
        for msg in others:
            other.transmit(msg,  duid=other.uids[main.local.name])

        self.serviceOneAll(main, other)

        self.assertEqual(main.remotes[main.uids['other']].sid, mainSid)
        self.assertEqual(other.remotes[other.uids['main']].sid, otherSid)
        self.assertEqual(main.remotes[main.uids['other']].rsid, otherSid)
        self.assertEqual(other.remotes[other.uids['main']].rsid, mainSid)

        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.remotes[main.uids['other']].books), 0)
        self.assertEqual(len(other.remotes[other.uids['main']].books), 0)
        self.assertEqual(len(main.rxMsgs), 1)
        self.assertEqual(len(other.rxMsgs), 1)
        self.assertEqual(main.stats['stale_book'], 1)
        self.assertEqual(other.stats['stale_book'], 2)

        main.server.close()
        other.server.close()

def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    """ Unittest runner """
    tests =  []
    names = ['testMessageJson',
             'testMessageMsgpack',
             'testMessageMultipleJson',
             'testMessageMultipleMsgpack',
             'testMessageSectionedJson',
             'testMessageSectionedMsgpack',
             'testAutoAccept',
             'testAutoAcceptNot',
             'testFetchRemoteFromHa',
             'testRestart']
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

    #runAll() #run all unittests

    runSome()#only run some

    #runOne('testRestart')


