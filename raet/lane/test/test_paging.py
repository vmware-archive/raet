# -*- coding: utf-8 -*-
'''
Tests to try out paging. Potentially ephemeral

'''
# pylint: skip-file
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import time
from collections import deque

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting
from raet.lane import paging, yarding, stacking

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass




def test( pk=raeting.packKinds.json):
    '''
    Test paging.
    '''
    console.reinit(verbosity=console.Wordage.concise)

    #data = odict(hk=hk, bk=bk)
    body = odict(raeting.PAGE_DEFAULTS)
    page0 = paging.TxPage(kind=pk, data=body)
    print page0.data
    page0.pack()
    print len(page0.packed)
    print page0.packed
    page1 = paging.RxPage(packed=page0.packed)
    page1.parse()
    print page1.data

    stuff = []
    for i in range(10000):
        stuff.append(str(i).rjust(10, " "))
    stuff = "".join(stuff)
    body = odict(msg=stuff)
    page0 = paging.TxPage(kind=pk, data=body)
    try:
        page0.pack()
    except raeting.PageError as ex:
        print ex
        print "Need to use book"

    data = odict(syn="boy", dyn='girl', mid=1)
    book0 = paging.TxBook(data=data, body=body, kind=pk)
    book0.pack()
    print book0.packed
    print book0.pages

    book1 = paging.RxBook()
    for page in book0.pages:
        page = paging.RxPage(packed=page.packed)
        page.parse()
        book1.parse(page)

    print book1.data
    print book1.body

    print body == book1.body

    stacking.LaneStack.Pk = pk
    store = storing.Store(stamp=0.0)

    #lord stack
    stack0 = stacking.LaneStack(store=store)

    #serf stack
    stack1 = stacking.LaneStack(store=store)

    stack0.addRemote(yarding.RemoteYard(ha=stack1.local.ha))
    stack1.addRemote(yarding.RemoteYard(ha=stack0.local.ha))

    print "{0} local name={1} ha={2}".format(stack0.name, stack0.local.name, stack0.local.ha)
    print "{0} remotes=\n{1}".format(stack0.name, stack0.remotes)
    print "{0} uids=\n{1}".format(stack0.name, stack0.uids)

    print "{0} local name={1} ha={2}".format(stack1.name, stack1.local.name, stack1.local.ha)
    print "{0} remotes=\n{1}".format(stack1.name, stack1.yards)
    print "{0} uids=\n{1}".format(stack1.name, stack1.uids)

    print "\n____________ Messaging through stack tests "

    msg = odict(stuff=stuff)
    stack0.transmit(msg=body)

    msg = odict(what="This is a message to the serf. Get to Work", extra="Fix the fence.")
    stack0.transmit(msg=msg)

    msg = odict(what="This is a message to the lord. Let me be", extra="Go away.")
    stack1.transmit(msg=msg)



    timer = Timer(duration=0.5)
    timer.restart()
    while not timer.expired or store.stamp < 1.0:
        stack0.serviceAll()
        stack1.serviceAll()
        store.advanceStamp(0.1)

    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print


    stack0.server.close()
    stack1.server.close()


#if __name__ == "__main__":
    #test(pk=raeting.packKinds.pack)
    #test(pk=raeting.packKinds.json)

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        # main stack
        self.main = stacking.LaneStack(name='main',
                                    lanename='cherry',
                                    yardname='main',
                                    dirpath='/tmp/raet/lane',
                                    sockdirpath='/tmp/raet/lane')

        #other stack
        self.other = stacking.LaneStack(name='other',
                                    lanename='cherry',
                                    yardname='other',
                                    dirpath='/tmp/raet/lane',
                                    sockdirpath='/tmp/raet/lane')

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


    def testPackParseJson(self):
        '''
        Test basic page pack and parse
        '''
        console.terse("{0}\n".format(self.testPackParseJson.__doc__))
        pk = raeting.packKinds.json

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        body = odict([('route', route), ('content', "Hello all yards.")])
        page0 = paging.TxPage(kind=pk, data=body)
        self.assertDictEqual(page0.data, body)
        page0.pack()
        self.assertEqual(len(page0.packed), 110)
        self.assertEqual(page0.packed, 'RAET\njson\n\n{"route":{"src":["mayor","main",null],"dst":["citizen","other",null]},"content":"Hello all yards."}')

        page1 = paging.RxPage(packed=page0.packed)
        page1.parse()
        self.assertDictEqual(page1.data, body)


        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        body = odict(msg=stuff)
        page0 = paging.TxPage(kind=pk, data=body)
        try:
            page0.pack()
        except raeting.PageError as ex:
            print ex
            print "Need to use book"

        data = odict(syn="boy", dyn='girl', mid=1)
        book0 = paging.TxBook(data=data, body=body, kind=pk)
        book0.pack()
        print book0.packed
        print book0.pages

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed)
            page.parse()
            book1.parse(page)

        print book1.data
        print book1.body

        print body == book1.body

    def testPackParseMsgpack(self):
        '''
        Test basic page pack and parse
        '''
        console.terse("{0}\n".format(self.testPackParseMsgpack.__doc__))
        pk = raeting.packKinds.pack

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        body = odict([('route', route), ('content', "Hello all yards.")])
        page0 = paging.TxPage(kind=pk, data=body)
        self.assertDictEqual(page0.data, body)
        page0.pack()
        self.assertEqual(len(page0.packed), 81)
        self.assertEqual(page0.packed, 'RAET\npack\n\n\x82\xa5route\x82\xa3src\x93\xa5mayor\xa4main\xc0\xa3dst\x93\xa7citizen\xa5other\xc0\xa7content\xb0Hello all yards.')

        page1 = paging.RxPage(packed=page0.packed)
        page1.parse()
        self.assertDictEqual(page1.data, body)


    def testSectionedJson(self):
        '''
        Test sectioned pack and parse json packing
        '''
        console.terse("{0}\n".format(self.testSectionedJson.__doc__))
        pk = raeting.packKinds.json

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        self.assertEqual(len(stuff), 100000)
        self.assertTrue(len(stuff) > raeting.UXD_MAX_PACKET_SIZE)

        body = odict([('route', route), ('content', stuff)])
        page0 = paging.TxPage(kind=pk, data=body)
        self.assertDictEqual(page0.data, body)
        self.assertRaises(raeting.PageError, page0.pack)


        data = odict(syn="boy", dyn='girl', mid=1)
        book0 = paging.TxBook(data=data, body=body, kind=pk)
        book0.pack()
        self.assertEqual(len(book0.packed), 100083)
        self.assertEqual(len(book0.pages), 2)
        self.assertEqual(book0.index, ('boy', 'girl', 1))

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed)
            page.parse()
            book1.parse(page)

        self.assertEqual(book1.index, ('girl', 'boy', 1))
        self.assertDictEqual(book1.body, body)
        self.assertEqual(book1.data['syn'], 'boy')
        self.assertEqual(book1.data['dyn'], 'girl')
        self.assertEqual(book1.data['mid'], 1)

    def testSectionedMsgpack(self):
        '''
        Test sectioned pack and parse msgpack packing
        '''
        console.terse("{0}\n".format(self.testSectionedMsgpack.__doc__))
        pk = raeting.packKinds.pack

        src = ['mayor', self.main.local.name, None]
        dst = ['citizen', self.other.local.name, None]
        route = odict([('src', src), ('dst', dst)])

        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        self.assertEqual(len(stuff), 100000)
        self.assertTrue(len(stuff) > raeting.UXD_MAX_PACKET_SIZE)

        body = odict([('route', route), ('content', stuff)])
        page0 = paging.TxPage(kind=pk, data=body)
        self.assertDictEqual(page0.data, body)
        self.assertRaises(raeting.PageError, page0.pack)


        data = odict(syn="boy", dyn='girl', mid=1)
        book0 = paging.TxBook(data=data, body=body, kind=pk)
        book0.pack()
        self.assertEqual(len(book0.packed), 100058)
        self.assertEqual(len(book0.pages), 2)
        self.assertEqual(book0.index, ('boy', 'girl', 1))

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed)
            page.parse()
            book1.parse(page)

        self.assertEqual(book1.index, ('girl', 'boy', 1))
        self.assertDictEqual(book1.body, body)
        self.assertEqual(book1.data['syn'], 'boy')
        self.assertEqual(book1.data['dyn'], 'girl')
        self.assertEqual(book1.data['mid'], 1)


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
    names = ['testPackParseJson',
             'testPackParseMsgpack',
             'testSectionedJson',
             'testSectionedMsgpack', ]
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

    #runOne('testPackParse')
