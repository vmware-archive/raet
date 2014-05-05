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

        self.baseDirpath = os.path.join(
                tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp'),
                'lane')

        # main stack
        self.main = stacking.LaneStack(name='main',
                                    lanename='cherry',
                                    yardname='main',
                                    dirpath=self.baseDirpath,
                                    sockdirpath=self.baseDirpath)

        #other stack
        self.other = stacking.LaneStack(name='other',
                                    lanename='cherry',
                                    yardname='other',
                                    dirpath=self.baseDirpath,
                                    sockdirpath=self.baseDirpath)

    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

        if os.path.exists(self.baseDirpath):
            shutil.rmtree(self.baseDirpath)

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
        self.main.addRemote(yarding.RemoteYard(ha=self.other.local.ha))
        self.other.addRemote(yarding.RemoteYard(ha=self.main.local.ha))

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
        Transmit and reciev messages in mains and others lists
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
        self.other.addRemote(yarding.RemoteYard(ha=self.main.local.ha))

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
        self.other.addRemote(yarding.RemoteYard(ha=self.main.local.ha))

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
             'testAutoAcceptNot', ]
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

    #runOne('testAutoAcceptNot')
