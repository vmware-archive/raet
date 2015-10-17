# -*- coding: utf-8 -*-
'''
stacking.py raet protocol stacking classes
'''
# pylint: skip-file
# pylint: disable=W0611

# Import python libs
import socket
import sys
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
from ioflo.aid.odicting import odict
from ioflo.base import nonblocking

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting, nacling, stacking
from . import paging, yarding
from ..raeting import PackKind

from ioflo.base.consoling import getConsole
console = getConsole()

class LaneStack(stacking.Stack):
    '''
    RAET protocol UXD (unix domain) socket stack object
    '''
    Count = 0
    Uid =  0
    Pk = PackKind.json.value # serialization pack kind of Uxd message
    Accept = True # accept any uxd messages if True from yards not already in lanes

    def __init__(self,
                 local=None, #passed up from subclass
                 name='',
                 puid=None,
                 uid=None,
                 lanename='lane',
                 sockdirpath='',
                 ha='',
                 bufcnt=100,
                 accept=None,
                 **kwa
                 ):
        '''
        Setup LaneStack instance
        '''
        if getattr(self, 'puid', None) is None:
            self.puid = puid if puid is not None else self.Uid

        local = local or yarding.Yard(stack=self,
                                            name=name,
                                            uid=uid,
                                            ha=ha,
                                            dirpath=sockdirpath,
                                            lanename=lanename)

        super(LaneStack, self).__init__(puid=puid,
                                        local=local,
                                        bufcnt=bufcnt,
                                        **kwa)

        self.haRemotes = odict() # remotes indexed by ha host address
        self.accept = self.Accept if accept is None else accept #accept uxd msg if not in lane

    def serverFromLocal(self):
        '''
        Create local listening server for stack
        '''

        if not sys.platform == 'win32':
            server = nonblocking.SocketUxdNb(ha=self.ha,
                                bufsize=raeting.UXD_MAX_PACKET_SIZE * self.bufcnt)
        else:
            server = nonblocking.WinMailslotNb(ha=self.ha,
                                bufsize=raeting.UXD_MAX_PACKET_SIZE * self.bufcnt)
        return server

    def addRemote(self, remote):
        '''
        Add a remote to indexes
        '''
        if remote.ha in self.haRemotes or remote.ha == self.local.ha:
            emsg = "Cannot add remote at ha '{0}', alreadys exists".format(remote.ha)
            raise raeting.StackError(emsg)
        super(LaneStack, self).addRemote(remote)
        self.haRemotes[remote.ha] = remote

    def removeRemote(self, remote):
        '''
        Remove remote from all remotes dicts
        '''
        super(LaneStack, self).removeRemote(remote)
        del self.haRemotes[remote.ha]

    def _handleOneRx(self):
        '''
        Handle on message from .rxes deque
        Assumes that there is a message on the .rxes deque
        '''
        raw, sa = self.rxes.popleft()
        console.verbose("{0} received raw message \n{1}\n".format(self.name, raw))
        page = paging.RxPage(packed=raw)

        try:
            page.head.parse()
        except raeting.PageError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('invalid_page_header')

        dn = page.data['dn'] # destination yard name
        if dn != self.local.name:
            emsg = "Invalid destination yard name = {0}. Dropping packet...\n".format(dn)
            console.concise( emsg)
            self.incStat('invalid_destination')

        sn = page.data['sn'] # source yard name
        if sn not in self.nameRemotes:
            if not self.accept:
                emsg = "Unaccepted source yard name = {0}. Dropping packet...\n".format(sn)
                console.terse(emsg)
                self.incStat('unaccepted_source_yard')
                return

            # sa is None on Windows, Mailslots don't convey their source addresses
            # So we need to construct a compatible source address from the local's dirpath
            # and lanename. Use the yarding.Yard.computeHa utility function for this.
            if sa is None:
                sa, haDirpath = yarding.Yard.computeHa(self.local.dirpath, self.local.lanename, sn)

            try:
                self.addRemote(yarding.RemoteYard(stack=self, ha=sa)) # sn and sa are assume compat
            except raeting.StackError as ex:
                console.terse(str(ex) + '\n')
                self.incStat('invalid_source_yard')
                return

        remote = self.nameRemotes[sn]
        si = page.data['si']

        if si != remote.rsid:
            remote.rsid = si
            remote.removeStaleBooks()

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

        self.rxMsgs.append((body, remote.name))

    def  _handleOneTxMsg(self):
        '''
        Take one message from .txMsgs deque and handle it
        Assumes there is a message on the deque
        '''
        body, uid = self.txMsgs.popleft() # duple (body dict, destination name)
        self.message(body, uid=uid)
        console.verbose("{0} sending to {1}\n{2}\n".format(self.name, uid, body))

    def _handleOneTx(self, laters, blocks):
        '''
        Handle one message on .txes deque
        Assumes there is a message
        laters is deque of messages to try again later
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
                ta, self.ha, ex))
            err = raeting.get_exception_error(ex)
            if err == errno.ECONNREFUSED or err == errno.ENOENT:
                self.incStat("stale_transmit_yard")
                yard = self.haRemotes.get(ta)
                if yard:
                    self.removeRemote(yard)
                    console.terse("Reaped yard {0}\n".format(yard.name))
            elif err in [errno.EAGAIN, errno.EWOULDBLOCK, errno.ENOBUFS]:
                self.incStat("busy_transmit_yard")
                #busy with last message save it for later
                laters.append((tx, ta))
                blocks.append(ta)

            else:
                self.incStat("error_transmit_yard")
                raise

    def message(self, body, uid=None):
        '''
        Sends message body to yard  given by uid and manages paging of long messages
        '''
        if uid is None:
            if not self.remotes:
                emsg = "No yard to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination")
                return
            uid = self.remotes.values()[0].uid
        if uid not in self.remotes:
            emsg = "Invalid destination yard '{0}'\n".format(uid)
            console.terse(emsg)
            self.incStat("invalid_destination")
            return
        remote = self.remotes[uid]
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


