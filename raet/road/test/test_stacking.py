# -*- coding: utf-8 -*-
'''
Tests to try out stacking. Potentially ephemeral

'''
from __future__ import print_function
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

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.base.storing import Store

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.road import keeping, estating, stacking, transacting

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
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.baseDirpath=tempfile.mkdtemp(prefix="raet",  suffix="base", dir=TEMPDIR)
        stacking.RoadStack.Bk = raeting.BodyKind.json.value

        #main stack
        mainName = "main"
        mainDirpath = os.path.join(self.baseDirpath, 'road', 'keep', mainName)
        signer = nacling.Signer()
        mainSignKeyHex = signer.keyhex
        privateer = nacling.Privateer()
        mainPriKeyHex = privateer.keyhex


        #other stack
        otherName = "other"
        otherDirpath = os.path.join(self.baseDirpath, 'road', 'keep', otherName)
        signer = nacling.Signer()
        otherSignKeyHex = signer.keyhex
        privateer = nacling.Privateer()
        otherPriKeyHex = privateer.keyhex


        keeping.clearAllKeep(mainDirpath)
        keeping.clearAllKeep(otherDirpath)

        self.main = stacking.RoadStack(store=self.store,
                                       name=mainName,
                                       main=True,
                                       auto=raeting.AutoMode.once.value,
                                       sigkey=mainSignKeyHex,
                                       prikey=mainPriKeyHex,
                                       dirpath=mainDirpath,
                                       )

        self.other = stacking.RoadStack(store=self.store,
                                        name=otherName,
                                        auto=raeting.AutoMode.once.value,
                                        ha=("", raeting.RAET_TEST_PORT),
                                        sigkey=otherSignKeyHex,
                                        prikey=otherPriKeyHex,
                                        dirpath=otherDirpath,
                                        )



    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

        self.main.clearAllDir()
        self.other.clearAllDir()

        if os.path.exists(self.baseDirpath):
            shutil.rmtree(self.baseDirpath)


    def join(self, timeout=None):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        if not self.other.remotes:
            self.other.addRemote(estating.RemoteEstate(stack=self.other,
                                                       #name=self.main.local.name,
                                                       fuid=0, # vacuous join
                                                       sid=0, # always 0 for join
                                                       ha=self.main.local.ha)
                                )
        self.other.join(timeout=timeout)
        self.service()

    def allow(self):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        self.other.allow()
        self.service()

    def alive(self, initiator, correspondent):
        '''
        Utility method to do alive. Call from test method.
        '''
        console.terse("\nAlive Transaction **************\n")
        initiator.alive()
        self.service()

    def service(self, duration=1.0, real=True):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            self.other.serviceAll()
            self.main.serviceAll()
            if not (self.main.transactions or self.other.transactions):
                break
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
            if not (self.other.transactions):
                break
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
            if not (self.main.transactions):
                break
            self.store.advanceStamp(0.1)
            if real:
                time.sleep(0.1)

    def bootstrap(self, bk=raeting.BodyKind.json.value):
        '''
        Initialize
            main on port 7530 with uid of 1
            other on port 7531 with uid of 1
        Complete
            main joined and allowed
            other  joined and allowed
        '''
        stacking.RoadStack.Bk = bk

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.ha, ("0.0.0.0", raeting.RAET_PORT))

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        self.join()
        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.name, 'other')
        self.assertEqual(remote.uid, 2)
        self.assertEqual(remote.uid, remote.nuid)
        self.assertEqual(remote.fuid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertTrue(len(self.main.nameRemotes), 1)
        self.assertEqual(len(remote.transactions), 0)
        self.assertTrue('other' in self.main.nameRemotes)
        self.assertIs(self.main.nameRemotes[remote.name], remote)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 1)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.name, 'main')
        self.assertEqual(remote.uid, 2)
        self.assertEqual(remote.uid, remote.nuid)
        self.assertEqual(remote.fuid, 2)
        self.assertTrue(2 in self.other.remotes)
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertTrue(len(self.other.nameRemotes), 1)
        self.assertEqual(len(remote.transactions), 0)
        self.assertTrue('main' in self.other.nameRemotes)
        self.assertIs(self.other.nameRemotes[remote.name], remote)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

        self.allow()
        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(remote.transactions), 0)
        console.terse("Stack '{0}' estate name '{1}' allowd with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.allowed))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(remote.transactions), 0)
        console.terse("Stack '{0}' estate name '{1}' allowed with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.allowed))

        console.terse("\nMessage: other to main *********\n")
        body = odict(what="This is a message to the main estate. How are you", extra="I am fine.")
        self.other.txMsgs.append((body, self.other.remotes.values()[0].fuid, None))
        #self.other.message(body=body, deid=self.main.local.uid)
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(len(self.main.transactions), 0)
        for msg, name in self.main.rxMsgs:
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.main.local.name, msg))
        self.assertDictEqual(body, self.main.rxMsgs[0][0])

        console.terse("\nMessage: main to other *********\n")
        body = odict(what="This is a message to the other estate. Get to Work", extra="Fix the fence.")
        self.main.txMsgs.append((body, self.main.remotes.values()[0].fuid, None))
        #self.main.message(body=body, deid=self.other.local.uid)
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(len(self.other.transactions), 0)
        for msg, name in self.other.rxMsgs:
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.other.local.name, msg))
        self.assertDictEqual(body, self.other.rxMsgs[0][0])

    def bidirectional(self, bk=raeting.BodyKind.json.value, mains=None, others=None, duration=3.0):
        '''
        Initialize
            main on port 7530 with uid of 1
            other on port 7531 with uid of 0
        Complete
            main uid of 1 joined and allowed
            other uid of 2 joined and allowed
        '''
        stacking.RoadStack.Bk = bk
        mains = mains or []
        other = others or []

        self.join()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        console.terse("\nMessages Bidirectional *********\n")
        for msg in mains:
            self.main.transmit(msg)
        for msg in others:
            self.other.transmit(msg)

        self.service(duration=duration)

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(others), len(self.main.rxMsgs))
        for i, duple in enumerate(self.main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.main.local.name, duple))
            self.assertDictEqual(others[i], duple[0])

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(len(self.other.transactions), 0)
        self.assertEqual(len(mains), len(self.other.rxMsgs))
        for i, duple in enumerate(self.other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.other.local.name, duple))
            self.assertDictEqual(mains[i], duple[0])

    def testBootstrapJson(self):
        '''
        Test join allow message transactions with JSON Serialization of body
        '''
        console.terse("{0}\n".format(self.testBootstrapJson.__doc__))
        self.bootstrap(bk=raeting.BodyKind.json.value)

    def testBootstrapMsgpack(self):
        '''
        Test join allow message transactions with MsgPack Serialization of body
        '''
        console.terse("{0}\n".format(self.testBootstrapMsgpack.__doc__))
        self.bootstrap(bk=raeting.BodyKind.msgpack.value)

    def testMsgBothwaysJson(self):
        '''
        Test message transactions
        '''
        console.terse("{0}\n".format(self.testMsgBothwaysJson.__doc__))

        others = []
        others.append(odict(house="Mama mia1", queue="fix me"))
        others.append(odict(house="Mama mia2", queue="help me"))
        others.append(odict(house="Mama mia3", queue="stop me"))
        others.append(odict(house="Mama mia4", queue="run me"))

        mains = []
        mains.append(odict(house="Papa pia1", queue="fix me"))
        mains.append(odict(house="Papa pia2", queue="help me"))
        mains.append(odict(house="Papa pia3", queue="stop me"))
        mains.append(odict(house="Papa pia4", queue="run me"))

        self.bidirectional(bk=raeting.BodyKind.json.value, mains=mains, others=others)

    def testMsgBothwaysMsgpack(self):
        '''
        Test message transactions
        '''
        console.terse("{0}\n".format(self.testMsgBothwaysMsgpack.__doc__))

        others = []
        others.append(odict(house="Mama mia1", queue="fix me"))
        others.append(odict(house="Mama mia2", queue="help me"))
        others.append(odict(house="Mama mia3", queue="stop me"))
        others.append(odict(house="Mama mia4", queue="run me"))

        mains = []
        mains.append(odict(house="Papa pia1", queue="fix me"))
        mains.append(odict(house="Papa pia2", queue="help me"))
        mains.append(odict(house="Papa pia3", queue="stop me"))
        mains.append(odict(house="Papa pia4", queue="run me"))

        self.bidirectional(bk=raeting.BodyKind.msgpack.value, mains=mains, others=others)

    def testSegmentedJson(self):
        '''
        Test segmented message transactions
        '''
        console.terse("{0}\n".format(self.testSegmentedJson.__doc__))

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        others = []
        mains = []
        others.append(odict(house="Snake eyes", queue="near stuff", stuff=stuff))
        mains.append(odict(house="Craps", queue="far stuff", stuff=stuff))

        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        others.append(odict(house="Other", queue="big stuff", bloat=bloat))
        mains.append(odict(house="Main", queue="gig stuff", bloat=bloat))

        self.bidirectional(bk=raeting.BodyKind.json.value, mains=mains, others=others, duration=20.0)

    def testSegmentedMsgpack(self):
        '''
        Test segmented message transactions
        '''
        console.terse("{0}\n".format(self.testSegmentedMsgpack.__doc__))

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        others = []
        mains = []
        others.append(odict(house="Snake eyes", queue="near stuff", stuff=stuff))
        mains.append(odict(house="Craps", queue="far stuff", stuff=stuff))

        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        others.append(odict(house="Other", queue="big stuff", bloat=bloat))
        mains.append(odict(house="Main", queue="gig stuff", bloat=bloat))

        self.bidirectional(bk=raeting.BodyKind.msgpack.value, mains=mains, others=others, duration=20.0)

    def testSegmentedJsonBurst(self):
        '''
        Test segmented message transactions with burst count limiting
        '''
        console.terse("{0}\n".format(self.testSegmentedJsonBurst.__doc__))

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        others = []
        mains = []
        others.append(odict(house="Snake eyes", queue="near stuff", stuff=stuff))
        mains.append(odict(house="Craps", queue="far stuff", stuff=stuff))

        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        others.append(odict(house="Other", queue="big stuff", bloat=bloat))
        mains.append(odict(house="Main", queue="gig stuff", bloat=bloat))

        stacking.RoadStack.BurstSize = 16
        self.assertEqual(stacking.RoadStack.BurstSize, 16)
        self.bidirectional(bk=raeting.BodyKind.json.value, mains=mains, others=others, duration=20.0)
        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

    def testSegmentedMsgpackBurst(self):
        '''
        Test segmented message transactions with burst count limiting
        '''
        console.terse("{0}\n".format(self.testSegmentedMsgpackBurst.__doc__))

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)

        others = []
        mains = []
        others.append(odict(house="Snake eyes", queue="near stuff", stuff=stuff))
        mains.append(odict(house="Craps", queue="far stuff", stuff=stuff))

        bloat = []
        for i in range(300):
            bloat.append(str(i).rjust(100, " "))
        bloat = "".join(bloat)
        others.append(odict(house="Other", queue="big stuff", bloat=bloat))
        mains.append(odict(house="Main", queue="gig stuff", bloat=bloat))

        stacking.RoadStack.BurstSize = 16
        self.assertEqual(stacking.RoadStack.BurstSize, 16)
        self.bidirectional(bk=raeting.BodyKind.msgpack.value, mains=mains, others=others, duration=20.0)
        stacking.RoadStack.BurstSize = 0
        self.assertEqual(stacking.RoadStack.BurstSize, 0)

    def testJoinForever(self):
        '''
        Test other joining with timeout set to 0.0 and default
        '''
        console.terse("{0}\n".format(self.testJoinForever.__doc__))
        self.other.addRemote(estating.RemoteEstate(stack=self.other,
                                                   fuid=0, # vacuous join
                                                   sid=0, # always 0 for join
                                                   ha=self.main.local.ha))
        self.other.join(timeout=0.0) #attempt to join forever with timeout 0.0
        self.serviceOther(duration=20.0, real=False) # only service other so no response

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(self.main.remotes), 0)

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 1)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 1)
        remote = self.other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.uid, 2)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))


        console.terse("{0} Stats\n".format(self.main.name))
        for key, val in self.main.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(len(self.main.stats), 0)

        console.terse("{0} Stats\n".format(self.other.name))
        for key, val in self.other.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.other.stats.get('joiner_tx_join_redo'), 6)

        # Now allow join to complete
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertTrue(len(self.main.nameRemotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 1)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.other.remotes)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertTrue(len(self.other.nameRemotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

        # Now try again with existing remote data
        self.other.join(timeout=0.0) #attempt to join forever with timeout 0.0
        self.serviceOther(duration=20.0, real=False) # only service other so no response

        # main will still have join results from previous join transaction
        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertTrue(len(self.main.nameRemotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        # Other will have outstanding join transaction
        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 1)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 1)
        remote = self.other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.other.remotes)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertTrue(len(self.other.nameRemotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

        console.terse("{0} Stats\n".format(self.main.name))
        for key, val in self.main.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.main.stats.get('join_correspond_complete'), 1)

        console.terse("{0} Stats\n".format(self.other.name))
        for key, val in self.other.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.other.stats.get('joiner_tx_join_redo'), 12)
        self.assertEqual(self.other.stats.get('join_initiate_complete'), 1)

        # Now allow join to complete
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertTrue(len(self.main.nameRemotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 1)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.other.remotes)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertTrue(len(self.other.nameRemotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.nameRemotes)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

    def testStaleNack(self):
        '''
        Test stale nack
        '''
        console.terse("{0}\n".format(self.testStaleNack.__doc__))

        self.join()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        console.terse("\nMessage transaction *********\n")
        body = odict(what="This is a message to the main estate. How are you", extra="I am fine.")
        self.other.txMsgs.append((body, self.other.remotes.values()[0].fuid, None))
        self.timer.restart(duration=1.0)
        while not self.timer.expired:
            self.other.serviceAllTx() # transmit but leave receives in socket buffer
            self.main.serviceAllRx() # receive but leave transmits in queue

            self.store.advanceStamp(0.1)
            time.sleep(0.1)

        self.assertEqual(len(self.main.transactions), 0) #completed
        self.assertEqual(len(self.other.transactions), 1) # waiting for ack

        remote = self.other.remotes.values()[0]
        remote.transactions = odict() #clear transactions so RX is stale correspondent
        self.assertEqual(len(self.other.transactions), 0) # no initated transaction

        self.timer.restart(duration=2.0)
        while not self.timer.expired:
            self.main.serviceAll() # transmit stale ack
            self.other.serviceAll() # recieve ack
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(self.other.transactions), 0)

        print("{0} Stats".format(self.main.name))
        for key, val in self.main.stats.items():
            print("   {0}={1}".format(key, val))
        print()
        print("{0} Stats".format(self.other.name))
        for key, val in self.other.stats.items():
            print("   {0}={1}".format(key, val))
        print()

        self.assertTrue(self.other.stats.get('stale_correspondent_attempt') >= 1)
        self.assertTrue(self.other.stats.get('stale_correspondent_nack') >= 1)
        self.assertTrue(self.main.stats.get('messagent_correspond_complete') >= 1)
        self.assertTrue(self.main.stats.get('stale_packet') >= 1)

    def testBasicAlive(self):
        '''
        Test basic alive transaction
        '''
        console.terse("{0}\n".format(self.testBasicAlive.__doc__))

        self.join()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow()
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertTrue(remote.alived)

        console.terse("\nAlive Other to Main *********\n")
        otherRemote = self.main.remotes.values()[0]
        mainRemote = self.other.remotes.values()[0]
        otherRemote.alived = None
        mainRemote.alived = None

        self.alive(self.other, self.main)
        self.assertEqual(len(self.main.transactions), 0)
        self.assertTrue(otherRemote.alived)
        self.assertEqual(len(self.other.transactions), 0)
        self.assertTrue(mainRemote.alived)

        console.terse("\nAlive Main to Other *********\n")
        self.alive(self.main, self.other)
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.alived)
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.alived)

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
    names = [
              'testBootstrapJson',
             'testBootstrapMsgpack',
             'testMsgBothwaysJson',
             'testMsgBothwaysMsgpack',
             'testSegmentedJson',
             'testSegmentedMsgpack',
             'testSegmentedJsonBurst',
             'testSegmentedMsgpackBurst',
             'testBasicAlive',
             'testStaleNack',
             'testJoinForever',
            ]
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
    #testStackUdp()
    #testStackUdp(bk=raeting.bodyKinds.msgpack)

    #runAll() #run all unittests

    runSome()#only run some

    #runOne('testJoinForever')
    #runOne('testBootstrapJson')
    #runOne('testBootstrapMsgpack')
