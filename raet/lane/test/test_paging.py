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

from ioflo.aid.odicting import odict
from ioflo.aid.timing import Timer, StoreTimer
from ioflo.base.storing import Store

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from raet.abiding import *  # import globals
from raet import raeting, nacling
from raet.lane import paging, yarding, stacking

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass


class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

    def tearDown(self):
        pass

    def testPackParseJson(self):
        '''
        Test basic page pack and parse
        '''
        console.terse("{0}\n".format(self.testPackParseJson.__doc__))
        data = odict(pk=raeting.PackKind.json.value)
        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
        route = odict([('src', src), ('dst', dst)])

        body = odict([('route', route), ('content', "Hello all yards.")])
        page0 = paging.TxPage(data=data, embody=body)
        self.assertDictEqual(page0.body.data, body)
        page0.pack()
        self.assertEqual(len(page0.packed), 169)
        self.assertEqual(page0.packed, b'ri RAET\nvn 0\npk 0\nsn \ndn \nsi 000000000000000000\nbi 0\npn 0000\npc 0001\n\n{"route":{"src":["mayor","main",null],"dst":["citizen","other",null]},"content":"Hello all yards."}')
        page1 = paging.RxPage(packed=page0.packed)
        page1.parse()
        self.assertDictEqual(page1.body.data, body)

        stuff = []
        for i in range(10000):
            stuff.append(str(i).rjust(10, " "))
        stuff = "".join(stuff)
        body = odict(msg=stuff)
        page0 = paging.TxPage(data=data, embody=body)
        self.assertRaises(raeting.PageError, page0.pack)

        sid = nacling.uuid(size=18)
        data.update(odict(sn="boy", dn='girl', si=sid, bi=1))
        book0 = paging.TxBook(data=data, body=body)
        book0.pack()
        self.assertEqual(len(book0.pages), 2)
        self.assertEqual(book0.packed, page0.body.packed)
        self.assertDictEqual(book0.pages[0].data, {'ri': 'RAET',
                                                   'vn': 0,
                                                   'pk': 0,
                                                   'sn': 'boy',
                                                   'dn': 'girl',
                                                   'si': sid,
                                                   'bi': 1,
                                                   'pn': 0,
                                                   'pc': 2})
        self.assertEqual(len(book0.pages[0].packed), 65533)
        self.assertDictEqual(book0.pages[1].data, {'ri': 'RAET',
                                                   'vn': 0,
                                                   'pk': 0,
                                                   'sn': 'boy',
                                                   'dn': 'girl',
                                                   'si': sid,
                                                   'bi': 1,
                                                   'pn': 1,
                                                   'pc': 2})
        self.assertEqual(len(book0.pages[1].packed), 34631)
        self.assertEqual(book0.index, ('boy', 'girl', sid, 1))

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed) # simulate received packed
            page.head.parse() #parse head to get data
            book1.parse(page)

        self.assertDictEqual(body, book1.body)
        self.assertDictEqual(book1.data, {'ri': 'RAET',
                                          'vn': 0,
                                          'pk': 0,
                                          'sn': 'boy',
                                          'dn': 'girl',
                                          'si': sid,
                                          'bi': 1,
                                          'pn': 0,
                                          'pc': 2})
        self.assertEqual(book1.index, ('girl', 'boy', sid, 1))

    def testPackParseMsgpack(self):
        '''
        Test basic page pack and parse
        '''
        console.terse("{0}\n".format(self.testPackParseMsgpack.__doc__))
        data = odict(pk=raeting.PackKind.pack.value)
        sid = nacling.uuid(size=18)
        data.update(odict(sn="boy", dn='girl', si=sid, bi=1))
        src = ['mayor', 'main', None]
        dst = ['citizen', 'other', None]
        route = odict([('src', src), ('dst', dst)])

        body = odict([('route', route), ('content', "Hello all yards.")])
        page0 = paging.TxPage(data=data, embody=body)
        self.assertDictEqual(page0.body.data, body)
        page0.pack()
        self.assertEqual(len(page0.packed), 147)
        self.assertEqual(page0.packed, ns2b('ri RAET\nvn 0\npk 1\nsn boy\ndn girl\nsi {0:.18s}\nbi 1\npn 0000\npc 0001\n\n\x82\xa5route\x82\xa3src\x93\xa5mayor\xa4main\xc0\xa3dst\x93\xa7citizen\xa5other\xc0\xa7content\xb0Hello all yards.'.format(sid)))
        page1 = paging.RxPage(packed=page0.packed)
        page1.parse()
        self.assertDictEqual(page1.body.data, body)

    def testSectionedJson(self):
        '''
        Test sectioned pack and parse json packing
        '''
        console.terse("{0}\n".format(self.testSectionedJson.__doc__))
        data = odict(pk=raeting.PackKind.json.value)
        sid = nacling.uuid(size=18)
        data.update(odict(sn="boy", dn='girl', si=sid, bi=1))
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
        page0 = paging.TxPage(data=data, embody=body)
        self.assertDictEqual(page0.body.data, body)
        self.assertRaises(raeting.PageError, page0.pack)

        book0 = paging.TxBook(data=data, body=body)
        book0.pack()
        self.assertEqual(len(book0.packed), 100083)
        self.assertEqual(len(book0.pages), 2)
        self.assertEqual(book0.index, ('boy', 'girl', sid, 1))

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed)
            page.head.parse() #parse head to get data
            book1.parse(page)

        self.assertEqual(book1.index, ('girl', 'boy', sid, 1))
        self.assertDictEqual(book1.body, body)
        self.assertEqual(book1.data['sn'], 'boy')
        self.assertEqual(book1.data['dn'], 'girl')
        self.assertEqual(book1.data['si'], sid)
        self.assertEqual(book1.data['bi'], 1)

    def testSectionedMsgpack(self):
        '''
        Test sectioned pack and parse msgpack packing
        '''
        console.terse("{0}\n".format(self.testSectionedMsgpack.__doc__))
        data = odict(pk=raeting.PackKind.pack.value)
        sid = nacling.uuid(size=18)
        data.update(odict(sn="boy", dn='girl', si=sid, bi=1))
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
        page0 = paging.TxPage(data=data, embody=body)
        self.assertDictEqual(page0.body.data, body)
        self.assertRaises(raeting.PageError, page0.pack)

        book0 = paging.TxBook(data=data, body=body)
        book0.pack()
        self.assertEqual(len(book0.packed), 100058)
        self.assertEqual(len(book0.pages), 2)
        self.assertEqual(book0.index, ('boy', 'girl', sid, 1))

        book1 = paging.RxBook()
        for page in book0.pages:
            page = paging.RxPage(packed=page.packed)
            page.head.parse() #parse head to get data
            book1.parse(page)

        self.assertEqual(book1.index, ('girl', 'boy', sid, 1))
        self.assertDictEqual(book1.body, body)
        self.assertEqual(book1.data['sn'], 'boy')
        self.assertEqual(book1.data['dn'], 'girl')
        self.assertEqual(book1.data['si'], sid)
        self.assertEqual(book1.data['bi'], 1)


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

    #runOne('testPackParseJson')
