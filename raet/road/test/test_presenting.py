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

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self, name, base, auto=None):
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
        data['auto'] = auto

        return data

    def createRoadStack(self, data, eid=0, main=None, auto=None, ha=None):
        '''
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
                                   auto=auto if auto is not None else data['auto'],
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

    def alive(self, initiator, correspondent):
        '''
        Utility method to do alive. Call from test method.
        '''
        console.terse("\nAlive Transaction **************\n")
        initiator.alive(deid=correspondent.local.uid)
        self.service(correspondent, initiator)

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

    def serviceStack(self, stack, duration=1.0):
        '''
        Utility method to service queues for one stack. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            stack.serviceAll()
            if not (stack.transactions):
                break
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
            if all([not stack.transactions for stack in stacks]):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)


    def testAlive(self):
        '''
        Test basic alive transaction
        '''
        console.terse("{0}\n".format(self.testAlive.__doc__))

        mainData = self.createRoadData(name='main', base=self.base, auto=True)
        keeping.clearAllKeepSafe(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     eid=1,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other', base=self.base)
        keeping.clearAllKeepSafe(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))


        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        otherRemote = main.remotes[other.local.uid]
        mainRemote = other.remotes.values()[0]
        self.assertTrue(otherRemote.joined)
        self.assertTrue(mainRemote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        otherRemote = main.remotes[other.local.uid]
        mainRemote = other.remotes.values()[0]
        self.assertTrue(otherRemote.allowed)
        self.assertTrue(mainRemote.allowed)

        console.terse("\nAlive Other to Main *********\n")
        otherRemote = main.remotes[other.local.uid]
        mainRemote = other.remotes.values()[0]
        self.assertIs(otherRemote.alive, None)
        self.assertIs(mainRemote.alive, None)

        self.alive(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertTrue(otherRemote.alive)
        self.assertTrue(mainRemote.alive)

        console.terse("\nAlive Main to Other *********\n")
        otherRemote.alive = None
        mainRemote.alive = None
        self.assertIs(otherRemote.alive, None)
        self.assertIs(mainRemote.alive, None)

        self.alive(main, other)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertTrue(otherRemote.alive)
        self.assertTrue(mainRemote.alive)


        console.terse("\nDead Other from Main *********\n")
        self.assertTrue(otherRemote.alive)
        self.assertTrue(mainRemote.alive)
        main.alive(deid=other.local.uid)
        self.serviceStack(main, duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertFalse(otherRemote.alive)
        self.serviceStack(other, duration=3.0)

        console.terse("\nDead Main from Other *********\n")
        self.assertTrue(mainRemote.alive)
        other.alive(deid=main.local.uid)
        self.serviceStack(other, duration=3.0)
        self.assertEqual(len(other.transactions), 0)
        self.assertFalse(mainRemote.alive)
        self.serviceStack(main, duration=3.0)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()


    def testAliveMultiple(self):
        '''
        Test alive transaction with multiple remotes
        '''
        console.terse("{0}\n".format(self.testAliveMultiple.__doc__))

        mainData = self.createRoadData(name='main', base=self.base, auto=True)
        keeping.clearAllKeepSafe(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     eid=1,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other', base=self.base)
        keeping.clearAllKeepSafe(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))


        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        otherRemote = main.remotes[other.local.uid]
        mainRemote = other.remotes.values()[0]
        self.assertTrue(otherRemote.joined)
        self.assertTrue(mainRemote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        otherRemote = main.remotes[other.local.uid]
        mainRemote = other.remotes.values()[0]
        self.assertTrue(otherRemote.allowed)
        self.assertTrue(mainRemote.allowed)


        other1Data = self.createRoadData(name='other1', base=self.base)
        keeping.clearAllKeepSafe(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", 7532))


        self.join(other1, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)
        other1Remote = main.remotes[other1.local.uid]
        main1Remote = other1.remotes.values()[0]
        self.assertTrue(other1Remote.joined)
        self.assertTrue(main1Remote.joined)

        self.allow(other1, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)
        other1Remote = main.remotes[other1.local.uid]
        main1Remote = other1.remotes.values()[0]
        self.assertTrue(other1Remote.allowed)
        self.assertTrue(main1Remote.allowed)

        console.terse("\nAlive Other to Main *********\n")
        self.assertIs(otherRemote.alive, None)
        self.assertIs(mainRemote.alive, None)

        self.alive(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertTrue(otherRemote.alive)
        self.assertTrue(mainRemote.alive)

        console.terse("\nAlive Main to Other *********\n")
        otherRemote.alive = None
        mainRemote.alive = None
        self.assertIs(otherRemote.alive, None)
        self.assertIs(mainRemote.alive, None)

        self.alive(main, other)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertTrue(otherRemote.alive)
        self.assertTrue(mainRemote.alive)

        console.terse("\nAlive Other1 to Main *********\n")
        self.assertIs(other1Remote.alive, None)
        self.assertIs(main1Remote.alive, None)

        self.alive(other1, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)
        self.assertTrue(other1Remote.alive)
        self.assertTrue(main1Remote.alive)

        console.terse("\nAlive Main to Other1 *********\n")
        other1Remote.alive = None
        main1Remote.alive = None
        self.assertIs(other1Remote.alive, None)
        self.assertIs(main1Remote.alive, None)

        self.alive(main, other1)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)
        self.assertTrue(other1Remote.alive)
        self.assertTrue(main1Remote.alive)

        console.terse("\nDead Other Alive Other1, from Main *********\n")
        self.assertTrue(otherRemote.alive)
        self.assertTrue(other1Remote.alive)
        main.alive(deid=other.local.uid)
        main.alive(deid=other1.local.uid)
        self.serviceStacks([main, other1], duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other1.transactions), 0)
        self.assertFalse(otherRemote.alive)
        self.assertTrue(other1Remote.alive)
        self.serviceStacks([other, main], duration=3.0)

        console.terse("\nAlive Other Dead Other 1 from Main *********\n")
        main.alive(deid=other.local.uid)
        main.alive(deid=other1.local.uid)
        self.serviceStacks([main, other], duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertFalse(other1Remote.alive)
        self.assertTrue(otherRemote.alive)
        self.serviceStacks([other1,  main], duration=3.0)

        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

        other1.server.close()
        other1.clearLocal()
        other1.clearRemoteKeeps()

    def testRemoteProcess(self):
        '''
        Test alive transaction with multiple remotes
        '''
        console.terse("{0}\n".format(self.testRemoteProcess.__doc__))

        mainData = self.createRoadData(name='main', base=self.base, auto=True)
        keeping.clearAllKeepSafe(mainData['dirpath'])
        main = self.createRoadStack(data=mainData,
                                     eid=1,
                                     main=True,
                                     auto=mainData['auto'],
                                     ha=None)

        otherData = self.createRoadData(name='other', base=self.base)
        keeping.clearAllKeepSafe(otherData['dirpath'])
        other = self.createRoadStack(data=otherData,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        other1Data = self.createRoadData(name='other1', base=self.base)
        keeping.clearAllKeepSafe(other1Data['dirpath'])
        other1 = self.createRoadStack(data=other1Data,
                                     eid=0,
                                     main=None,
                                     auto=None,
                                     ha=("", 7532))


        self.join(other, main)
        self.join(other1, main)
        self.allow(other, main)
        self.allow(other1, main)

        console.terse("\nTest process remotes presence *********\n")
        console.terse("\nMake all alive *********\n")
        stacks = [main, other, other1]
        for remote in main.remotes.values(): #make all alive
            main.alive(deid=remote.uid)
        self.serviceStacks(stacks, duration=3.0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alive)

        main.manage()
        for stack in stacks: # no alive transactions started
            self.assertEqual(len(stack.transactions), 0)

        console.terse("\nMake all expired so send alive *********\n")
        # advance clock so remote keep alive timers expire
        self.store.advanceStamp(estating.RemoteEstate.Period + estating.RemoteEstate.Offset)
        main.manage()
        for remote in main.remotes.values(): # should start
            self.assertIs(remote.alive, None)

        self.assertEqual(len(main.transactions), 2) # started 2 alive transactions

        self.serviceStacks(stacks, duration=3.0)
        for stack in stacks:
            self.assertEqual(len(stack.transactions), 0)
        for remote in main.remotes.values():
            self.assertTrue(remote.alive)


        main.server.close()
        main.clearLocal()
        main.clearRemoteKeeps()

        other.server.close()
        other.clearLocal()
        other.clearRemoteKeeps()

        other1.server.close()
        other1.clearLocal()
        other1.clearRemoteKeeps()

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
    names = ['testAlive',
             'testAliveMultiple',
             'testRemoteProcess', ]

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

    #runOne('testRemoteProcess')

