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


class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)


    def tearDown(self):
        pass



    def testPackParseJson(self):
        '''
        Test basic page pack and parse
        '''
        console.terse("{0}\n".format(self.testPackParseJson.__doc__))
        pk = raeting.packKinds.json

        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
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

        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
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

        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
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

        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
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
