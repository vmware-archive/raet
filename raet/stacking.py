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

class Stack(object):
    '''
    RAET protocol base stack object.
    Should be subclassed for specific transport type such as UDP or UXD
    '''
    Count = 0

    def __init__(self,
                 name='',
                 main=False,
                 version=raeting.VERSION,
                 store=None,
                 local=None,
                 keep=None,
                 dirpath=None,
                 rxMsgs=None,
                 txMsgs=None,
                 rxes=None,
                 txes=None,
                 stats=None,
                 ):
        '''
        Setup StackUdp instance
        '''
        if not name:
            name = "stack{0}".format(Stack.Count)
            Stack.Count += 1
        self.name = name
        self.version = version
        self.store = store or storing.Store(stamp=0.0)
        self.keep = keep or keeping.Keep(dirpath=dirpath, stackname=self.name)
        kept = self.loadLocal() # load local data from saved data
        self.local = kept or local
        if self.local:
            self.local.stack = self
        self.remotes = odict() # remotes indexed by id
        self.rids = odict() # remote ids indexed by name
        kepts = self.loadAllRemote() # load remotes from saved data
        for kept in kepts:
            self.addRemote(kept)

        self.rxMsgs = rxMsgs if rxMsgs is not None else deque() # messages received
        self.txMsgs = txMsgs if txMsgs is not None else deque() # messages to transmit
        self.rxes = rxes if rxes is not None else deque() # udp packets received
        self.txes = txes if txes is not None else deque() # udp packet to transmit
        self.stats = stats if stats is not None else odict() # udp statistics
        self.statTimer = aiding.StoreTimer(self.store)
        self.server = None

        self.dumpLocal() # save local data
        self.dumpAllRemote() # save remote data

    def addRemote(self, remote, rid=None):
        '''
        Add a remote  to .remotes
        '''
        if rid is None:
            rid = remote.rid
        if rid in self.remotes:
            emsg = "Cannot add remote at rid '{0}', alreadys exists".format(rid)
            raise raeting.StackError(emsg)
        remote.stack = self
        self.remotes[rid] = remote
        if remote.name in self.rids:
            emsg = "Cannot add remote with name '{0}', alreadys exists".format(remote.name)
            raise raeting.StackError(emsg)
        self.rids[remote.name] = remote.rid

    def moveRemote(self, old, new):
        '''
        Move remote at key old rid to key new rid but keep same index
        '''
        if new in self.remotes:
            emsg = "Cannot move, remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.remotes:
            emsg = "Cannot move remote '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        remote = self.remotes[old]
        index = self.remotes.keys().index(old)
        remote.rid = new
        self.rids[remote.name] = new
        del self.remotes[old]
        self.remotes.insert(index, remote.rid, remote)

    def renameRemote(self, old, new):
        '''
        rename remote with old name to new name but keep same index
        '''
        if new in self.rids:
            emsg = "Cannot rename remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.rids:
            emsg = "Cannot rename remote '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        rid = self.rids[old]
        remote = self.remotes[rid]
        remote.name = new
        index = self.rids.keys().index(old)
        del self.rids[old]
        self.rids.insert(index, remote.name, remote.rid)

    def removeRemote(self, rid):
        '''
        Remove remote at key rid
        '''
        if rid not in self.remotes:
            emsg = "Cannot remove remote '{0}', does not exist".format(rid)
            raise raeting.StackError(emsg)

        remote = self.remotes[rid]
        del self.remotes[rid]
        del self.rids[remote.name]

    def fetchRemoteByName(self, name):
        '''
        Search for remote with matching name
        Return remote if found Otherwise return None
        '''
        return self.remotes.get(self.rids.get(name))

    def clearLocal(self):
        '''
        Clear local keep
        '''
        self.keep.clearLocalData()

    def clearRemote(self, remote):
        '''
        Clear remote keep of remote
        '''
        self.keep.clearRemoteData(remote.rid)

    def clearAllRemote(self):
        '''
        Clear all remote keeps
        '''
        self.keep.clearAllRemoteData()

    def dumpLocal(self):
        '''
        Dump keeps of local
        '''
        self.keep.dumpLocalData()

    def dumpRemote(self, remote):
        '''
        Dump keeps of remote
        '''
        self.keep.dumpRemoteData(remote.rid)

    def dumpAllRemote(self):
        '''
        Dump all remotes estates to keeps'''
        self.keep.dumpAllRemoteData(self.remotes)

    def loadLocal(self):
        '''
        Load and Return local if keeps found
        '''
        localdata = self.keep.loadLocalData()
        return None

    def loadAllRemote(self):
        '''
        Load and Return list of remotes
        '''
        data = self.keep.loadAllRemoteData()

        for key, road in data.items():
            '''
            '''
        return data

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

    def serviceRx(self):
        '''
        Service the server receive and fill the rxes deque
        '''
        if self.server:
            while True:
                rx, ra = self.server.receive()  # if no data the duple is ('',None)
                if not rx:  # no received data so break
                    break
                # triple = ( packet, source address, destination address)
                self.rxes.append((rx, ra, self.server.ha))

        return None

    def serviceRxes(self):
        '''
        Process all messages in .rxes deque
        '''
        while self.rxes:
            self.processRx()

    def processRx(self):
        '''
        Retrieve next packet from stack receive queue if any and parse
        Process associated transaction or reply with new correspondent transaction
        '''
        try:
            raw, sa, da = self.rxes.popleft()
        except IndexError:
            return None

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing  messages
        '''
        while self.txMsgs:
            body, drid = self.txMsgs.popleft() # duple (body dict, destination eid)


    def tx(self, packed, drid):
        '''
        Queue duple of (packed, da) on stack transmit queue
        Where da is the ip destination (host,port) address associated with
        the estate with deid
        '''
        if drid not in self.remotes:
            msg = "Invalid destination remote id '{0}'".format(drid)
            raise raeting.StackError(msg)
        self.txes.append((packed, self.remotes[drid].ha))

    def serviceTxes(self):
        '''
        Service the .txes deque to send  messages through server
        '''
        if self.server:
            laters = deque()
            while self.txes:
                tx, ta = self.txes.popleft()  # duple = (packet, destination address)
                try:
                    self.server.send(tx, ta)
                except socket.error as ex:
                    if ex.errno == errno.EAGAIN or ex.errno == errno.EWOULDBLOCK:
                        #busy with last message save it for later
                        laters.append((tx, ta))
                    else:
                        #console.verbose("socket.error = {0}\n".format(ex))
                        raise
            while laters:
                self.txes.append(laters.popleft())

    def serviceAllRx(self):
        '''
        Service:
           UDP Socket receive
           rxes queue
           process
        '''
        self.serviceRx()
        self.serviceRxes()
        self.process()

    def serviceAllTx(self):
        '''
        Service:
           txMsgs queue
           txes queue and UDP Socket send
        '''
        self.serviceTxMsgs()
        self.serviceTxes()

    def serviceAll(self):
        '''
        Service or Process:
           UDP Socket receive
           rxes queue
           process
           txMsgs queue
           txes queue and UDP Socket send
        '''
        serviceAllRx()
        serviceAllTx()

    def serviceServer(self):
        '''
        Service the server's receive and transmit queues
        '''
        self.serviceRx()
        self.serviceTxes()


    def process(self):
        '''
        Allow timer based processing
        '''
        pass



