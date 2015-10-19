# -*- coding: utf-8 -*-
#pylint: skip-file
'''
paging module provides classes for RAET UXD messaging management

'''

# Import python libs
from collections import Mapping
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

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import PackKind

class Part(object):
    '''
    Base class for parts of a RAET page
    Should be subclassed
    '''

    def __init__(self, page=None, **kwa):
        '''
        Setup Part instance
        '''
        self.page = page  # Page this Part belongs too
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
    RAET protocol page header class
    Manages the header portion of a page
    '''
    def __init__(self, **kwa):
        '''
        Setup Head instance
        '''
        super(Head, self).__init__(**kwa)

class TxHead(Head):
    '''
    RAET protocol transmit page header class
    '''
    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        data = self.page.data  # for speed
        lines = []
        for k, v in data.items():
            lines.append("{key} {val:{fmt}}".format(
                            key=k, val=v, fmt=raeting.PAGE_FIELD_FORMATS[k]))

        self.packed = ns2b('\n'.join(lines)) + raeting.HEAD_END


class RxHead(Head):
    '''
    RAET protocol receive page header class
    '''
    def parse(self):
        '''
        Unpacks head. Parses head and updates .page.data
        Raises PageError if failure occurs
        '''
        self.packed = b''
        data = self.page.data  # for speed
        packed = self.page.packed  # for speed

        if not packed:
            emsg = "Packed empty, nothing to parse."
            console.terse(emsg)
            raise raeting.PageError(emsg)

        if (not packed.startswith(ns2b('ri RAET\n')) or raeting.HEAD_END not in packed):
            emsg = "Unrecognized page head\n"
            console.terse(emsg)
            raise raeting.PageError(emsg)

        front, sep, back = packed.partition(raeting.HEAD_END)
        self.packed = front + sep
        self.page.body.packed = back

        kit = odict()
        lines = str(front.decode(encoding='ISO-8859-1')).split('\n')
        for line in lines:
            key, val = line.split(' ')
            if key not in raeting.PAGE_FIELDS:
                emsg = "Unknown head field '{0}'".format(key)
                raise raeting.PageError(emsg)
            if 'x' in raeting.PAGE_FIELD_FORMATS[key]:
                val = int(val, 16)
            elif 'd' in raeting.PAGE_FIELD_FORMATS[key]:
                val = int(val)
            elif 'f' in raeting.PAGE_FIELD_FORMATS[key]:
                val = float(val)
            kit[key] = val

        data.update(kit)


class Body(Part):
    '''
    RAET protocol page body class
    Manages the message portion of the page
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
    RAET protocol tx page body class
    '''
    def pack(self):
        '''
        Composes .packed, which is the packed form of this part
        '''
        self.packed = b''
        pk = self.page.data['pk']

        if pk == PackKind.json:
            if self.data:
                self.packed = ns2b(json.dumps(self.data,
                                         separators=(',', ':')))
        elif pk == PackKind.pack:
            if self.data:
                if not msgpack:
                    emsg = "Msgpack not installed."
                    raise raeting.PacketError(emsg)
                self.packed = msgpack.dumps(self.data,
                                            encoding='utf-8')
        else:
            emsg = "Unrecognized message pack kind '{0}'\n".format(pk)
            console.terse(emsg)
            raise raeting.PageError(emsg)

        if self.size > raeting.MAX_MESSAGE_SIZE:
            emsg = "Packed message length of {0}, exceeds max of {1}".format(
                     self.size, raeting.MAX_MESSAGE_SIZE)
            raise raeting.PageError(emsg)

class RxBody(Body):
    '''
    RAET protocol rx packet body class
    '''
    def parse(self):
        '''
        Parses body. Assumes already unpacked.
        Results in updated .data
        '''
        self.data = odict()
        pk = self.page.data['pk']

        if pk not in list(PackKind):
            emsg = "Unrecognizable page body."
            raise raeting.PageError(emsg)

        if pk == PackKind.json:
            if self.packed:
                self.data = json.loads(self.packed.decode(encoding='utf-8'),
                                       object_pairs_hook=odict)
        elif pk == PackKind.pack:
            if self.packed:
                if not msgpack:
                    emsg = "Msgpack not installed."
                    raise raeting.PacketError(emsg)
                self.data = msgpack.loads(self.packed,
                                          object_pairs_hook=odict,
                                          encoding='utf-8')

        if not isinstance(self.data, Mapping):
            emsg = "Message body not a mapping\n"
            console.terse(emsg)
            raise raeting.PageError(emsg)

class Page(object):
    '''
    RAET UXD protocol page object. Support sectioning of messages into Uxd pages
    '''

    def __init__(self, stack=None, data=None):
        ''' Setup Page instance. Meta data for a packet. '''
        self.stack = stack
        self.data = odict(raeting.PAGE_DEFAULTS)
        if data:
            self.data.update(data)
        self.packed = b''  # packed string

    @property
    def size(self):
        '''
        Property is the length of the .packed of this page
        '''
        return len(self.packed)

    @property
    def paginated(self):
        '''
        Property is True if the page count > 1 else False
        '''
        return (True if self.data.get('pc', 0) > 1 else False)

class TxPage(Page):
    '''
    RAET Protocol Transmit Page object
    '''
    def __init__(self, embody=None, **kwa):
        '''
        Setup TxPacket instance
        '''
        super(TxPage, self).__init__(**kwa)
        self.head = TxHead(page=self)
        self.body = TxBody(page=self, data=embody)

    @property
    def index(self):
        '''
        Property is unique message tuple (ln, rn, si, bi)
        ln = local yard name which for transmit is sn
        rn = remote yard name which for transmit is dn
        si = session id
        bi = book id
        '''
        return (self.data['sn'], self.data['dn'], self.data['si'], self.data['bi'], )

    def prepack(self):
        '''
        Pack without raising oversize exception
        '''
        self.head.pack()
        self.body.pack()
        self.packed = self.head.packed + self.body.packed

    def pack(self):
        '''
        Pack serialize message body data and check for size limit
        '''
        self.prepack()

        if self.size > raeting.UXD_MAX_PACKET_SIZE: #raeting.MAX_MESSAGE_SIZE
            emsg = "Message length of {0}, exceeds max of {1}\n".format(
                     self.size, raeting.UXD_MAX_PACKET_SIZE)
            console.terse(emsg)
            raise raeting.PageError(emsg)

class RxPage(Page):
    '''
    RAET Protocol Receive Page object
    '''
    def __init__(self, packed=None, **kwa):
        '''
        Setup RxPage instance
        '''
        super(RxPage, self).__init__(**kwa)
        self.head = RxHead(page=self)
        self.body = RxBody(page=self)
        self.packed = packed or ''

    @property
    def index(self):
        '''
        Property is unique message tuple (ln, rn, si, bi)
        ln = local yard name which for receive is dn
        rn = remote yard name which for receive is sn
        si = session id
        bi = book id
        '''
        return (self.data['dn'], self.data['sn'], self.data['si'], self.data['bi'],)

    def parse(self, packed=None):
        '''
        Parse (deserialize message) result in self.data
        '''
        if packed:
            self.packed = packed

        self.head.parse() #this sets self.body.packed
        self.body.parse()

class Book(object):
    '''
    Manages messages, sectioning when needed and the associated pages
    '''
    def __init__(self, stack=None, data=None, body=None):
        '''
        Setup instance
        '''
        self.stack = stack
        self.data = odict(raeting.PAGE_DEFAULTS)
        if data:
            self.data.update(data)
        self.body = body #body data of message
        self.packed = b'' # complete unsectionalize packed message body no headers

    @property
    def size(self):
        '''
        Property is the length of the .packed
        '''
        return len(self.packed)

class TxBook(Book):
    '''
    Manages an outgoing message and its associated pages(s)
    '''
    def __init__(self, **kwa):
        '''
        Setup instance
        '''
        super(TxBook, self).__init__(**kwa)
        self.pages = []

    @property
    def index(self):
        '''
        Property is unique message tuple (rn, ln, si, bi)
        rn = remote yard name which for transmit is sn
        ln = local yard name which for transmit is dn
        si = session id
        bi = book id
        '''
        return (self.data['sn'], self.data['dn'], self.data['si'], self.data['bi'],)

    def pack(self, data=None, body=None):
        '''
        Convert message in .body into one or more pages
        '''
        if data:
            self.data.update(data)
        if body is not None:
            self.body = body

        self.pages = []
        page = TxPage(  stack=self.stack,
                        data=self.data,
                        embody=self.body)

        page.prepack()
        self.packed = page.body.packed
        if page.size <= raeting.UXD_MAX_PACKET_SIZE:
            self.pages.append(page)
        else:
            self.paginate(headsize=len(page.head.packed))

    def paginate(self, headsize):
        '''
        Create packeted segments from .packed using headsize
        '''
        extrasize = 2 #need better estimate
        hotelsize = headsize + extrasize
        secsize = raeting.UXD_MAX_PACKET_SIZE - hotelsize

        seccount = (self.size // secsize) + (1 if self.size % secsize else 0)
        for i in range(seccount):
            if i == seccount - 1: #last section
                section = self.packed[i * secsize:]
            else:
                section = self.packed[i * secsize: (i+1) * secsize]
            data = odict(self.data) #make copy so self.data is first page
            data['pn'] = i
            data['pc'] = seccount
            page = TxPage( stack=self.stack, data=data)
            page.body.packed = section
            page.head.pack()
            page.packed = page.head.packed + page.body.packed
            self.pages.append(page)


class RxBook(Book):
    '''
    Manages sectioned messages and the associated pages
    '''
    def __init__(self, sections=None, **kwa):
        '''
        Setup instance
        '''
        super(RxBook, self).__init__(**kwa)
        self.sections = sections if sections is not None else []
        self.complete = False

    @property
    def index(self):
        '''
        Property is unique message tuple (ln, rn, si, bi)
        ln = local yard name which for receive is dn
        rn = remote yard name which for receive is sn
        si = session id
        bi = book id
        '''
        return (self.data['dn'], self.data['sn'], self.data['si'], self.data['bi'], )

    def parse(self, page):
        '''
        Process a given page. Assumes page.head has been successfully parsed
        '''
        if not page.paginated: # not a paginated message so can parse body as is
            self.data.update(page.data)
            page.body.parse()
            self.body = page.body.data
            self.complete = True
            return self.body

        #paginated so add to pages
        pc = page.data['pc'] #page count
        pn = page.data['pn']
        console.verbose("page count={0} number={1} session id={2} book id={2}\n".format(
                     pc, pn, page.data['si'], page.data['bi']))

        if not self.sections: #update data from first page received
            self.data.update(page.data)
            self.sections = [None] * pc

        self.sections[pn] = page.body.packed
        if None in self.sections: #don't have all sections yet
            return None
        self.body = self.desectionize()
        return self.body

    def desectionize(self):
        '''
        Generate message from pages
        '''
        self.packed = b''.join(self.sections)
        page = RxPage(stack = self.stack, data=self.data)
        page.body.packed = self.packed
        page.body.parse()
        self.complete = True

        return page.body.data


