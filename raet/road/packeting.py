# -*- coding: utf-8 -*-
#pylint: skip-file
'''
packeting module provides classes for Raet packets

'''

# Import python libs
from collections import Mapping, deque
try:
    import simplejson as json
except ImportError:
    import json

try:
    import msgpack
except ImportError:
    mspack = None

# Import ioflo libs
from ioflo.aid.odicting import odict
from ioflo.aid.aiding import packByte, unpackByte

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import (PcktKind, TailSize, CoatKind, FootSize, FootKind,
                       BodyKind, HeadKind, TrnsKind)

class Part(object):
    '''
    Base class for parts of a RAET packet
    Should be subclassed
    '''

    def __init__(self, packet=None, **kwa):
        '''
        Setup Part instance
        '''
        self.packet = packet  # Packet this Part belongs too
        self.packed = b''

    def __len__(self):
        '''
        Returns the length of .packed
        '''
        return len(self.packed)

    @property
    def size(self):
        '''
        Property is the length of this Part
        '''
        return self.__len__()

class Head(Part):
    '''
    RAET protocol packet header class
    Manages the header portion of a packet
    '''
    def __init__(self, **kwa):
        '''
        Setup Head instance
        '''
        super(Head, self).__init__(**kwa)

class TxHead(Head):
    '''
    RAET protocol transmit packet header class
    '''
    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        data = self.packet.data  # for speed
        data['fl'] = self.packet.foot.size
        data['fg'] = "{0:02x}".format(self.packFlags())

        # kit always includes raet id, packet length, header kind and flag fields
        kit = odict([('ri', 'RAET'), ('pl', 0), ('hl', 0), ('fg', '00')])
        for k, v in raeting.PACKET_DEFAULTS.items():  # include if not equal to default
            if ((k in raeting.PACKET_HEAD_FIELDS) and
                (k not in raeting.PACKET_FLAGS) and
                (data[k] != v)):
                kit[k] = data[k]

        if data['hk'] == HeadKind.raet:
            packed = b''
            lines = []
            for k, v in kit.items():
                lines.append("{key} {val:{fmt}}".format(
                        key=k, val=v, fmt=raeting.PACKET_FIELD_FORMATS[k]))
            packed = ns2b('\n'.join(lines)) + raeting.HEAD_END
            hl = len(packed)
            if hl > raeting.MAX_HEAD_SIZE:
                emsg = "Head length of {0}, exceeds max of {1}".format(hl, MAX_HEAD_SIZE)
                raise raeting.PacketError(emsg)
            data['hl'] = hl

            if self.packet.coat.size > raeting.MAX_MESSAGE_SIZE:
                emsg = "Packed message length of {0}, exceeds max of {1}".format(
                         self.packet.coat.size, raeting.MAX_MESSAGE_SIZE)
                raise raeting.PacketError(emsg)
            pl = hl + self.packet.coat.size + data['fl']
            data['pl'] = pl
            # Tray checks for packet length greater than UDP_MAX_PACKET_SIZE
            # and segments appropriately so pl may be truncated below in this case
            # substitute true lengths
            packed = packed.replace(ns2b('\npl {val:{fmt}}\n'.format(
                                        val=kit['pl'],
                                        fmt=raeting.PACKET_FIELD_FORMATS['pl'])),
                                    ns2b('\npl {0}\n'.format("{val:{fmt}}".format(
                                        val=pl,
                                        fmt=raeting.PACKET_FIELD_FORMATS['pl'])[-4:])),
                                    1)
            packed = packed.replace(ns2b('\nhl {val:{fmt}}\n'.format(
                                        val=kit['hl'],
                                        fmt=raeting.PACKET_FIELD_FORMATS['hl'])),
                                    ns2b('\nhl {0}\n'.format("{val:{fmt}}".format(
                                            val=hl,
                                            fmt=raeting.PACKET_FIELD_FORMATS['hl'])[-2:])),
                                    1)
            self.packed = packed

        elif data['hk'] == HeadKind.json:
            kit['pl'] = '0000000'  # need hex string so fixed length and jsonable
            kit['hl'] = '00'  # need hex string so fixed length and jsonable
            packed = (ns2b(json.dumps(kit, separators=(',', ':'))) + raeting.JSON_END)
            hl = len(packed)
            if hl > raeting.MAX_HEAD_SIZE:
                emsg = "Head length of {0}, exceeds max of {1}".format(hl, MAX_HEAD_SIZE)
                raise raeting.PacketError(emsg)
            data['hl'] = hl

            if self.packet.coat.size > raeting.MAX_MESSAGE_SIZE:
                emsg = "Packed message length of {0}, exceeds max of {1}".format(
                         self.packet.coat.size, raeting.MAX_MESSAGE_SIZE)
                raise raeting.PacketError(emsg)
            pl = hl + self.packet.coat.size + data['fl']
            data['pl'] = pl
            #substitute true length converted to 2 byte hex string
            packed = packed.replace(ns2b('"pl":"0000000"'),
                                    ns2b('"pl":"{0}"'.format("{0:07x}".format(pl)[-7:])),
                                    1)  # JSON needs double quotes on strings
            self.packed = packed.replace(ns2b('"hl":"00"'),
                                         ns2b('"hl":"{0}"'.format("{0:02x}".format(hl)[-2:])),
                                         1)  # JSON needs double quotes on strings

    def packFlags(self):
        '''
        Packs all the flag fields into a single two char hex string
        '''
        values = []
        for field in raeting.PACKET_FLAG_FIELDS:
            values.append(1 if self.packet.data.get(field, 0) else 0)
        return packByte(fmt=b'11111111', fields=values)

class RxHead(Head):
    '''
    RAET protocol receive packet header class
    '''
    def parse(self):
        '''
        From .packed.packed, Detects head kind. Unpacks head. Parses head and updates
        .packet.data
        Raises PacketError if failure occurs
        '''
        self.packed = b''
        data = self.packet.data  # for speed
        packed = self.packet.packed  # for speed

        if packed.startswith(b'ri RAET\n') and raeting.HEAD_END in packed: # raet head
            hk = HeadKind.raet.value
            front, sep, back = packed.partition(raeting.HEAD_END)
            self.packed = front + sep
            kit = odict()
            lines = str(front.decode('ISO-8859-1')).split('\n')
            for line in lines:
                key, val = line.split(' ')
                if key not in raeting.PACKET_HEAD_FIELDS:
                    emsg = "Unknown head field '{0}'".format(key)
                    raise raeting.PacketError(emsg)
                if 'x' in raeting.PACKET_FIELD_FORMATS[key]:
                    val = int(val, 16)
                elif 'd' in raeting.PACKET_FIELD_FORMATS[key]:
                    val = int(val)
                elif 'f' in raeting.PACKET_FIELD_FORMATS[key]:
                    val = float(val)
                kit[key] = val

            data.update(kit)
            if 'fg' in data:
                self.unpackFlags(data['fg'])

            if data['hk'] != hk:
                emsg = 'Recognized head kind does not match head field value.'
                raise raeting.PacketError(emsg)

            if data['hl'] != self.size:
                emsg = 'Actual head length = {0} not match head field = {1}'.format(
                        self.size, data['hl'])
                raise raeting.PacketError(emsg)

            if data['pl'] != self.packet.size:
                emsg = 'Actual packet length = {0} not match head field = {1}'.format(
                    self.packet.size, data['pl'])
                raise raeting.PacketError(emsg)


        elif packed.startswith(ns2b('{"ri":"RAET",')) and raeting.JSON_END in packed: # json head
            hk = HeadKind.json.value
            front, sep, back = packed.partition(raeting.JSON_END)
            self.packed = front + sep
            kit = json.loads(front.decode('ascii'),
                             object_pairs_hook=odict)
            data.update(kit)
            if 'fg' in data:
                self.unpackFlags(data['fg'])

            if data['hk'] != hk:
                emsg = 'Recognized head kind does not match head field value.'
                raise raeting.PacketError(emsg)

            hl = int(data['hl'], 16)
            if hl != self.size:
                emsg = 'Actual head length does not match head field value.'
                raise raeting.PacketError(emsg)
            data['hl'] = hl
            pl = int(data['pl'], 16)
            if pl != self.packet.size:
                emsg = 'Actual packet length does not match head field value.'
                raise raeting.PacketError(emsg)
            data['pl'] = pl

        else:  # notify unrecognizable packet head
            data['hk'] = HeadKind.unknown.value
            emsg = "Unrecognizable packet head."
            raise raeting.PacketError(emsg)

    def unpackFlags(self, flags):
        '''
        Unpacks all the flag fields from a single two char hex string
        '''
        values = unpackByte(fmt=b'11111111', byte=int(flags, 16), boolean=True)
        for i, field in enumerate(raeting.PACKET_FLAG_FIELDS):
            if field in self.packet.data:
                self.packet.data[field] = values[i]

class Body(Part):
    '''
    RAET protocol packet body class
    Manages the message portion of the packet
    '''
    def __init__(self, data=None, **kwa):
        '''
        Setup Body instance
        '''
        super(Body, self).__init__(**kwa)
        if data is None:
            data = odict()
        self.data = data

class TxBody(Body):
    '''
    RAET protocol tx packet body class
    '''
    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        bk = self.packet.data['bk']
        if bk == BodyKind.json:
            if self.data:
                self.packed = ns2b(json.dumps(self.data,
                                              separators=(',', ':')))
        elif bk == BodyKind.msgpack:
            if self.data:
                if not msgpack:
                    emsg = "Msgpack not installed."
                    raise raeting.PacketError(emsg)
                self.packed = msgpack.dumps(self.data,
                                            encoding='utf-8')
        elif bk == BodyKind.raw:
            self.packed = self.data # data is already formatted string

class RxBody(Body):
    '''
    RAET protocol rx packet body class
    '''
    def parse(self):
        '''
        Parses body. Assumes already unpacked.
        Results in updated .data
        '''
        bk = self.packet.data['bk']

        if bk not in list(BodyKind):
            self.packet.data['bk']= BodyKind.unknown.value
            emsg = "Unrecognizable packet body."
            raise raeting.PacketError(emsg)

        self.data = odict()

        if bk == BodyKind.json:
            if self.packed:
                kit = json.loads(self.packed.decode('utf-8'),
                                 object_pairs_hook=odict,
                                 encoding='utf-8')
                if not isinstance(kit, Mapping):
                    emsg = "Packet body not a mapping."
                    raise raeting.PacketError(emsg)
                self.data = kit
        elif bk == BodyKind.msgpack:
            if self.packed:
                if not msgpack:
                    emsg = "Msgpack not installed."
                    raise raeting.PacketError(emsg)
                kit = msgpack.loads(self.packed,
                                    object_pairs_hook=odict,
                                    encoding='utf-8')
                if not isinstance(kit, Mapping):
                    emsg = "Packet body not a mapping."
                    raise raeting.PacketError(emsg)
                self.data = kit
        elif bk == BodyKind.raw:
            self.data = self.packed # return as bytes
        elif bk == BodyKind.nada:
            pass

class Coat(Part):
    '''
    RAET protocol packet coat class
    Supports encapsulated encrypt/decrypt of body portion of packet
    '''
    def __init__(self, **kwa):
        ''' Setup Coat instance'''
        super(Coat, self).__init__(**kwa)

class TxCoat(Coat):
    '''
    RAET protocol tx packet coat class
    '''
    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        ck = self.packet.data['ck']

        if ck == CoatKind.nacl:
            msg = self.packet.body.packed
            if msg:
                cipher, nonce = self.packet.encrypt(msg)
                self.packed = b''.join([cipher, nonce])

        if ck == CoatKind.nada:
            self.packed = self.packet.body.packed

class RxCoat(Coat):
    '''
    RAET protocol rx packet coat class
    '''
    def parse(self):
        '''
        Parses coat. Assumes already unpacked.
        '''
        ck = self.packet.data['ck']

        if ck not in list(CoatKind):
            self.packet.data['ck'] = CoatKind.unknown.value
            emsg = "Unrecognizable packet coat."
            raise raeting.PacketError(emsg)

        if ck == CoatKind.nacl:
            if self.packed:
                tl = TailSize.nacl.value # nonce length
                cipher = self.packed[:-tl]
                nonce = self.packed[-tl:]
                msg = self.packet.decrypt(cipher, nonce)
                self.packet.body.packed = msg
            else:
                self.packet.body.packed = self.packed

        if ck == CoatKind.nada:
            self.packet.body.packed = self.packed
            pass

class Foot(Part):
    '''
    RAET protocol packet foot class
    Manages the signing or authentication of the packet
    '''
    def __init__(self, **kwa):
        '''
        Setup Foot instance
        '''
        super(Foot, self).__init__(**kwa)

class TxFoot(Foot):
    '''
    RAET protocol transmit packet foot class
    '''

    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        fk = self.packet.data['fk']

        if fk not in list(FootKind):
            self.packet.data['fk'] = FootKind.unknown.value
            emsg = "Unrecognizable packet foot."
            raise raeting.PacketError(emsg)

        if fk == FootKind.nacl:
            self.packed = b''.rjust(FootSize.nacl.value, b'\x00')

        elif fk == FootKind.nada:
            pass

    def sign(self):
        '''
        Compute signature on packet.packed and update packet.packet with signature
        '''
        fk = self.packet.data['fk']
        if fk not in list(FootKind):
            self.packet.data['fk'] = FootKind.unknown.value
            emsg = "Unrecognizable packet foot."
            raise raeting.PacketError(emsg)

        if fk == FootKind.nacl:
            self.packed = self.packet.signature(self.packet.packed)

        elif fk == FootKind.nada:
            pass

class RxFoot(Foot):
    '''
    RAET protocol receive packet foot class
    '''
    def parse(self):
        '''
        Parses foot. Assumes foot already unpacked
        '''
        fk = self.packet.data['fk']
        fl = self.packet.data['fl']
        tk = self.packet.data['tk']
        self.packed = b''

        if fk not in list(FootKind):
            self.packet.data['fk'] = FootKind.unknown.value
            emsg = "Unrecognizable packet foot."
            raise raeting.PacketError(emsg)

        if self.packet.size < fl:
            emsg = "Packet size not big enough for foot."
            raise raeting.PacketError(emsg)

        self.packed = self.packet.packed[self.packet.size - fl:]

        if self.packet.stack.veritive and tk == TrnsKind.message and fk != FootKind.nacl:
            reason = "missing signature"
            emsg = "Failed verification: {0}".format(reason)
            raise raeting.PacketError(emsg)

        if fk == FootKind.nacl:
            if self.size != FootSize.nacl:
                emsg = ("Actual foot size '{0}' does not match "
                    "kind size '{1}'".format(self.size, FootSize.nacl.value))
                raise raeting.PacketError(emsg)

            signature = self.packed
            blank = b''.rjust(FootSize.nacl.value, b'\x00')

            front = self.packet.packed[:self.packet.size - fl]

            msg = front + blank
            if not self.packet.verify(signature, msg):
                if self.packet.data['de'] not in self.packet.stack.remotes:
                    reason =  "nuid not in remotes"
                else:
                    reason = "key invalid"
                emsg = "Failed verification: {0}".format(reason)
                raise raeting.PacketError(emsg)

        if fk == FootKind.nada:
            pass

class Packet(object):
    '''
    RAET protocol packet object
    '''
    def __init__(self, stack=None, data=None, kind=None):
        ''' Setup Packet instance. Meta data for a packet. '''
        self.stack = stack
        self.packed = b''  # packed string
        self.data = odict(raeting.PACKET_DEFAULTS)
        if data:
            self.data.update(data)
        if kind:
            if kind not in list(PcktKind):
                self.data['pk'] = PcktKind.unknown.value
                emsg = "Unrecognizable packet kind."
                raise raeting.PacketError(emsg)
            self.data.update(pk=kind)

    @property
    def size(self):
        '''
        Property is the length of the .packed of this Packet
        '''
        return len(self.packed)

    @property
    def segmentive(self):
        '''
        Property is True
        If packet segment flag is True Or packet segment count is > 1
        '''
        return (True if (self.data.get('sf') or (self.data.get('sc', 1) > 1)) else False)

    def refresh(self, data=None):
        '''
        Refresh .data to defaults and update if data
        '''
        self.data = odict(raeting.PACKET_DEFAULTS)
        if data:
            self.data.update(data)
        return self  # so can method chain

class TxPacket(Packet):
    '''
    RAET Protocol Transmit Packet object
    '''
    def __init__(self, embody=None, **kwa):
        '''
        Setup TxPacket instance
        '''
        super(TxPacket, self).__init__(**kwa)
        self.head = TxHead(packet=self)
        self.body = TxBody(packet=self, data=embody)
        self.coat = TxCoat(packet=self)
        self.foot = TxFoot(packet=self)

    @property
    def index(self):
        '''
        Property is transaction tuple (rf, le, re, si, ti, bf,)
        rf = cf
        '''
        data = self.data
        cf = data['cf']
        le = data['se']
        re = data['de']
        if (re == 0 and not cf) or (le == 0 and cf):
            re = (data['dh'], data['dp'])
        return ((cf, le, re, data['si'], data['ti'], data['bf']))

    def signature(self, msg):
        '''
        Return signature resulting from signing msg
        '''
        return (self.stack.local.signer.signature(msg))

    def sign(self):
        '''
        Sign packet with foot
        '''
        self.foot.sign()
        self.packed = b''.join([self.head.packed,
                               self.coat.packed,
                               self.foot.packed])

    def encrypt(self, msg):
        '''
        Return (cipher, nonce) duple resulting from encrypting message
        with short term keys
        '''
        remote = self.stack.remotes[self.data['se']]
        return (remote.privee.encrypt(msg, remote.publee.key))

    def prepack(self):
        '''
        Pre Pack the parts of the packet .packed but do not sign so can see
        if needs to be segmented
        '''
        self.body.pack()
        self.coat.pack()
        self.foot.pack()
        self.head.pack()
        self.packed = b''.join([self.head.packed,
                               self.coat.packed,
                               self.foot.packed])

    def repack(self):
        '''
        Repack the head and resign. Useful if need to change head flag
        '''
        self.foot.pack()  # need to pack to reblank it
        self.head.pack()
        self.packed = b''.join([self.head.packed,
                               self.coat.packed,
                               self.foot.packed])

        self.sign()  # sign updates self.packed
        if self.size > raeting.UDP_MAX_PACKET_SIZE:
            emsg = "Packet length of {0}, exceeds max of {1}".format(
                self.size, raeting.UDP_MAX_PACKET_SIZE)
            raise raeting.PacketError(emsg)

    def pack(self):
        '''
        Pack the parts of the packet and then the full packet into .packed
        '''
        self.prepack()
        if self.size > raeting.UDP_MAX_PACKET_SIZE:
            emsg = "Packet length of {0}, exceeds max of {1}".format(
                    self.size, raeting.UDP_MAX_PACKET_SIZE)
            raise raeting.PacketError(emsg)
        self.sign()

class RxPacket(Packet):
    '''
    RAET Protocol Receive Packet object
    '''
    def __init__(self, packed=None, **kwa):
        '''
        Setup RxPacket instance
        '''
        super(RxPacket, self).__init__(**kwa)
        self.head = RxHead(packet=self)
        self.body = RxBody(packet=self)
        self.coat = RxCoat(packet=self)
        self.foot = RxFoot(packet=self)
        self.packed = packed or ''

    @property
    def index(self):
        '''
        Property is transaction tuple (rf, le, re, si, ti, bf,)
        rf = not cf
        '''
        data = self.data
        cf = data['cf']
        le = data['de']
        re = data['se']
        if (re == 0 and cf) or (le == 0 and not cf):
            re = (data['sh'], data['sp'])
        return ((not cf, le, re, data['si'], data['ti'], data['bf']))

    def verify(self, signature, msg):
        '''
        Return result of verifying msg with signature
        '''
        nuid = self.data['de']
        if not nuid in self.stack.remotes:
            return False
        return (self.stack.remotes[nuid].verfer.verify(signature, msg))

    def decrypt(self, cipher, nonce):
        '''
        Return msg resulting from decrypting cipher and nonce
        with short term keys
        '''
        remote = self.stack.remotes[self.data['de']]
        return (remote.privee.decrypt(cipher, nonce, remote.publee.key))

    def parse(self, packed=None):
        '''
        Parses raw packet completely
        Result is .data and .body.data
        Raises PacketError exception If failure
        '''
        self.parseOuter(packed=packed)
        self.parseInner()

    def parseOuter(self, packed=None):
        '''
        Parses raw packet head from packed if provided or .packed otherwise
        Deserializes head
        Unpacks rest of packet.
        Parses foot (signature) if given and verifies signature
        Returns False if not verified Otherwise True
        Result is .data
        Raises PacketError exception If failure
        '''
        if packed:
            self.packed = packed
        if not self.packed:
            emsg = "Packed empty, nothing to parse."
            raise raeting.PacketError(emsg)

        self.head.parse()

        if self.data['vn'] not in raeting.VERSIONS.values():
            emsg = ("Received incompatible version '{0}'"
                    "version '{1}'".format(self.data['vn']))
            raise raeting.PacketError(emsg)

        self.foot.parse() #foot unpacks itself

    def unpackInner(self, packed=None):
        '''
        Unpacks the body, and coat parts of .packed
        Assumes that the lengths of the parts are valid in .data as would be
        the case after successfully parsing the head section
        '''
        hl = self.data['hl']
        fl = self.data['fl']
        self.coat.packed = self.packed[hl:self.size - fl] #coat.parse loads body.packed

    def parseInner(self):
        '''
        Assumes the head as already been parsed so self.data is valid
        Assumes packet as already been unpacked
        Assumes foot signature has already been verified if any
        Parses coat if given and decrypts enclosed body
        Parses decrypted body and deserializes
        Returns True if decrypted deserialize successful Otherwise False
        Result is .body.data and .data
        Raises PacketError exception If failure
        '''
        self.unpackInner()
        self.coat.parse()
        self.body.parse()

class Tray(object):
    '''
    Manages messages, segmentation when needed and the associated packets
    '''
    def __init__(self, stack=None, data=None, body=None, packed=None,  **kwa):
        '''
        Setup instance
        '''
        self.stack = stack
        self.packed = packed or ''
        self.data = odict(raeting.PACKET_DEFAULTS)
        if data:
            self.data.update(data)
        self.body = body #body data of message

    @property
    def size(self):
        '''
        Property is the length of the .packed
        '''
        return len(self.packed)

class TxTray(Tray):
    '''
    Manages an outgoing message and ites associated packet(s)
    '''
    def __init__(self, **kwa):
        '''
        Setup instance
        '''
        super(TxTray, self).__init__(**kwa)
        self.packets = []
        self.current = 0 # next  packet to send
        self.last = 0 # last packet sent

    def pack(self, data=None, body=None):
        '''
        Convert message in .body into one or more packets
        '''
        if data:
            self.data.update(data)
        if body is not None:
            self.body = body

        self.current = 0
        self.packets = []
        packet = TxPacket(stack=self.stack,
                          kind=PcktKind.message.value,
                          embody=self.body,
                          data=self.data)

        packet.prepack()
        if packet.size <= raeting.UDP_MAX_PACKET_SIZE:
            packet.sign()
            self.packets.append(packet)
        else:
            self.packed = packet.coat.packed
            self.packetize(headsize=packet.head.size, footsize=packet.foot.size)

    def packetize(self, headsize, footsize):
        '''
        Create packeted segments from .packed using headsize footsize
        '''
        extrasize = 0
        if self.data['hk'] == HeadKind.raet:
            extrasize = 27 # extra header size as a result of segmentation
        elif self.data['hk'] == HeadKind.json:
            extrasize = 36 # extra header size as a result of segmentation

        hotelsize = headsize + extrasize + footsize
        segsize = raeting.UDP_MAX_PACKET_SIZE - hotelsize

        segcount = (self.size // segsize) + (1 if self.size % segsize else 0)
        for i in range(segcount):
            if i == segcount - 1: #last segment
                segment = self.packed[i * segsize:]
            else:
                segment = self.packed[i * segsize: (i+1) * segsize]

            packet = TxPacket( stack=self.stack,
                                data=self.data)
            packet.data.update(sn=i, sc=segcount, ml=self.size, sf=True)
            packet.coat.packed = packet.body.packed = segment
            packet.foot.pack()
            packet.head.pack()
            packet.packed = b''.join([packet.head.packed,
                                     packet.coat.packed,
                                     packet.foot.packed])
            packet.sign()
            self.packets.append(packet)


class RxTray(Tray):
    '''
    Manages segmentated messages and the associated packets
    '''
    def __init__(self, segments=None, **kwa):
        '''
        Setup instance
        '''
        super(RxTray, self).__init__(**kwa)
        self.segments = segments if segments is not None else []
        self.complete = False
        self.highest = 0  # highest segment number received

    def parse(self, packet):
        '''
        Process a given packet assumes parseOuter done already
        '''
        sc = packet.data['sc']
        sn = packet.data['sn']
        if sn > self.highest:
            self.highest = sn
        console.verbose("segment count={0} number={1} tid={2}\n".format(
            sc, sn, packet.data['ti']))

        if sc == 1:  # this is only segment to complete now
            self.data.update(packet.data)
            packet.parseInner()
            self.body = packet.body.data
            self.complete = True
            return self.body

        if not self.segments: #get data from first packet received
            self.data.update(packet.data)
            self.segments = [None] * sc

        hl = packet.data['hl']
        fl = packet.data['fl']
        segment = packet.packed[hl:packet.size - fl]

        self.segments[sn] = segment
        if None in self.segments:  # don't have all segments yet
            return None
        self.body = self.desegmentize()
        return self.body

    def missing(self, begin=None, end=None):
        '''
        return list of missing packet numbers between begin (incl) and end (excl)
        '''
        if begin is None:
            begin = 0
        if end is None:
            end = self.highest  # don't return trailing empty numbers
        return [i for i in xrange(begin, end) if self.segments[i] is None]

    def desegmentize(self):
        '''
        Process message packet assumes already parsed outer so verified signature
        and processed header data
        '''
        sc = self.data['sc']
        self.packed = b''.join(self.segments)
        ml = self.data['ml']
        if sc > 1 and self.size != ml:
            emsg = ("Full message payload length '{0}' does not equal head field"
                                          " '{1}'".format(self.size, ml))
            raise raeting.PacketError(emsg)

        packet = RxPacket(stack = self.stack, data=self.data)
        packet.coat.packed = self.packed

        packet.coat.parse()
        packet.body.parse()
        self.complete = True

        return packet.body.data


