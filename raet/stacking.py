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
from . import keeping
from . import lotting

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
                 version=raeting.VERSION,
                 store=None,
                 keep=None,
                 dirpath='',
                 local=None,
                 bufcnt=2,
                 server=None,
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

        self.keep = keep or keeping.LotKeep(dirpath=dirpath, stackname=self.name)
        self.loadLocal(local) # load local data from saved data else passed in local
        self.remotes = odict() # remotes indexed by uid
        self.uids = odict() # remote uids indexed by name
        self.loadRemotes() # load remotes from saved data

        self.bufcnt = bufcnt
        if not server:
            server = self.serverFromLocal()

        self.server = server
        if self.server:
            if not self.server.reopen():  # open socket
                raise raeting.StackError("Stack {0}: Can't open server at"
                            " {1}\n".format(self.name, self.server.ha))
            if self.local:
                self.local.ha = self.server.ha  # update local host address after open

        self.rxMsgs = rxMsgs if rxMsgs is not None else deque() # messages received
        self.txMsgs = txMsgs if txMsgs is not None else deque() # messages to transmit
        self.rxes = rxes if rxes is not None else deque() # udp packets received
        self.txes = txes if txes is not None else deque() # udp packet to transmit
        self.stats = stats if stats is not None else odict() # udp statistics
        self.statTimer = aiding.StoreTimer(self.store)

        self.dumpLocal() # save local data
        self.dumpRemotes() # save remote data

    def serverFromLocal(self):
        '''
        Create server from local data
        '''
        return None

    def addRemote(self, remote, uid=None):
        '''
        Add a remote  to .remotes
        '''
        if uid is None:
            uid = remote.uid
        if uid and (uid in self.remotes or uid == self.local.uid):
            emsg = "Cannot add remote at uid '{0}', alreadys exists".format(uid)
            raise raeting.StackError(emsg)
        remote.stack = self
        self.remotes[uid] = remote
        if remote.name in self.uids or remote.name == self.local.name:
            emsg = "Cannot add remote with name '{0}', alreadys exists".format(remote.name)
            raise raeting.StackError(emsg)
        self.uids[remote.name] = remote.uid

    def moveRemote(self, old, new):
        '''
        Move remote at key old uid with key new uid and replace the odict key index
        so order is the same
        '''
        if new in self.remotes:
            emsg = "Cannot move, remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.remotes:
            emsg = "Cannot move remote '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        remote = self.remotes[old]
        self.clearRemote(remote)
        index = self.remotes.keys().index(old)
        remote.uid = new
        self.uids[remote.name] = new
        del self.remotes[old]
        self.remotes.insert(index, remote.uid, remote)

    def renameRemote(self, old, new):
        '''
        rename remote with old name to new name but keep same index
        '''
        if new in self.uids:
            emsg = "Cannot rename remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.uids:
            emsg = "Cannot rename remote '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        uid = self.uids[old]
        remote = self.remotes[uid]
        remote.name = new
        index = self.uids.keys().index(old)
        del self.uids[old]
        self.uids.insert(index, remote.name, remote.uid)

    def removeRemote(self, uid):
        '''
        Remove remote at key uid
        '''
        if uid not in self.remotes:
            emsg = "Cannot remove remote '{0}', does not exist".format(uid)
            raise raeting.StackError(emsg)

        remote = self.remotes[uid]
        self.clearRemote(remote)
        del self.remotes[uid]
        del self.uids[remote.name]

    def removeAllRemotes(self):
        '''
        Remove all the remotes
        '''
        uids = self.remotes.keys() #make copy since changing .remotes in-place
        for uid in uids:
            self.removeRemote(uid)

    def fetchRemoteByName(self, name):
        '''
        Search for remote with matching name
        Return remote if found Otherwise return None
        '''
        return self.remotes.get(self.uids.get(name))

    def dumpLocal(self):
        '''
        Dump keeps of local
        '''
        self.keep.dumpLocal(self.local)

    def loadLocal(self, local=None):
        '''
        Load self.local from keep file else local or new
        '''
        data = self.keep.loadLocalData()
        if data and self.keep.verifyLocalData(data):
            self.local = lotting.Lot(stack=self,
                                     uid=data['uid'],
                                     name=data['name'],
                                     ha=data['ha'])
            self.name = self.local.name

        elif local:
            local.stack = self
            self.local = local

        else:
            self.local = lotting.Lot(stack=self)

    def clearLocal(self):
        '''
        Clear local keep
        '''
        self.keep.clearLocalData()

    def dumpRemote(self, remote):
        '''
        Dump keeps of remote
        '''
        self.keep.dumpRemote(remote)

    def dumpRemotes(self):
        '''
        Dump all remotes data to keep files
        '''
        self.clearRemotes()
        datadict = odict()
        for remote in self.remotes.values():
            self.dumpRemote(remote)

    def loadRemotes(self):
        '''
        Load and add remote for each remote file
        '''
        datadict = self.keep.loadAllRemoteData()
        for data in datadict.values():
            if self.keep.verifyRemoteData(data):
                lot = lotting.Lot(stack=self,
                                  uid=data['uid'],
                                  name=data['name'],
                                  ha=data['ha'])
                self.addRemote(remote)

    def clearRemote(self, remote):
        '''
        Clear remote keep of remote
        '''
        self.keep.clearRemoteData(remote.uid)

    def clearRemotes(self):
        '''
        Clear remote keeps of .remotes
        '''
        for remote in self.remotes.values():
            self.clearRemote(remote)

    def clearRemoteKeeps(self):
        '''
        Clear all remote keeps
        '''
        self.keep.clearAllRemoteData()

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

    def clearStat(self, key):
        '''
        Set the specified state counter to zero
        '''
        if key in self.stats:
            self.stats[key] = 0

    def clearStats(self):
        '''
        Set all the stat counters to zero and reset the timer
        '''
        for key, value in self.stats.items():
            self.stats[key] = 0
        self.statTimer.restart()

    def serviceReceives(self):
        '''
        Retrieve from server all recieved and put on the rxes deque
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
            raw, sa, da = self.rxes.popleft()
            console.verbose("{0} received raw message\n{1}\n".format(self.name, raw))
            processRx(received=raw)

    def processRx(self, received):
        '''
        Process
        '''
        pass

    def transmit(self, msg, duid=None):
        '''
        Append duple (msg, duid) to .txMsgs deque
        If msg is not mapping then raises exception
        If deid is None then it will default to the first entry in .estates
        '''
        if not isinstance(msg, Mapping):
            emsg = "Invalid msg, not a mapping {0}\n".format(msg)
            console.terse(emsg)
            self.incStat("invalid_transmit_body")
            return
        if duid is None:
            if not self.remotes:
                emsg = "No remote to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination")
                return
            duid = self.remotes.values()[0].uid
        self.txMsgs.append((msg, duid))

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing  messages
        '''
        while self.txMsgs:
            body, drid = self.txMsgs.popleft() # duple (body dict, destination eid)

            #need to pack body here and tx

    def tx(self, packed, duid):
        '''
        Queue duple of (packed, da) on stack .txes queue
        Where da is the ip destination (host,port) address associated with
        the remote identified by duid
        '''
        if duid not in self.remotes:
            msg = "Invalid destination remote id '{0}'".format(duid)
            raise raeting.StackError(msg)
        self.txes.append((packed, self.remotes[duid].ha))

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
           server receive
           rxes queue
           process
        '''
        self.serviceReceives()
        self.serviceRxes()
        self.process()

    def serviceAllTx(self):
        '''
        Service:
           txMsgs queue
           txes queue to server send
        '''
        self.serviceTxMsgs()
        self.serviceTxes()

    def serviceAll(self):
        '''
        Service or Process:
           server receive
           rxes queue
           process
           txMsgs queue
           txes queue to server send
        '''
        self.serviceAllRx()
        self.serviceAllTx()

    def serviceServer(self):
        '''
        Service the server's receive and transmit queues
        '''
        self.serviceReceives()
        self.serviceTxes()

    def process(self):
        '''
        Allow timer based processing
        '''
        pass



