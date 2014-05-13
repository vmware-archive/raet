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

from .. import raeting, nacling, stacking
from . import paging, yarding, keeping

from ioflo.base.consoling import getConsole
console = getConsole()

class LaneStack(stacking.Stack):
    '''
    RAET protocol UXD (unix domain) socket stack object
    '''
    Count = 0
    Pk = raeting.packKinds.json # serialization pack kind of Uxd message
    Accept = True # accept any uxd messages if True from yards not already in lanes

    def __init__(self,
                 name='',
                 main=False,
                 keep=None,
                 dirpath='',
                 local=None,
                 lanename='lane',
                 yid=None,
                 yardname='',
                 sockdirpath='',
                 ha='',
                 bufcnt=10,
                 accept=None,
                 **kwa
                 ):
        '''
        Setup StackUxd instance
        '''
        if not name:
            name = "lanestack{0}".format(LaneStack.Count)
            LaneStack.Count += 1

        if not keep:
            keep = keeping.LaneKeep(dirpath=dirpath, stackname=name)

        if not local:
            self.remotes = odict()
            local = yarding.LocalYard(  stack=self,
                                        yid=yid,
                                        name=yardname,
                                        main=main,
                                        ha=ha,
                                        dirpath=sockdirpath,
                                        lanename=lanename)


        super(LaneStack, self).__init__(name=name,
                                        keep=keep,
                                        dirpath=dirpath,
                                        local=local,
                                        bufcnt=bufcnt,
                                        **kwa)

        self.books = odict()
        self.accept = self.Accept if accept is None else accept #accept uxd msg if not in lane

    def serverFromLocal(self):
        '''
        Create server from local data
        '''
        if not self.local:
            return None

        server = aiding.SocketUxdNb(ha=self.local.ha,
                            bufsize=raeting.UXD_MAX_PACKET_SIZE * self.bufcnt)
        return server

    def loadLocal(self, local=None):
        '''
        Load self.local from keep file else local or new
        '''
        data = self.keep.loadLocalData()
        if data and self.keep.verifyLocalData(data):
            self.local = yarding.LocalYard(stack=self,
                                     name=data['name'],
                                     ha=data['ha'])

        elif local:
            local.stack = self
            self.local = local

        else:
            self.local = yarding.LocalYard(stack=self)

    def loadRemotes(self):
        '''
        Load and add remote for each remote file
        '''
        datadict = self.keep.loadAllRemoteData()
        for data in datadict.values():
            if self.keep.verifyRemoteData(data):
                lot = yarding.RemoteYard(stack=self,
                                  name=data['name'],
                                  ha=data['ha'])
                self.addRemote(remote)


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

    def serviceRxes(self):
        '''
        Process all messages in .rxes deque
        '''
        while self.rxes:
            raw, sa, da = self.rxes.popleft()

            console.verbose("{0} received raw message \n{1}\n".format(self.name, raw))

            if sa not in self.remotes:
                if not self.accept:
                    emsg = "Unaccepted source ha = {0}. Dropping packet...\n".format(sa)
                    console.terse(emsg)
                    self.incStat('unaccepted_source_yard')
                    return
                try:
                    self.addRemote(yarding.RemoteYard(ha=sa))
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.incStat('invalid_source_yard')
                    return

            page = paging.RxPage(packed=raw)
            page.parse()

            self.processRx(page)

    def processRx(self, received):
        '''
        Retrieve next page from stack receive queue if any and parse
        '''
        console.verbose("{0} received page data\n{1}\n".format(self.name, received.data))
        console.verbose("{0} received page index = '{1}'\n".format(self.name, received.index))

        if received.paginated:
            book = self.books.get(received.index)
            if not book:
                book = paging.RxBook(stack=self)
                self.addBook(received.index, book)
            body = book.parse(received)
            if body is None: #not done yet
                return
            self.removeBook(book.index)
        else:
            body = received.data

        self.rxMsgs.append(body)

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing messages
        '''
        while self.txMsgs:
            body, duid = self.txMsgs.popleft() # duple (body dict, destination name)
            self.message(body, duid)
            console.verbose("{0} sending to {1}\n{2}\n".format(self.name, duid, body))

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
                        yard = self.remotes.get(ta)
                        if yard:
                            self.removeRemote(yard.uid)
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

    def message(self, body, duid):
        '''
        Sends message body to yard name and manages paging of long messages
        '''
        if duid is None:
            if not self.remotes:
                emsg = "No yard to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination")
                return
            duid = self.remotes.values()[0].name
        if duid not in self.remotes:
            emsg = "Invalid destination yard '{0}'\n".format(duid)
            console.terse(emsg)
            self.incStat("invalid_destination")
            return
        remote = self.remotes[duid]
        data = odict(syn=self.local.name, dyn=remote.name, mid=remote.nextMid())
        book = paging.TxBook(data=data, body=body, kind=self.Pk)
        try:
            book.pack()
        except raeting.PageError as ex:
            console.terse(str(ex) + '\n')
            self.incStat("packing_error")
            return

        for page in book.pages:
            self.txes.append((page.packed, remote.ha))


