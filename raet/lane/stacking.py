# -*- coding: utf-8 -*-
'''
stacking.py raet protocol stacking classes
'''
# pylint: skip-file
# pylint: disable=W0611

# Import python libs
import socket
import os
import errno

from collections import deque,  Mapping
try:
    import simplejson as json
except ImportError:
    import json

try:
    import msgpack
except ImportError:
    mspack = None

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding
from ioflo.base import storing

from . import raeting
from . import nacling
from . import packeting
from . import paging
from . import estating
from . import yarding
from . import keeping
from . import transacting

from ioflo.base.consoling import getConsole
console = getConsole()



class StackUxd(object):
    '''
    RAET protocol UXD (unix domain) socket stack object
    '''
    Count = 0
    Pk = raeting.packKinds.json # serialization pack kind of Uxd message
    Accept = True # accept any uxd messages if True from yards not already in lanes

    def __init__(self,
                 name='',
                 version=raeting.VERSION,
                 store=None,
                 lanename='lane',
                 yard=None,
                 yid=None,
                 yardname='',
                 ha='',
                 rxMsgs = None,
                 txMsgs = None,
                 rxes = None,
                 txes = None,
                 lane=None,
                 accept=None,
                 dirpath=None,
                 stats=None,
                 ):
        '''
        Setup StackUxd instance
        '''
        if not name:
            name = "stackUxd{0}".format(StackUxd.Count)
            StackUxd.Count += 1
        self.name = name
        self.version = version
        self.store = store or storing.Store(stamp=0.0)
        self.yards = odict() # remote uxd yards attached to this stack by name
        self.names = odict() # remote uxd yard names  by ha
        self.yard = yard or yarding.LocalYard(stack=self,
                                         name=yardname,
                                         yid=yid,
                                         ha=ha,
                                         prefix=lanename,
                                         dirpath=dirpath)
        self.books = odict()
        self.rxMsgs = rxMsgs if rxMsgs is not None else deque() # messages received
        self.txMsgs = txMsgs if txMsgs is not None else deque() # messages to transmit
        self.rxes = rxes if rxes is not None else deque() # uxd packets received
        self.txes = txes if txes is not None else deque() # uxd packets to transmit
        self.stats = stats if stats is not None else odict() # udp statistics
        self.statTimer = aiding.StoreTimer(self.store)

        self.lane = lane # or keeping.LaneKeep()
        self.accept = self.Accept if accept is None else accept #accept uxd msg if not in lane
        self.server = aiding.SocketUxdNb(ha=self.yard.ha, bufsize=raeting.UXD_MAX_PACKET_SIZE * 2)
        self.server.reopen()  # open socket
        self.yard.ha = self.server.ha  # update estate host address after open
        #self.lane.dumpLocalLane(self.yard)

    def fetchRemoteByHa(self, ha):
        '''
        Search for remote yard with matching ha
        Return yard if found Otherwise return None
        '''
        return self.yards.get(self.names.get(ha))

    def addRemoteYard(self, yard, name=None):
        '''
        Add a remote yard to .yards
        '''
        if name is None:
            name = yard.name

        if name in self.yards or name == self.yard.name:
            emsg = "Cannot add '{0}' yard alreadys exists".format(name)
            raise raeting.StackError(emsg)
        yard.stack = self
        self.yards[name] = yard
        if yard.ha in self.names or yard.ha == self.yard.ha:
            emsg = "Cannot add ha '{0}' yard alreadys exists".format(yard.ha)
            raise raeting.StackError(emsg)
        self.names[yard.ha] = yard.name

    def moveRemote(self, old, new):
        '''
        Move yard at key old name to key new name but keep same index
        '''
        if new in self.yards:
            emsg = "Cannot move, '{0}' yard already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.yards:
            emsg = "Cannot move '{0}' yard does not exist".format(old)
            raise raeting.StackError(emsg)

        yard = self.yards[old]
        index = self.yards.keys().index(old)
        yard.name = new
        self.names[yard.ha] = new
        del self.yards[old]
        self.yards.insert(index, yard.name, yard)

    def rehaRemote(self, old, new):
        '''
        change yard with old ha to new ha but keep same index
        '''
        if new in self.names:
            emsg = "Cannot reha, '{0}' yard already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.names:
            emsg = "Cannot reha '{0}' yard does not exist".format(old)
            raise raeting.StackError(emsg)

        name = self.names[old]
        yard = self.yards[name]
        yard.ha = new
        index = self.names.keys().index(old)
        del self.names[old]
        self.yards.insert(index, yard.ha, yard.name)

    def removeRemote(self, name):
        '''
        Remove yard at key name
        '''
        if name not in self.yards:
            emsg = "Cannot remove, '{0}' yard does not exist".format(name)
            raise raeting.StackError(emsg)

        yard = self.yards[name]
        del self.yards[name]
        del self.names[yard.ha]

    def addBook(self, index, book):
        '''
        Safely add book at index If not already there
        '''
        self.books[index] = book
        console.verbose( "Added book to {0} at '{1}'\n".format(self.name, index))

    def removeBook(self, index, book=None):
        '''
        Safely remove book at index If book identity same
        If book is None then remove without comparing identity
        '''
        if index in self.books:
            if book:
                if book is self.books[index]:
                    del  self.books[index]
            else:
                del self.books[index]

    def clearStats(self):
        '''
        Set all the stat counters to zero and reset the timer
        '''
        for key, value in self.stats.items():
            self.stats[key] = 0
        self.statTimer.restart()

    def clearStat(self, key):
        '''
        Set the specified state counter to zero
        '''
        if key in self.stats:
            self.stats[key] = 0

    def incStat(self, key, delta=1):
        '''
        Increment stat key counter by delta
        '''
        if key in self.stats:
            self.stats[key] += delta
        else:
            self.stats[key] = delta

    def updateStat(self, key, value):
        '''
        Set stat key to value
        '''
        self.stats[key] = value

    def serviceUxdRx(self):
        '''
        Service the Uxd receive and fill the .rxes deque
        '''
        if self.server:
            while True:
                rx, ra = self.server.receive()  # if no data the duple is ('',None)
                if not rx:  # no received data so break
                    break
                # triple = ( packet, source address, destination address)
                self.rxes.append((rx, ra, self.server.ha))

    def serviceRxes(self):
        '''
        Process all messages in .rxes deque
        '''
        while self.rxes:
            self.processUxdRx()

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing messages
        '''
        while self.txMsgs:
            body, name = self.txMsgs.popleft() # duple (body dict, destination name)
            self.message(body, name)
            console.verbose("{0} sending\n{1}\n".format(self.name, body))

    def serviceTxes(self):
        '''
        Service the .txes deque to send Uxd messages
        '''
        if self.server:
            laters = deque()
            blocks = []

            while self.txes:
                tx, ta = self.txes.popleft()  # duple = (packet, destination address)

                if ta in blocks: # already blocked on this iteration
                    laters.append((tx, ta)) # keep sequential
                    continue

                try:
                    self.server.send(tx, ta)
                except socket.error as ex:
                    if ex.errno == errno.ECONNREFUSED:
                        console.terse("socket.error = {0}\n".format(ex))
                        self.incStat("stale_transmit_yard")
                        yard = self.fetchRemoteByHa(ta)
                        if yard:
                            self.removeRemote(yard.name)
                            console.terse("Reaped yard {0}\n".format(yard.name))
                    elif ex.errno == errno.EAGAIN or ex.errno == errno.EWOULDBLOCK:
                        #busy with last message save it for later
                        laters.append((tx, ta))
                        blocks.append(ta)

                    else:
                        #console.verbose("socket.error = {0}\n".format(ex))
                        raise
            while laters:
                self.txes.append(laters.popleft())

    def serviceUxd(self):
        '''
        Service the UXD receive and transmit queues
        '''
        self.serviceUxdRx()
        self.serviceTxes()

    def serviceRx(self):
        '''
        Service:
           Uxd Socket receive
           rxes queue
        '''
        self.serviceUxdRx()
        self.serviceRxes()

    def serviceTx(self):
        '''
        Service:
           txMsgs deque
           txes deque and send Uxd messages
        '''
        self.serviceTxMsgs()
        self.serviceTxes()

    def serviceAll(self):
        '''
        Service or Process:
           Uxd Socket receive
           rxes queue
           txMsgs queue
           txes queue and Uxd Socket send
        '''
        self.serviceUxdRx()
        self.serviceRxes()
        self.serviceTxMsgs()
        self.serviceTxes()

    def txUxd(self, packed, name):
        '''
        Queue duple of (packed, da) on stack .txes queue
        Where da is the uxd destination address associated with
        the yard with name
        If name is None then it will default to the first entry in .yards
        '''
        if name is None:
            if not self.yards:
                emsg = "No yard to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination_yard")
                return
            name = self.yards.values()[0].name
        if name not in self.yards:
            msg = "Invalid destination yard name '{0}'".format(name)
            console.terse(msg + '\n')
            self.incStat("invalid_destination_yard")
            return
        self.txes.append((packed, self.yards[name].ha))

    def transmit(self, msg, name=None):
        '''
        Append duple (msg, name) to .txMsgs deque
        If msg is not mapping then raises exception
        If name is None then txUxd will supply default
        '''
        if not isinstance(msg, Mapping):
            emsg = "Invalid msg, not a mapping {0}\n".format(msg)
            console.terse(emsg)
            self.incStat("invalid_transmit_body")
            return
        self.txMsgs.append((msg, name))

    def message(self, body, name):
        '''
        Sends message body to yard name and manages paging of long messages
        '''
        if name is None:
            if not self.yards:
                emsg = "No yard to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination_yard")
                return
            name = self.yards.values()[0].name
        if name not in self.yards:
            emsg = "Invalid destination yard name '{0}'\n".format(name)
            console.terse(emsg)
            self.incStat("invalid_destination_yard")
            return
        remote = self.yards[name]
        data = odict(syn=self.yard.name, dyn=remote.name, mid=remote.nextMid())
        book = paging.TxBook(data=data, body=body, kind=self.Pk)
        try:
            book.pack()
        except raeting.PageError as ex:
            console.terse(str(ex) + '\n')
            self.incStat("packing_error")
            return

        print "Pages {0}".format(len(book.pages))

        for page in book.pages:
            self.txes.append((page.packed, remote.ha))

    def processUxdRx(self):
        '''
        Retrieve next page from stack receive queue if any and parse
        '''
        page = self.fetchParseUxdRx()
        if not page:
            return

        console.verbose("{0} received page data\n{1}\n".format(self.name, page.data))
        console.verbose("{0} received page index = '{1}'\n".format(self.name, page.index))

        if page.paginated:
            book = self.books.get(page.index)
            if not book:
                book = paging.RxBook(stack=self)
                self.addBook(page.index, book)
            body = book.parse(page)
            if body is None: #not done yet
                return
            self.removeBook(book.index)
        else:
            body = page.data

        self.rxMsgs.append(body)

    def fetchParseUxdRx(self):
        '''
        Fetch from UXD deque next message tuple
        Parse raw message
        Return body if no errors
        Otherwise return None
        '''
        try:
            raw, sa, da = self.rxes.popleft()
        except IndexError:
            return None

        console.verbose("{0} received raw message \n{1}\n".format(self.name, raw))

        if sa not in self.names:
            if not self.accept:
                emsg = "Unaccepted source ha = {0}. Dropping packet...\n".format(sa)
                console.terse(emsg)
                self.incStat('unaccepted_source_yard')
                return None
            try:
                self.addRemoteYard(yarding.RemoteYard(ha=sa))
            except raeting.StackError as ex:
                console.terse(str(ex) + '\n')
                self.incStat('invalid_source_yard')
                return None

        page = paging.RxPage(packed=raw)
        page.parse()
        return page

