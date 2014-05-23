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

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import keeping, estating, stacking, transacting

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.baseDirpath=tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')
        stacking.RoadStack.Bk = raeting.bodyKinds.json

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


        keeping.clearAllKeepSafe(mainDirpath)
        keeping.clearAllKeepSafe(otherDirpath)

        local = estating.LocalEstate(eid=1,
                                     name=mainName,
                                     sigkey=mainSignKeyHex,
                                     prikey=mainPriKeyHex,)

        self.main = stacking.RoadStack(name=mainName,
                                         local=local,
                                         auto=True,
                                         main=True,
                                         dirpath=mainDirpath,
                                         store=self.store)

        local = estating.LocalEstate(eid=0,
                                     name=otherName,
                                     ha=("", raeting.RAET_TEST_PORT),
                                     sigkey=otherSignKeyHex,
                                     prikey=otherPriKeyHex,)

        self.other = stacking.RoadStack(name=otherName,
                                         local=local,
                                         dirpath=otherDirpath,
                                         store=self.store)



    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

        self.main.clearLocal()
        self.main.clearRemoteKeeps()
        self.other.clearLocal()
        self.other.clearRemoteKeeps()

        if os.path.exists(self.baseDirpath):
            shutil.rmtree(self.baseDirpath)


    def join(self, mha=None, timeout=None):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        self.other.join(mha=mha, timeout=timeout)
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
        initiator.alive(deid=correspondent.local.uid)
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


    def bootstrap(self, bk=raeting.bodyKinds.json):
        '''
        Initialize
            main on port 7530 with eid of 1
            other on port 7531 with eid of 0
        Complete
            main eid of 1 joined and allowed
            other eid of 2 joined and allowed
        '''
        stacking.RoadStack.Bk = bk

        self.assertEqual(self.main.name, 'main')
        self.assertEqual(self.main.local.name, 'main')
        self.assertEqual(self.main.local.ha, ("0.0.0.0", raeting.RAET_PORT))

        self.assertEqual(self.other.name, 'other')
        self.assertEqual(self.other.local.name, 'other')
        self.assertEqual(self.other.local.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        self.join()
        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(remote.uid in self.main.remotes)
        self.assertTrue(len(self.main.uids), 1)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertEqual(len(remote.indexes), 0)
        self.assertTrue('other' in self.main.uids)
        self.assertIs(self.main.remotes[self.main.uids[remote.name]], remote)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 2)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 1)
        self.assertTrue(1 in self.other.remotes)
        self.assertTrue(remote.uid in self.other.remotes)
        self.assertTrue(len(self.other.uids), 1)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertEqual(len(remote.indexes), 0)
        self.assertTrue('main' in self.other.uids)
        self.assertIs(self.other.remotes[self.other.uids[remote.name]], remote)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

        self.allow()
        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        remote = self.main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(remote.uid, 2)
        self.assertTrue(2 in self.main.remotes)
        self.assertTrue(len(self.main.uids), 1)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertEqual(len(remote.indexes), 0)
        self.assertTrue('other' in self.main.uids)
        console.terse("Stack '{0}' estate name '{1}' allowd with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.allowed))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 2)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(remote.uid, 1)
        self.assertTrue(1 in self.other.remotes)
        self.assertTrue(len(self.other.uids), 1)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertEqual(len(remote.indexes), 0)
        self.assertTrue('main' in self.other.uids)
        console.terse("Stack '{0}' estate name '{1}' allowed with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.allowed))

        console.terse("\nMessage: other to main *********\n")
        body = odict(what="This is a message to the main estate. How are you", extra="I am fine.")
        self.other.txMsgs.append((body, self.main.local.uid))
        #self.other.message(body=body, deid=self.main.local.uid)
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(len(self.main.transactions), 0)
        for msg in self.main.rxMsgs:
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.main.local.name, msg))
        self.assertDictEqual(body, self.main.rxMsgs[0])

        console.terse("\nMessage: main to other *********\n")
        body = odict(what="This is a message to the other estate. Get to Work", extra="Fix the fence.")
        self.main.txMsgs.append((body, self.other.local.uid))
        #self.main.message(body=body, deid=self.other.local.uid)
        self.service()

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(len(self.other.transactions), 0)
        for msg in self.other.rxMsgs:
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.other.local.name, msg))
        self.assertDictEqual(body, self.other.rxMsgs[0])

    def bidirectional(self, bk=raeting.bodyKinds.json, mains=None, others=None, duration=3.0):
        '''
        Initialize
            main on port 7530 with eid of 1
            other on port 7531 with eid of 0
        Complete
            main eid of 1 joined and allowed
            other eid of 2 joined and allowed
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
            #self.main.txMsgs.append((msg, None))
            #self.main.message(body=msg, deid=self.other.local.uid)
        for msg in others:
            self.other.transmit(msg)
            #self.other.txMsgs.append((msg, None))
            #self.other.message(body=msg, deid=self.main.local.uid)

        self.service(duration=duration)

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(others), len(self.main.rxMsgs))
        for i, msg in enumerate(self.main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.main.local.name, msg))
            self.assertDictEqual(others[i], msg)

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(len(self.other.transactions), 0)
        self.assertEqual(len(mains), len(self.other.rxMsgs))
        for i, msg in enumerate(self.other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(self.other.local.name, msg))
            self.assertDictEqual(mains[i], msg)

    def testBootstrapJson(self):
        '''
        Test join allow message transactions with JSON Serialization of body
        '''
        console.terse("{0}\n".format(self.testBootstrapJson.__doc__))
        self.bootstrap(bk=raeting.bodyKinds.json)

    def testBootstrapMsgpack(self):
        '''
        Test join allow message transactions with MsgPack Serialization of body
        '''
        console.terse("{0}\n".format(self.testBootstrapMsgpack.__doc__))
        self.bootstrap(bk=raeting.bodyKinds.msgpack)

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

        self.bidirectional(bk=raeting.bodyKinds.json, mains=mains, others=others)

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

        self.bidirectional(bk=raeting.bodyKinds.msgpack, mains=mains, others=others)

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

        self.bidirectional(bk=raeting.bodyKinds.json, mains=mains, others=others)

    def testSegmentedMsgpack(self):
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

        self.bidirectional(bk=raeting.bodyKinds.msgpack, mains=mains, others=others)

    def testJoinForever(self):
        '''
        Test other joining with timeout set to 0.0 and default
        '''
        console.terse("{0}\n".format(self.testJoinForever.__doc__))

        self.other.join(timeout=0.0) #attempt to join forever with timeout 0.0
        self.serviceOther(duration=20.0, real=False) # only service other so no response

        console.terse("\nStack '{0}' uid= {1}\n".format(self.main.name, self.main.local.uid))
        self.assertEqual(self.main.local.uid, 1)
        self.assertEqual(self.main.name, 'main')
        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(self.main.remotes), 0)

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 0)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 1)
        remote = self.other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.uid, 0)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))


        console.terse("{0} Stats\n".format(self.main.name))
        for key, val in self.main.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(len(self.main.stats), 0)

        console.terse("{0} Stats\n".format(self.other.name))
        for key, val in self.other.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.other.stats.get('redo_join'), 6)

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
        self.assertTrue(len(self.main.uids), 1)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.uids)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 2)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 1)
        self.assertTrue(1 in self.other.remotes)
        self.assertTrue(len(self.other.uids), 1)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.uids)
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
        self.assertTrue(len(self.main.uids), 1)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.uids)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        # Other will have outstanding join transaction
        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 2)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 1)
        remote = self.other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.uid, 1)
        self.assertTrue(1 in self.other.remotes)
        self.assertTrue(len(self.other.uids), 1)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.uids)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.other.name, self.other.local.name, remote.name, remote.joined))

        console.terse("{0} Stats\n".format(self.main.name))
        for key, val in self.main.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.main.stats.get('join_correspond_complete'), 1)

        console.terse("{0} Stats\n".format(self.other.name))
        for key, val in self.other.stats.items():
            console.terse("   {0}={1}\n".format(key, val))
        self.assertEqual(self.other.stats.get('redo_join'), 12)
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
        self.assertTrue(len(self.main.uids), 1)
        self.assertTrue(len(self.main.remotes), 1)
        self.assertEqual(remote.name, 'other')
        self.assertTrue('other' in self.main.uids)
        console.terse("Stack '{0}' estate name '{1}' joined with '{2}' = {3}\n".format(
                self.main.name, self.main.local.name, remote.name, remote.joined))

        console.terse("\nStack '{0}' uid= {1}\n".format(self.other.name, self.other.local.uid))
        self.assertEqual(self.other.local.uid, 2)
        self.assertEqual(self.other.name, 'other')
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.uid, 1)
        self.assertTrue(1 in self.other.remotes)
        self.assertTrue(len(self.other.uids), 1)
        self.assertTrue(len(self.other.remotes), 1)
        self.assertEqual(remote.name, 'main')
        self.assertTrue('main' in self.other.uids)
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
        self.other.txMsgs.append((body, self.main.local.uid))
        self.timer.restart(duration=1.0)
        while not self.timer.expired:
            self.other.serviceAllTx() # transmit but leave receives in socket buffer
            self.main.serviceAllRx() # receive but leave transmits in queue

            self.store.advanceStamp(0.1)
            time.sleep(0.1)

        self.assertEqual(len(self.main.transactions), 0) #completed
        self.assertEqual(len(self.other.transactions), 1) # waiting for ack

        self.other.transactions = odict() #clear transactions so RX is stale correspondent
        self.assertEqual(len(self.other.transactions), 0) # no initated transaction

        self.timer.restart(duration=2.0)
        while not self.timer.expired:
            self.main.serviceAll() # transmit stale ack
            self.other.serviceAll() # recieve ack
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

        self.assertEqual(len(self.main.transactions), 0)
        self.assertEqual(len(self.other.transactions), 0)

        print "{0} Stats".format(self.main.name)
        for key, val in self.main.stats.items():
            print "   {0}={1}".format(key, val)
        print
        print "{0} Stats".format(self.other.name)
        for key, val in self.other.stats.items():
            print "   {0}={1}".format(key, val)
        print

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
        self.assertEqual(len(self.other.transactions), 0)
        remote = self.other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        console.terse("\nAlive Other to Main *********\n")
        otherRemote = self.main.remotes.values()[0]
        mainRemote = self.other.remotes.values()[0]
        self.assertIs(otherRemote.alived, None)
        self.assertIs(mainRemote.alived, None)

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
    names = ['testBootstrapJson',
             'testBootstrapMsgpack',
             'testMsgBothwaysJson',
             'testMsgBothwaysMsgpack',
             'testSegmentedJson',
             'testSegmentedMsgpack',
             'testJoinForever',
             'testStaleNack',
             'testBasicAlive', ]
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

    runAll() #run all unittests

    #runSome()#only run some

    #runOne('testAlive')
