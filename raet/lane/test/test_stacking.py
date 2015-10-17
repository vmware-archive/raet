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
import sys
import time
import tempfile
import shutil
from collections import deque

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.base.storing import Store

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting
from raet.lane import yarding, stacking

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

if sys.platform == 'win32':
    TEMPDIR = '\\\\.\\mailslot'
else:
    TEMPDIR = '/tmp'

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        if sys.platform == 'win32':
            self.tempDirpath = tempfile.mktemp(prefix="raet",  suffix="base",
                                               dir=TEMPDIR)
        else:
            self.tempDirpath = tempfile.mkdtemp(prefix="raet",  suffix="base",
                                                dir=TEMPDIR)

        self.baseDirpath = os.path.join(self.tempDirpath, 'lane', 'keep')

        # main stack
        self.main = stacking.LaneStack(name='main',
                                       uid=1,
                                       lanename='cherry',
                                       sockdirpath=self.baseDirpath)

        #other stack
        self.other = stacking.LaneStack(name='other',
                                        uid=1,
                                        lanename='cherry',
                                        sockdirpath=self.baseDirpath)

    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

        if not sys.platform == 'win32':
            shutil.rmtree(self.tempDirpath)

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

    def bootstrap(self, kind=raeting.PackKind.json.value):
        '''
        Basic messaging
        '''
        self.main.addRemote(yarding.RemoteYard(stack=self.main, ha=self.other.ha))
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 1)
        remote = self.main.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(remote.name, 'other')
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(remote.name in self.main.nameRemotes)
        self.assertTrue(remote.ha in self.main.haRemotes)
        self.assertIs(self.main.nameRemotes[remote.name], remote)
        self.assertIs(self.main.haRemotes[remote.ha], remote)


        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.nameRemotes)
        self.assertTrue(remote.ha in self.other.haRemotes)
        self.assertIs(self.other.nameRemotes[remote.name], remote)
        self.assertIs(self.other.haRemotes[remote.ha], remote)

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
        for i, duple in enumerate(self.main.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(self.main.local.name, duple))
            self.assertDictEqual(others[i], duple[0])

        self.assertEqual(len(self.other.rxMsgs), len(mains))
        for i, duple in enumerate(self.other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(self.other.local.name, duple))
            self.assertDictEqual(mains[i], duple[0])

    def createLaneData(self, name, uid, base, lanename):
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
        data['uid'] = uid
        data['sockdirpath'] = os.path.join(base, name)
        data['lanename'] = lanename

        return data

    def createLaneStack(self, data, main=None):
        '''
        Creates stack and local yard from data
        returns stack

        '''
        stack = stacking.LaneStack(name=data['name'],
                                   uid=data['uid'],
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
            main.transmit(msg, uid=main.fetchUidByName(other.local.name))
        for msg in others:
            other.transmit(msg,  uid=other.fetchUidByName(main.local.name))

        self.serviceMainOther(main, other, duration=duration)

        self.assertEqual(len(main.rxMsgs), len(others))
        for i, duple in enumerate(main.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(main.local.name, duple))
            self.assertDictEqual(others[i], duple[0])

        self.assertEqual(len(other.rxMsgs), len(mains))
        for i, duple in enumerate(other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(other.local.name, duple))
            self.assertDictEqual(mains[i], duple[0])

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
        self.bootstrap(kind=raeting.PackKind.json.value)

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
        self.bootstrap(kind=raeting.PackKind.pack.value)

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
        self.bootstrap(kind=raeting.PackKind.json.value)

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
        self.bootstrap(kind=raeting.PackKind.pack.value)

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

        self.bootstrap(kind=raeting.PackKind.json.value)

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

        self.bootstrap(kind=raeting.PackKind.pack.value)

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
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 0)

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.nameRemotes)
        self.assertTrue(remote.ha in self.other.haRemotes)
        self.assertIs(self.other.nameRemotes[remote.name], remote)
        self.assertIs(self.other.haRemotes[remote.ha], remote)

        stacking.LaneStack.Pk = raeting.PackKind.pack.value

        others = []
        others.append(odict(what="This is a message to the lord. Let me be", extra="Go away."))

        self.message(mains=[], others=others)

        self.assertEqual(len(self.main.remotes), 1)
        remote = self.main.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(remote.name, 'other')
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(remote.name in self.main.nameRemotes)
        self.assertTrue(remote.ha in self.main.haRemotes)
        self.assertIs(self.main.nameRemotes[remote.name], remote)
        self.assertIs(self.main.haRemotes[remote.ha], remote)

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
        self.other.addRemote(yarding.RemoteYard(stack=self.other, ha=self.main.ha))

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(len(self.main.remotes), 0)

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.ha, os.path.join(self.baseDirpath, 'cherry.other.uxd'))
        self.assertEqual(len(self.other.remotes), 1)
        remote = self.other.remotes.values()[0]
        self.assertEqual(remote.ha, os.path.join(self.baseDirpath, 'cherry.main.uxd'))
        self.assertEqual(remote.name, 'main')

        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(remote.name in self.other.nameRemotes)
        self.assertTrue(remote.ha in self.other.haRemotes)
        self.assertIs(self.other.nameRemotes[remote.name], remote)
        self.assertIs(self.other.haRemotes[remote.ha], remote)

        stacking.LaneStack.Pk = raeting.PackKind.pack.value

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
        self.bootstrap(kind=raeting.PackKind.json.value)

        for remote in self.main.remotes.values():
            fetched = self.main.haRemotes.get(remote.ha)
            self.assertIs(remote, fetched)


        for remote in self.other.remotes.values():
            fetched = self.other.haRemotes.get(remote.ha)
            self.assertIs(remote, fetched)

    def testRestart(self):
        '''
        Test messaging after restart
        '''
        console.terse("{0}\n".format(self.testRestart.__doc__))

        stacking.LaneStack.Pk = raeting.PackKind.json.value

        mainData = self.createLaneData(name='main',
                                       uid=1,
                                       base=self.baseDirpath,
                                       lanename='apple')
        main = self.createLaneStack(data=mainData, main=True)
        self.assertTrue(main.ha.endswith(os.path.join('lane','keep','main',
                                                      'apple.main.uxd')))
        self.assertTrue(main.main)

        otherData = self.createLaneData(name='other',
                                        uid=1,
                                        base=self.baseDirpath,
                                        lanename='apple')
        other = self.createLaneStack(data=otherData)
        self.assertTrue(other.ha.endswith(os.path.join('lane','keep','other',
                                                      'apple.other.uxd')))

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.ha))
        self.assertTrue('other' in main.nameRemotes)
        self.assertTrue(other.ha in main.haRemotes)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.ha))
        self.assertTrue('main' in other.nameRemotes)
        self.assertTrue(main.ha in other.haRemotes)

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
        self.assertTrue('other' in main.nameRemotes)
        self.assertEqual(len(other.remotes), 1)
        self.assertTrue('main' in other.nameRemotes)

        self.assertNotEqual(main.nameRemotes['other'].sid, 0)
        self.assertNotEqual(other.nameRemotes['main'].sid, 0)
        self.assertEqual(main.nameRemotes['other'].rsid,
                         other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                         main.nameRemotes['other'].sid)

        #now close down  make new stacks
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.ha))
        self.assertTrue('other' in main.nameRemotes)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.ha))
        self.assertTrue('main' in other.nameRemotes)

        self.assertEqual(len(main.remotes), 1)
        self.assertEqual(len(other.remotes), 1)

        self.assertNotEqual(main.nameRemotes['other'].sid, 0)
        self.assertNotEqual(other.nameRemotes['main'].sid, 0)
        self.assertEqual(main.nameRemotes['other'].rsid, 0)
        self.assertEqual(other.nameRemotes['main'].rsid, 0)

        self.messageMainOther(main, other, mains, others, duration=1.0)

        self.assertEqual(main.nameRemotes['other'].rsid,
                         other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                         main.nameRemotes['other'].sid)


        #now close down  make new stacks
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.ha))
        self.assertTrue('other' in main.nameRemotes)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.ha))
        self.assertTrue('main' in other.nameRemotes)

        self.assertEqual(len(main.remotes), 1)
        self.assertEqual(len(other.remotes), 1)

        self.assertNotEqual(main.nameRemotes['other'].sid, 0)
        self.assertNotEqual(other.nameRemotes['main'].sid, 0)
        self.assertEqual(main.nameRemotes['other'].rsid, 0)
        self.assertEqual(other.nameRemotes['main'].rsid, 0)

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

        self.assertEqual(main.nameRemotes['other'].rsid,
                          other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                          main.nameRemotes['other'].sid)

        #now close down  make new stacks send page at a time
        main.server.close()
        other.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        other = self.createLaneStack(data=otherData)

        main.addRemote(yarding.RemoteYard(stack=main, ha=other.ha))
        self.assertTrue('other' in main.nameRemotes)
        other.addRemote(yarding.RemoteYard(stack=other, ha=main.ha))
        self.assertTrue('main' in other.nameRemotes)

        self.assertEqual(len(main.remotes), 1)
        self.assertEqual(len(other.remotes), 1)

        self.assertNotEqual(main.nameRemotes['other'].sid, 0)
        self.assertNotEqual(other.nameRemotes['main'].sid, 0)
        self.assertEqual(main.nameRemotes['other'].rsid, 0)
        self.assertEqual(other.nameRemotes['main'].rsid, 0)

        for msg in mains:
            main.transmit(msg, uid=main.fetchUidByName(other.local.name))
        for msg in others:
            other.transmit(msg, uid=other.fetchUidByName(main.local.name))


        self.assertEqual(len(main.txMsgs), 1)
        self.assertEqual(len(other.txMsgs), 1)
        self.assertEqual(len(main.nameRemotes['other'].books), 0)
        self.assertEqual(len(other.nameRemotes['main'].books), 0)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # Now only send and receive one page to/from each side
        self.serviceOneAll(main, other)

        self.assertEqual(len(main.txMsgs), 0)
        self.assertEqual(len(other.txMsgs), 0)
        self.assertEqual(len(main.txes), 1)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.nameRemotes['other'].books), 1)
        self.assertEqual(len(other.nameRemotes['main'].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        self.assertEqual(main.nameRemotes['other'].rsid,
                          other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                          main.nameRemotes['other'].sid)

        # save sids
        mainSid = main.nameRemotes['other'].sid
        otherSid = other.nameRemotes['main'].sid

        #now close down one side only, make new stack
        main.server.close()
        main = self.createLaneStack(data=mainData, main=True)
        main.addRemote(yarding.RemoteYard(stack=main, ha=other.ha))

        self.assertEqual(len(main.remotes), 1)
        self.assertEqual(len(other.remotes), 1)

        self.assertNotEqual(main.nameRemotes['other'].sid, mainSid)
        self.assertEqual(other.nameRemotes['main'].sid, otherSid)
        self.assertEqual(main.nameRemotes['other'].rsid, 0)
        self.assertEqual(other.nameRemotes['main'].rsid, mainSid)

        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.nameRemotes['other'].books), 0)
        self.assertEqual(len(other.nameRemotes['main'].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)

        # Now remaining page from other (there should be no pages from main)
        self.serviceOneAll(main, other)

        self.assertEqual(main.nameRemotes['other'].rsid,
                          other.nameRemotes['main'].sid)
        self.assertNotEqual(other.nameRemotes['main'].rsid,
                          main.nameRemotes['other'].sid)


        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.nameRemotes['other'].books), 0)
        self.assertEqual(len(other.nameRemotes['main'].books), 1)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 0)
        self.assertEqual(main.stats['missed_page'], 1)


        #send a new message from main and reap stale book from other
        for msg in mains:
            main.transmit(msg, uid=main.fetchUidByName(other.local.name))

        self.serviceMainOther(main, other, duration=1.0)

        self.assertEqual(main.nameRemotes['other'].rsid,
                          other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                          main.nameRemotes['other'].sid)
        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.nameRemotes['other'].books), 0)
        self.assertEqual(len(other.nameRemotes['main'].books), 0)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.rxMsgs), 1)
        self.assertEqual(other.stats['stale_book'], 1)

        self.assertEqual(len(other.rxMsgs), len(mains))
        for i, duple in enumerate(other.rxMsgs):
            console.terse("Yard '{0}' rxed:\n'{1}'\n".format(other.local.name, duple))
            self.assertDictEqual(mains[i], duple[0])


        # setup to test reset sid numbering by sending single pages to create stale books

        other.rxMsgs.pop()
        for msg in mains:
            main.transmit(msg, uid=main.fetchUidByName(other.local.name))
        for msg in others:
            other.transmit(msg, uid=other.fetchUidByName(main.local.name))

        self.serviceOneAll(main, other)

        self.assertEqual(main.nameRemotes['other'].rsid,
                          other.nameRemotes['main'].sid)
        self.assertEqual(other.nameRemotes['main'].rsid,
                          main.nameRemotes['other'].sid)


        self.assertEqual(len(main.txes), 1)
        self.assertEqual(len(other.txes), 1)
        self.assertEqual(len(main.nameRemotes['other'].books), 1)
        self.assertEqual(len(other.nameRemotes['main'].books), 1)
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
        main.nameRemotes['other'].sid = mainSid
        other.nameRemotes['main'].sid = otherSid
        for msg in mains:
            main.transmit(msg, uid=main.fetchUidByName(other.local.name))
        for msg in others:
            other.transmit(msg,  uid=other.fetchUidByName(main.local.name))

        self.serviceOneAll(main, other)

        self.assertEqual(main.nameRemotes['other'].sid, mainSid)
        self.assertEqual(other.nameRemotes['main'].sid, otherSid)
        self.assertEqual(main.nameRemotes['other'].rsid, otherSid)
        self.assertEqual(other.nameRemotes['main'].rsid, mainSid)

        self.assertEqual(len(main.txes), 0)
        self.assertEqual(len(other.txes), 0)
        self.assertEqual(len(main.nameRemotes['other'].books), 0)
        self.assertEqual(len(other.nameRemotes['main'].books), 0)
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


