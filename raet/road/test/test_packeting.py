# -*- coding: utf-8 -*-
'''
Tests to try out packeting. Potentially ephemeral

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
from raet.road import keeping, packeting, estating, stacking, transacting

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

def tempbasedir(prefix='', suffix='', dir='', lane='', keep=''):
    return tempfile.mkdtemp(prefix=prefix, suffix=suffix)

class BasicTestCase(unittest.TestCase):
    '''
    Basic pack and parse
    '''

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

    def tearDown(self):
        pass

    def testBasicJson(self):
        '''
        Basic pack parse with header json and body json
        '''
        console.terse("{0}\n".format(self.testBasicJson.__doc__))

        hk = raeting.headKinds.json
        bk = raeting.bodyKinds.json

        data = odict(hk=hk, bk=bk)
        body = odict(msg='Hello Raet World', extra='Goodby Big Moon')
        packet0 = packeting.TxPacket(embody=body, data=data, )
        self.assertDictEqual(packet0.body.data, body)
        packet0.pack()
        self.assertEqual(packet0.packed,
                '{"ri":"RAET","pl":"000006c","hl":"38","hk":1,"bk":1}\r\n\r\n{"msg":"Hello Raet World","extra":"Goodby Big Moon"}')

        packet1 = packeting.RxPacket(packed=packet0.packed)
        packet1.parse()
        self.assertDictEqual(packet1.data, {'sh': '',
                                            'sp': 7530,
                                            'dh': '127.0.0.1',
                                            'dp': 7530,
                                            'ri':'RAET',
                                            'vn': 0,
                                            'pk': 0,
                                            'pl': 108,
                                            'hk': 1,
                                            'hl': 56,
                                            'se': 0,
                                            'de': 0,
                                            'cf': False,
                                            'bf': False,
                                            'si': 0,
                                            'ti': 0,
                                            'tk': 0,
                                            'dt': 0,
                                            'oi': 0,
                                            'wf': False,
                                            'sn': 0,
                                            'sc': 1,
                                            'ml': 0,
                                            'sf': False,
                                            'af': False,
                                            'bk': 1,
                                            'ck': 0,
                                            'fk': 0,
                                            'fl': 0,
                                            'fg': '00'})
        self.assertDictEqual(packet1.body.data, body)

    def testBasicMsgpack(self):
        '''
        Basic pack parse with header json and body msgpack
        '''
        console.terse("{0}\n".format(self.testBasicMsgpack.__doc__))

        hk = raeting.headKinds.json
        bk = raeting.bodyKinds.msgpack

        data = odict(hk=hk, bk=bk)
        body = odict(msg='Hello Raet World', extra='Goodby Big Moon')
        packet0 = packeting.TxPacket(embody=body, data=data, )
        self.assertDictEqual(packet0.body.data, body)
        packet0.pack()
        self.assertEqual(packet0.packed,
                '{"ri":"RAET","pl":"0000064","hl":"38","hk":1,"bk":3}\r\n\r\n\x82\xa3msg\xb0Hello Raet World\xa5extra\xafGoodby Big Moon')

        packet1 = packeting.RxPacket(packed=packet0.packed)
        packet1.parse()
        self.assertDictEqual(packet1.data, {'sh': '',
                                            'sp': 7530,
                                            'dh': '127.0.0.1',
                                            'dp': 7530,
                                            'ri':'RAET',
                                            'vn': 0,
                                            'pk': 0,
                                            'pl': 100,
                                            'hk': 1,
                                            'hl': 56,
                                            'se': 0,
                                            'de': 0,
                                            'cf': False,
                                            'bf': False,
                                            'si': 0,
                                            'ti': 0,
                                            'tk': 0,
                                            'dt': 0,
                                            'oi': 0,
                                            'wf': False,
                                            'sn': 0,
                                            'sc': 1,
                                            'ml': 0,
                                            'sf': False,
                                            'af': False,
                                            'bk': 3,
                                            'ck': 0,
                                            'fk': 0,
                                            'fl': 0,
                                            'fg': '00'})
        self.assertDictEqual(packet1.body.data, body)

    def testBasicRaetJson(self):
        '''
        Basic pack parse with header raet and body json
        '''
        console.terse("{0}\n".format(self.testBasicRaetJson.__doc__))

        hk = raeting.headKinds.raet
        bk = raeting.bodyKinds.json

        data = odict(hk=hk, bk=bk)
        body = odict(msg='Hello Raet World', extra='Goodby Big Moon')
        packet0 = packeting.TxPacket(embody=body, data=data, )
        self.assertDictEqual(packet0.body.data, body)
        packet0.pack()
        self.assertEqual(packet0.packed,
                'ri RAET\npl 0050\nhl 1c\nbk 1\n\n{"msg":"Hello Raet World","extra":"Goodby Big Moon"}')

        packet1 = packeting.RxPacket(packed=packet0.packed)
        packet1.parse()
        self.assertDictEqual(packet1.data, {'sh': '',
                                            'sp': 7530,
                                            'dh': '127.0.0.1',
                                            'dp': 7530,
                                            'ri':'RAET',
                                            'vn': 0,
                                            'pk': 0,
                                            'pl': 80,
                                            'hk': 0,
                                            'hl': 28,
                                            'se': 0,
                                            'de': 0,
                                            'cf': False,
                                            'bf': False,
                                            'si': 0,
                                            'ti': 0,
                                            'tk': 0,
                                            'dt': 0,
                                            'oi': 0,
                                            'wf': False,
                                            'sn': 0,
                                            'sc': 1,
                                            'ml': 0,
                                            'sf': False,
                                            'af': False,
                                            'bk': 1,
                                            'ck': 0,
                                            'fk': 0,
                                            'fl': 0,
                                            'fg': '00'})
        self.assertDictEqual(packet1.body.data, body)

    def testBasicRaetMsgpack(self):
        '''
        Basic pack parse with header json and body msgpack
        '''
        console.terse("{0}\n".format(self.testBasicRaetMsgpack.__doc__))

        hk = raeting.headKinds.raet
        bk = raeting.bodyKinds.msgpack

        data = odict(hk=hk, bk=bk)
        body = odict(msg='Hello Raet World', extra='Goodby Big Moon')
        packet0 = packeting.TxPacket(embody=body, data=data, )
        self.assertDictEqual(packet0.body.data, body)
        packet0.pack()
        self.assertEqual(packet0.packed,
                'ri RAET\npl 0048\nhl 1c\nbk 3\n\n\x82\xa3msg\xb0Hello Raet World\xa5extra\xafGoodby Big Moon')

        packet1 = packeting.RxPacket(packed=packet0.packed)
        packet1.parse()
        self.assertDictEqual(packet1.data, {'sh': '',
                                            'sp': 7530,
                                            'dh': '127.0.0.1',
                                            'dp': 7530,
                                            'ri':'RAET',
                                            'vn': 0,
                                            'pk': 0,
                                            'pl': 72,
                                            'hk': 0,
                                            'hl': 28,
                                            'se': 0,
                                            'de': 0,
                                            'cf': False,
                                            'bf': False,
                                            'si': 0,
                                            'ti': 0,
                                            'tk': 0,
                                            'dt': 0,
                                            'oi': 0,
                                            'wf': False,
                                            'sn': 0,
                                            'sc': 1,
                                            'ml': 0,
                                            'sf': False,
                                            'af': False,
                                            'bk': 3,
                                            'ck': 0,
                                            'fk': 0,
                                            'fl': 0,
                                            'fg': '00'})
        self.assertDictEqual(packet1.body.data, body)

    def testBasicRaetRaw(self):
        '''
        Basic pack parse with header raet and body json
        '''
        console.terse("{0}\n".format(self.testBasicRaetJson.__doc__))

        hk = raeting.headKinds.raet
        bk = raeting.bodyKinds.raw

        data = odict(hk=hk, bk=bk)
        body = "This is a fine kettle of fish."
        packet0 = packeting.TxPacket(embody=body, data=data, )
        self.assertEqual(packet0.body.data, body)
        packet0.pack()
        self.assertEqual(packet0.packed,
                'ri RAET\npl 003a\nhl 1c\nbk 2\n\nThis is a fine kettle of fish.')

        packet1 = packeting.RxPacket(packed=packet0.packed)
        packet1.parse()
        self.assertDictEqual(packet1.data, {'sh': '',
                                            'sp': 7530,
                                            'dh': '127.0.0.1',
                                            'dp': 7530,
                                            'ri':'RAET',
                                            'vn': 0,
                                            'pk': 0,
                                            'pl': 58,
                                            'hk': 0,
                                            'hl': 28,
                                            'se': 0,
                                            'de': 0,
                                            'cf': False,
                                            'bf': False,
                                            'si': 0,
                                            'ti': 0,
                                            'tk': 0,
                                            'dt': 0,
                                            'oi': 0,
                                            'wf': False,
                                            'sn': 0,
                                            'sc': 1,
                                            'ml': 0,
                                            'sf': False,
                                            'af': False,
                                            'bk': 2,
                                            'ck': 0,
                                            'fk': 0,
                                            'fl': 0,
                                            'fg': '00'})
        self.assertEqual(packet1.body.data, body)

    def testSegmentation(self):
        '''
        Test pack unpack segmented
        '''
        console.terse("{0}\n".format(self.testBasicRaetJson.__doc__))
        hk = raeting.headKinds.raet
        bk = raeting.bodyKinds.raw

        data = odict(hk=hk, bk=bk)

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(4, " "))
        stuff = "".join(stuff)
        self.assertEqual(len(stuff), 1200)
        self.assertTrue(len(stuff) > raeting.UDP_MAX_PACKET_SIZE)
        packet0 = packeting.TxPacket(embody=stuff, data=data, )
        self.assertRaises(raeting.PacketError, packet0.pack)

        tray0 = packeting.TxTray(data=data, body=stuff)
        tray0.pack()
        self.assertEquals(tray0.packed, '   0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36  37  38  39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61  62  63  64  65  66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299')
        self.assertEquals(len(tray0.packets), 2)

        tray1 = packeting.RxTray()
        for packet in tray0.packets:
            tray1.parse(packet)

        print tray1.data
        self.assertDictEqual(tray1.data, {'sh': '',
                                           'sp': 7530,
                                           'dh': '127.0.0.1',
                                           'dp': 7530,
                                           'ri': 'RAET',
                                           'vn': 0,
                                           'pk': 0,
                                           'pl': 1015,
                                           'hk': 0,
                                           'hl': 46,
                                           'se': 0,
                                           'de': 0,
                                           'cf': False,
                                           'bf': False,
                                           'si': 0,
                                           'ti': 0,
                                           'tk': 0,
                                           'dt': 0,
                                           'oi': 0,
                                           'wf': False,
                                           'sn': 0,
                                           'sc': 2,
                                           'ml': 1200,
                                           'sf': True,
                                           'af': False,
                                           'bk': 2,
                                           'ck': 0,
                                           'fk': 0,
                                           'fl': 0,
                                           'fg': '10'})
        self.assertEquals( tray1.body, stuff)

class StackTestCase(unittest.TestCase):
    '''
    Pack and Parse with stacks
    '''

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.dirpathBase=tempfile.mkdtemp(prefix="raet",  suffix="base")
        stacking.RoadStack.Bk = raeting.bodyKinds.json

        #main stack
        mainName = "main"
        mainDirpath = os.path.join(self.dirpathBase, 'road', 'keep', mainName)
        signer = nacling.Signer()
        mainSignKeyHex = signer.keyhex
        mainVerKeyHex = signer.verhex
        privateer = nacling.Privateer()
        mainPriKeyHex = privateer.keyhex
        mainPubKeyHex = privateer.pubhex

        #other stack
        otherName = "other"
        otherDirpath = os.path.join(self.dirpathBase, 'road', 'keep', otherName)
        signer = nacling.Signer()
        otherSignKeyHex = signer.keyhex
        otherVerKeyHex = signer.verhex
        privateer = nacling.Privateer()
        otherPriKeyHex = privateer.keyhex
        otherPubKeyHex = privateer.pubhex

        keeping.clearAllKeep(mainDirpath)
        keeping.clearAllKeep(otherDirpath)

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

        remote1 = estating.RemoteEstate(stack=self.main,
                                        eid=2,
                                        name=otherName,
                                        ha=("127.0.0.1", raeting.RAET_TEST_PORT),
                                        verkey=otherVerKeyHex,
                                        pubkey=otherPubKeyHex,
                                        period=self.main.period,
                                        offset=self.main.offset,)
        self.main.addRemote(remote1)


        local = estating.LocalEstate(eid=2,
                                     name=otherName,
                                     ha=("", raeting.RAET_TEST_PORT),
                                     sigkey=otherSignKeyHex,
                                     prikey=otherPriKeyHex,)

        self.other = stacking.RoadStack(name=otherName,
                                         local=local,
                                         dirpath=otherDirpath,
                                         store=self.store)

        remote0 = estating.RemoteEstate(stack=self.other,
                                        eid=1,
                                        name=mainName,
                                        ha=('127.0.0.1', raeting.RAET_PORT),
                                        verkey=mainVerKeyHex,
                                        pubkey=mainPubKeyHex,
                                        period=self.other.period,
                                        offset=self.other.offset,)
        self.other.addRemote(remote0)

        remote0.publee = nacling.Publican(key=remote1.privee.pubhex)
        remote1.publee = nacling.Publican(key=remote0.privee.pubhex)

        stuff = []
        for i in range(300):
            stuff.append(str(i).rjust(4, " "))
        self.stuff = "".join(stuff)

        self.data = odict(hk=raeting.headKinds.raet)


    def tearDown(self):
        self.main.server.close()
        self.other.server.close()

        self.main.clearLocalKeep()
        self.main.clearRemoteKeeps()
        self.other.clearLocalKeep()
        self.other.clearRemoteKeeps()

        if os.path.exists(self.dirpathBase):
            shutil.rmtree(self.dirpathBase)

    def testSign(self):
        '''
        Signing tests
        '''
        console.terse("{0}\n".format(self.testSign.__doc__))

        self.assertEqual(len(self.stuff), 1200)
        self.assertTrue(len(self.stuff) > raeting.UDP_MAX_PACKET_SIZE)

        # Raw bodied signed
        self.data.update(se=1, de=2, bk=raeting.bodyKinds.raw, fk=raeting.footKinds.nacl)
        tray0 = packeting.TxTray(stack=self.main, data=self.data, body=self.stuff)
        tray0.pack()
        self.assertEqual(tray0.packed, '   0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36  37  38  39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61  62  63  64  65  66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299')
        self.assertEqual(len(tray0.packets), 2)
        self.assertEqual(len(tray0.packets[0].packed), 1015)
        self.assertEqual(len(tray0.packets[1].packed), 452)


        tray1 = packeting.RxTray(stack=self.other)
        self.assertFalse(tray1.complete)
        for packet in tray0.packets:
            tray1.parse(packet)

        self.assertTrue(tray1.complete)
        self.assertDictEqual(tray1.data, {'sh': '',
                                          'sp': 7530,
                                          'dh': '127.0.0.1',
                                          'dp': 7530,
                                          'ri': 'RAET',
                                          'vn': 0,
                                          'pk': 0,
                                          'pl': 1015,
                                          'hk': 0,
                                          'hl': 67,
                                          'se': 1,
                                          'de': 2,
                                          'cf': False,
                                          'bf': False,
                                          'si': 0,
                                          'ti': 0,
                                          'tk': 0,
                                          'dt': 0,
                                          'oi': 0,
                                          'wf': False,
                                          'sn': 0,
                                          'sc': 2,
                                          'ml': 1200,
                                          'sf': True,
                                          'af': False,
                                          'bk': 2,
                                          'ck': 0,
                                          'fk': 1,
                                          'fl': 64,
                                          'fg': '10'})
        self.assertEqual( tray1.body, self.stuff)

        # Json body
        body = odict(stuff=self.stuff)
        self.data.update(se=1, de=2, bk=raeting.bodyKinds.json, fk=raeting.footKinds.nacl)
        tray0 = packeting.TxTray(stack=self.main, data=self.data, body=body)
        tray0.pack()

        self.assertEqual(tray0.packed, '{"stuff":"   0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36  37  38  39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61  62  63  64  65  66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299"}')
        self.assertEqual(len(tray0.packets), 2)
        self.assertEqual(len(tray0.packets[0].packed), 1015)
        self.assertEqual(len(tray0.packets[1].packed), 464)


        tray1 = packeting.RxTray(stack=self.other)
        self.assertFalse(tray1.complete)
        for packet in tray0.packets:
            tray1.parse(packet)

        self.assertTrue(tray1.complete)
        self.assertDictEqual(tray1.data, {'sh': '',
                                          'sp': 7530,
                                          'dh': '127.0.0.1',
                                          'dp': 7530,
                                          'ri': 'RAET',
                                          'vn': 0,
                                          'pk': 0,
                                          'pl': 1015,
                                          'hk': 0,
                                          'hl': 67,
                                          'se': 1,
                                          'de': 2,
                                          'cf': False,
                                          'bf': False,
                                          'si': 0,
                                          'ti': 0,
                                          'tk': 0,
                                          'dt': 0,
                                          'oi': 0,
                                          'wf': False,
                                          'sn': 0,
                                          'sc': 2,
                                          'ml': 1212,
                                          'sf': True,
                                          'af': False,
                                          'bk': 1,
                                          'ck': 0,
                                          'fk': 1,
                                          'fl': 64,
                                          'fg': '10'})

        self.assertEqual( tray1.body, body)


    def testEncrypt(self):
        '''
        Encrypt Decrypt tests
        '''
        console.terse("{0}\n".format(self.testEncrypt.__doc__))

        self.assertEqual(len(self.stuff), 1200)
        self.assertTrue(len(self.stuff) > raeting.UDP_MAX_PACKET_SIZE)

        body = odict(stuff=self.stuff)
        self.data.update(se=1, de=2,
                    bk=raeting.bodyKinds.json,
                    ck=raeting.coatKinds.nacl,
                    fk=raeting.footKinds.nacl)
        tray0 = packeting.TxTray(stack=self.main, data=self.data, body=body)
        tray0.pack()

        self.assertEqual(len(tray0.packed), 1252)
        self.assertEqual(len(tray0.packets), 2)
        self.assertEqual(len(tray0.packets[0].packed), 1015)
        self.assertEqual(len(tray0.packets[1].packed), 514)

        tray1 = packeting.RxTray(stack=self.other)
        self.assertFalse(tray1.complete)
        for packet in tray0.packets:
            tray1.parse(packet)

        self.assertTrue(tray1.complete)
        self.assertDictEqual(tray1.data, {'sh': '',
                                          'sp': 7530,
                                          'dh': '127.0.0.1',
                                          'dp': 7530,
                                          'ri': 'RAET',
                                          'vn': 0,
                                          'pk': 0,
                                          'pl': 1015,
                                          'hk': 0,
                                          'hl': 72,
                                          'se': 1,
                                          'de': 2,
                                          'cf': False,
                                          'bf': False,
                                          'si': 0,
                                          'ti': 0,
                                          'tk': 0,
                                          'dt': 0,
                                          'oi': 0,
                                          'wf': False,
                                          'sn': 0,
                                          'sc': 2,
                                          'ml': 1252,
                                          'sf': True,
                                          'af': False,
                                          'bk': 1,
                                          'ck': 1,
                                          'fk': 1,
                                          'fl': 64,
                                          'fg': '10'})

        self.assertEqual( tray1.body, body)



def runOneBasic(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runOneStack(test):
    '''
    Unittest Runner
    '''
    test = StackTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    """ Unittest runner """
    tests =  []
    names = ['testBasicJson',
             'testBasicMsgpack',
             'testBasicRaetJson',
             'testBasicRaetMsgpack',
             'testBasicRaetRaw',
             'testSegmentation']
    tests.extend(map(BasicTestCase, names))

    #names = ['testPackParse']
    #tests.extend(map(StackTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(StackTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    runAll() #run all unittests

    #runSome()#only run some

    #runOneBasic('testBasicJson')
    #runOneStack('testEncrypt')
