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
    Yid = 1
    Pk = raeting.packKinds.json # serialization pack kind of Uxd message
    Accept = True # accept any uxd messages if True from yards not already in lanes

    def __init__(self,
                 name='',
                 main=None,
                 keep=None,
                 dirpath='',
                 basedirpath='',
                 local=None,
                 localname='',
                 lanename='lane',
                 yid=None,
                 sockdirpath='',
                 ha='',
                 bufcnt=10,
                 accept=None,
                 **kwa
                 ):
        '''
        Setup LaneStack instance

        stack.name and stack.local.name will match
        '''
        self.nyid = self.Yid # yid of initial next estate to add to road
        self.accept = self.Accept if accept is None else accept #accept uxd msg if not in lane
        if not name:
            name = "lane{0}".format(LaneStack.Count)
            LaneStack.Count += 1

        if not local:
            self.remotes = odict()
            local = yarding.LocalYard(  stack=self,
                                        yid=yid,
                                        name=localname,
                                        main=main,
                                        ha=ha,
                                        dirpath=sockdirpath,
                                        lanename=lanename)
        else:
            if main is not None:
                local.main = True if main else False

        if not keep:
            keep = keeping.LaneKeep(dirpath=dirpath,
                                    basedirpath=basedirpath,
                                    stackname=name)

        super(LaneStack, self).__init__(name=name,
                                        keep=keep,
                                        dirpath=dirpath,
                                        basedirpath=basedirpath,
                                        local=local,
                                        localname=localname,
                                        bufcnt=bufcnt,
                                        **kwa)

    def nextYid(self):
        '''
        Generates next yard id number.
        '''
        self.nyid += 1
        if self.nyid > 0xffffffffL:
            self.nyid = 1  # rollover to 1
        return self.nyid

    def serverFromLocal(self):
        '''
        Create server from local data
        '''
        if not self.local:
            return None

        server = aiding.SocketUxdNb(ha=self.local.ha,
                            bufsize=raeting.UXD_MAX_PACKET_SIZE * self.bufcnt)
        return server

    def fetchRemoteFromHa(self, ha):
        '''
        Return the remote yard associated with the UXD host address filepath.
        If not found return None
        '''
        head, tail = os.path.split(ha)
        if not tail:
            emsg = "Invalid format for ha '{0}'. No file\n".format(ha)
            console.concise(emsg)
            return None

        root, ext = os.path.splitext(tail)

        if ext != ".uxd":
            emsg = "Invalid format for ha '{0}'. Ext not 'uxd'\n".format(ha)
            console.concise(emsg)
            return None

        lanename, sep, yardname = root.rpartition('.')
        if not sep:
            emsg = "Invalid format for ha '{0}'. No lane.name\n".format(ha)
            console.concise(emsg)
            return None

        return self.fetchRemoteByName(yardname)

    def loadLocal(self, local=None, name=''):
        '''
        Load self.local from keep file else local or new
        '''
        data = self.keep.loadLocalData()
        if data and self.keep.verifyLocalData(data):
            self.local = yarding.LocalYard(stack=self,
                                           yid=data['uid'],
                                           name=data['name'],
                                           ha=data['ha'],
                                           main=data['main'],
                                           sid=data['sid'],
                                           lanename=data['lanename'])
            self.name = data['stack']
            self.nyid = data['nyid']
            self.accept = data['accept']

        elif local:
            local.stack = self
            self.local = local

        else:
            self.local = yarding.LocalYard(stack=self, name=name)

    def loadRemotes(self):
        '''
        Load and add remote for each remote file
        '''
        datadict = self.keep.loadAllRemoteData()
        for data in datadict.values():
            if self.keep.verifyRemoteData(data):
                remote = yarding.RemoteYard(stack=self,
                                            yid=data['uid'],
                                            name=data['name'],
                                            ha=data['ha'],
                                            sid=data['sid'],)
                self.addRemote(remote)

    def _handleOneRx(self):
        '''
        Handle on message from .rxes deque
        Assumes that there is a message on the .rxes deque
        '''
        raw, sa, da = self.rxes.popleft()
        console.verbose("{0} received raw message \n{1}\n".format(self.name, raw))
        page = paging.RxPage(packed=raw)

        try:
            page.head.parse()
        except PageError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('invalid_page_header')

        dn = page.data['dn']
        if dn != self.local.name:
            emsg = "Invalid destination yard name = {0}. Dropping packet...\n".format(dn)
            console.concise( emsg)
            self.incStat('invalid_destination')

        sn = page.data['sn']
        if sn not in self.uids:
            if not self.accept:
                emsg = "Unaccepted source yard name = {0}. Dropping packet...\n".format(sn)
                console.terse(emsg)
                self.incStat('unaccepted_source_yard')
                return

            try:
                self.addRemote(yarding.RemoteYard(ha=sa)) # sn and sa are assume compat
            except raeting.StackError as ex:
                console.terse(str(ex) + '\n')
                self.incStat('invalid_source_yard')
                return

        remote = self.remotes[self.uids[sn]]
        si = page.data['si']
        if si != 0 and not remote.validRsid(si):
            emsg = "Stale sid '{0}' in page from remote {1}\n".format(si, remote.name)
            console.terse(emsg)
            self.incStat('stale_sid_attempt')
            return

        if si != remote.rsid:
            remote.rsid = si
            remote.removeStaleBooks(renew=(si == 0))

        self.processRx(page, remote)

    def serviceRxes(self):
        '''
        Process all messages in .rxes deque
        '''
        while self.rxes:
            self._handleOneRx()

    def serviceRxOnce(self):
        '''
        Process one messages in .rxes deque
        '''
        if self.rxes:
            self._handleOneRx()

    def processRx(self, received, remote):
        '''
        Retrieve next page from stack receive queue if any and parse
        Assumes received header has been parsed
        '''
        console.verbose("{0} received page header\n{1}\n".format(self.name, received.data))
        console.verbose("{0} received page index = '{1}'\n".format(self.name, received.index))

        if received.paginated:
            index = received.index #(received.data['si'], received.data['bi'])
            book = remote.books.get(index)
            if not book:
                if received.data['pn'] != 0: # not first page to missed first page
                    emsg = "Missed page  prior to '{0}' from remote {1}\n".format(
                            received.data['pn'], remote.name)
                    console.terse(emsg)
                    self.incStat('missed_page')
                    return
                book = paging.RxBook(stack=self)
                remote.addBook(index, book)
            book.parse(received)
            if not book.complete:
                return
            remote.removeBook(index)
            body = book.body
        else:
            received.body.parse()
            body = received.body.data

        self.rxMsgs.append(body)

    def  _handleOneTxMsg(self):
        '''
        Take one message from .txMsgs deque and handle it
        Assumes there is a message on the deque
        '''
        body, duid = self.txMsgs.popleft() # duple (body dict, destination name)
        self.message(body, duid)
        console.verbose("{0} sending to {1}\n{2}\n".format(self.name, duid, body))

    def _handleOneTx(self, laters, blocks):
        '''
        Handle one message on .txes deque
        Assumes there is a message
        aters is deque of messages to try again later
        blocks is list of blocked destination address so put all associated into laters
        '''
        tx, ta = self.txes.popleft()  # duple = (packet, destination address)

        if ta in blocks: # already blocked on this iteration
            laters.append((tx, ta)) # keep sequential
            return

        try:
            self.server.send(tx, ta)
        except Exception as ex:
            console.concise("Error sending to '{0}' from '{1}: {2}\n".format(
                ta, self.local.ha, ex))
            if ex.errno == errno.ECONNREFUSED or ex.errno == errno.ENOENT:
                self.incStat("stale_transmit_yard")
                yard = self.fetchRemoteFromHa(ta)
                if yard:
                    self.removeRemote(yard.uid)
                    console.terse("Reaped yard {0}\n".format(yard.name))
            elif ex.errno == errno.EAGAIN or ex.errno == errno.EWOULDBLOCK:
                self.incStat("busy_transmit_yard")
                #busy with last message save it for later
                laters.append((tx, ta))
                blocks.append(ta)

            else:
                self.incStat("error_transmit_yard")
                raise

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
        data = odict(pk=self.Pk,
                     sn=self.local.name,
                     dn=remote.name,
                     si=remote.sid,
                     bi=remote.nextBid())
        book = paging.TxBook(data=data, body=body)
        try:
            book.pack()
        except raeting.PageError as ex:
            console.terse(str(ex) + '\n')
            self.incStat("packing_error")
            return

        for page in book.pages:
            self.txes.append((page.packed, remote.ha))


