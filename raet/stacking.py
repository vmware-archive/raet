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
                 main=None,
                 version=raeting.VERSION,
                 store=None,
                 keep=None,
                 dirpath='',
                 basedirpath='',
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
        Setup Stack instance
        '''
        if not name:
            name = "{0}{1}".format(self.__class__.__name__.lower(), Stack.Count)
            Stack.Count += 1

        self.version = version
        self.store = store or storing.Store(stamp=0.0)
        self.local = local or lotting.LocalLot(stack=self,
                                               name=name,
                                               main=main,)
        self.local.stack = self
        if self.local.main is None and main is not None:
            self.local.main = True if main else False

        self.remotes = odict() # remotes indexed by uid
        self.uids = odict() # remote uids indexed by name

        self.bufcnt = bufcnt
        if not server:
            server = self.serverFromLocal()

        self.server = server
        if self.server:
            if not self.server.reopen():  # open socket
                raise raeting.StackError("Stack '{0}': Failed opening server at"
                            " '{1}'\n".format(self.name, self.server.ha))
            if self.local:
                self.local.ha = self.server.ha  # update local host address after open

            console.verbose("Stack '{0}': Opened server at '{1}'\n".format(self.name, self.local.ha))

        self.rxMsgs = rxMsgs if rxMsgs is not None else deque() # messages received
        self.txMsgs = txMsgs if txMsgs is not None else deque() # messages to transmit
        self.rxes = rxes if rxes is not None else deque() # udp packets received
        self.txes = txes if txes is not None else deque() # udp packet to transmit
        self.stats = stats if stats is not None else odict() # udp statistics
        self.statTimer = aiding.StoreTimer(self.store)

    @property
    def name(self):
        '''
        property that returns name of local interface
        '''
        return self.local.name

    @name.setter
    def name(self, value):
        '''
        setter for name property
        '''
        self.local.name = value

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
        # allow for condition where local.uid == 0 and remote.uid == 0
        if uid in self.remotes or (uid and uid == self.local.uid):
            emsg = "Cannot add remote at uid '{0}', alreadys exists".format(uid)
            raise raeting.StackError(emsg)
        remote.stack = self
        self.remotes[uid] = remote
        if remote.name in self.uids or remote.name == self.local.name:
            emsg = "Cannot add remote with name '{0}', alreadys exists".format(remote.name)
            raise raeting.StackError(emsg)
        self.uids[remote.name] = remote.uid

    def moveRemote(self, remote, new):
        '''
        Move remote at key remote.uid to new uid and replace the odict key index
        so order is the same
        '''
        old = remote.uid

        if new in self.remotes or new == self.local.uid:
            emsg = "Cannot move, remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.remotes:
            emsg = "Cannot move remote at '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        if remote is not self.remotes[old]:
            emsg = "Cannot move remote at '{0}', not identical".format(old)
            raise raeting.StackError(emsg)

        #remote = self.remotes[old]
        index = self.remotes.keys().index(old)
        remote.uid = new
        self.uids[remote.name] = new
        del self.remotes[old]
        self.remotes.insert(index, remote.uid, remote)

    def renameRemote(self, remote, new):
        '''
        rename remote with old remote.name to new name but keep same index
        '''
        old = remote.name
        if new != old:
            if new in self.uids or new == self.local.name:
                emsg = "Cannot rename remote to '{0}', already exists".format(new)
                raise raeting.StackError(emsg)

            if old not in self.uids:
                emsg = "Cannot rename remote '{0}', does not exist".format(old)
                raise raeting.StackError(emsg)

            if remote is not self.remotes[self.uids[old]]:
                emsg = "Cannot rename remote '{0}', not identical".format(old)
                raise raeting.StackError(emsg)

            #remote = self.remotes[self.uids[old]]
            remote.name = new
            index = self.uids.keys().index(old)
            del self.uids[old]
            self.uids.insert(index, remote.name, remote.uid)

    def removeRemote(self, remote):
        '''
        Remove remote at key remote.uid
        '''
        uid = remote.uid
        if uid not in self.remotes:
            emsg = "Cannot remove remote '{0}', does not exist".format(uid)
            raise raeting.StackError(emsg)

        if remote is not self.remotes[uid]:
            emsg = "Cannot remove remote '{0}', not identical".format(uid)
            raise raeting.StackError(emsg)

        #remote = self.remotes[uid]
        del self.remotes[uid]
        del self.uids[remote.name]

    def removeAllRemotes(self):
        '''
        Remove all the remotes
        '''
        remotes = self.remotes.values() #make copy since changing .remotes in-place
        for remote in remotes:
            self.removeRemote(remote)

    def fetchRemoteByName(self, name):
        '''
        Search for remote with matching name
        Return remote if found Otherwise return None
        '''
        return self.remotes.get(self.uids.get(name))

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

    def _handleOneReceived(self):
        '''
        Handle one received message from server
        assumes that there is a server
        '''
        rx, ra = self.server.receive()  # if no data the duple is ('',None)
        if not rx:  # no received data
            return False
        # triple = ( packet, source address, destination address)
        self.rxes.append((rx, ra, self.server.ha))
        return True

    def serviceReceives(self):
        '''
        Retrieve from server all recieved and put on the rxes deque
        '''
        if self.server:
            while self._handleOneReceived():
                pass

    def serviceReceiveOnce(self):
        '''
        Retrieve from server one recieved and put on the rxes deque
        '''
        if self.server:
            self._handleOneReceived()

    def _handleOneRx(self):
        '''
        Handle on message from .rxes deque
        Assumes that there is a message on the .rxes deque
        '''
        raw, sa, da = self.rxes.popleft()
        console.verbose("{0} received raw message\n{1}\n".format(self.name, raw))
        processRx(received=raw)

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
            self.handleOnceRx()

    def processRx(self, received):
        '''
        Process
        '''
        pass

    def transmit(self, msg, duid=None):
        '''
        Append duple (msg, duid) to .txMsgs deque
        If msg is not mapping then raises exception
        If duid is None then it will default to the first entry in .remotes
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

    def  _handleOneTxMsg(self):
        '''
        Take one message from .txMsgs deque and handle it
        Assumes there is a message on the deque
        '''
        body, duid = self.txMsgs.popleft() # duple (body dict, destination uid
        self.message(body, duid)
        console.verbose("{0} sending\n{1}\n".format(self.name, body))

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing  messages
        '''
        while self.txMsgs:
            self._handleOneTxMsg()

    def serviceTxMsgOnce(self):
        '''
        Service one message on .txMsgs queue of outgoing messages
        '''
        if self.txMsgs:
            self._handleOneTxMsg()

    def message(self, body, duid):
        '''
        Sends message body remote at duid
        '''
        pass

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


    def _handleOneTx(self, laters, blocks):
        '''
        Handle one message on .txes deque
        Assumes there is a message
        laters is deque of messages to try again later
        blocks is list of destinations that already blocked on this service
        '''
        tx, ta = self.txes.popleft()  # duple = (packet, destination address)

        if ta in blocks: # already blocked on this iteration
            laters.append((tx, ta)) # keep sequential
            return

        try:
            self.server.send(tx, ta)
        except socket.error as ex:
            if ex.errno == errno.EAGAIN or ex.errno == errno.EWOULDBLOCK:
                #busy with last message save it for later
                laters.append((tx, ta))
                blocks.append(ta)
            else:
                raise

    def serviceTxes(self):
        '''
        Service the .txes deque to send  messages through server
        '''
        if self.server:
            laters = deque()
            blocks = []
            while self.txes:
                self._handleOneTx(laters, blocks)
            while laters:
                self.txes.append(laters.popleft())

    def serviceTxOnce(self):
        '''
        Service on message on the .txes deque to send through server
        '''
        if self.server:
            laters = deque()
            blocks = [] # will always be empty since only once
            if self.txes:
                self._handleOneTx(laters, blocks)
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

    def serviceOneAllRx(self):
        '''
        Propagate one packet all the way through the received side of the stack
        Service:
           server receive
           rxes queue
           process
        '''
        self.serviceReceiveOnce()
        self.serviceRxOnce()
        self.process()

    def serviceOneAllTx(self):
        '''
        Propagate one packet all the way through the transmit side of the stack
        Service:
           txMsgs queue
           txes queue to server send
        '''
        self.serviceTxMsgOnce()
        self.serviceTxOnce()

    def process(self):
        '''
        Allow timer based processing
        '''
        pass

class KeepStack(Stack):
    '''
    RAET protocol base stack object with persistance via Keep attribute.
    Should be subclassed for specific transport type
    '''
    def __init__(self,
                 name='',
                 main=None,
                 keep=None,
                 dirpath='',
                 basedirpath='',
                 local=None,
                 clean=False,
                 **kwa
                 ):
        '''
        Setup Stack instance
        '''
        self.keep = keep or keeping.LotKeep(dirpath=dirpath,
                                            basedirpath=basedirpath,
                                            stackname=name)

        if clean: # clear persisted data so use provided or default data
            self.clearLocalKeep()

        local = self.restoreLocal() or local or lotting.LocalLot(stack=self,
                                                                 main=main,
                                                                 name=name)
        local.stack = self
        if local.main is None and main is not None:
            local.main = True if main else False

        super(KeepStack, self).__init__(name=name,
                                        main=main,
                                        dirpath=dirpath,
                                        basedirpath=basedirpath,
                                        local=local,
                                        **kwa)


        if clean:
            self.clearRemoteKeeps()
        self.restoreRemotes() # load remotes from saved data

        for remote in self.remotes.values():
            remote.nextSid()

        self.dumpLocal() # save local data
        self.dumpRemotes() # save remote data

    def addRemote(self, remote, uid=None, dump=False):
        '''
        Add a remote  to .remotes
        '''
        super(KeepStack, self).addRemote(remote=remote, uid=uid)
        if dump:
            self.dumpRemote(remote)

    def moveRemote(self, remote, new, clear=True, dump=False):
        '''
        Move remote with key remote.uid old to key new uid and replace the odict key index
        so order is the same.
        If clear then clear the keep file for remote at old
        If dump then dump the keep file for the remote at new
        '''
        old = remote.uid
        super(KeepStack, self).moveRemote(remote, new=new)
        if clear:
            self.keep.clearRemoteData(old)
        if dump:
            self.dumpRemote(remote=remote)

    def renameRemote(self, remote, new, dump=False):
        '''
        Rename remote with old remote.name to new name but keep same index
        '''
        super(KeepStack, self).renameRemote(remote=remote, new=new)
        if dump:
            self.dumpRemote(remote=remote)

    def removeRemote(self, remote, clear=True):
        '''
        Remove remote at key uid
        If clear then also remove from disk
        '''
        super(KeepStack, self).removeRemote(remote=remote)
        if clear:
            self.keep.clearRemoteData(remote.uid)

    def removeAllRemotes(self, clear=True):
        '''
        Remove all the remotes
        If clear then also remove from disk
        '''
        remotes = self.remotes.values() #make copy since changing .remotes in-place
        for remote in remotes:
            self.removeRemote(remote, clear=clear)

    def clearAllDir(self):
        '''
        Clear out and remove the keep dir and contents
        '''
        console.verbose("Stack {0}: Clearing keep dir '{1}'\n".format(
                                  self.name, self.keep.dirpath))
        self.keep.clearAllDir()

    def dumpLocal(self):
        '''
        Dump keeps of local
        '''
        self.keep.dumpLocal(self.local)

    def restoreLocal(self):
        '''
        Load self.local from keep file if any and return local
        Otherwise return None
        '''
        local = None
        data = self.keep.loadLocalData()
        if data and self.keep.verifyLocalData(data):
            local = lotting.LocalLot(stack=self,
                                     uid=data['uid'],
                                     name=data['name'],
                                     ha=data['ha'],
                                     sid = data['sid'])
            self.local = local
        return local

    def clearLocalKeep(self):
        '''
        Clear local keep
        '''
        self.keep.clearLocalData()

    def dumpRemote(self, remote):
        '''
        Dump keeps of remote
        '''
        self.keep.dumpRemote(remote)

    def dumpRemotes(self, clear=True):
        '''
        Dump all remotes data to keep files
        If clear then clear all files first
        '''
        if clear:
            self.clearRemotes()
        for remote in self.remotes.values():
            self.dumpRemote(remote)

    def restoreRemote(self, uid):
        '''
        Load, add, and return remote with uid if any
        Otherwise return None
        '''
        remote = None
        data = self.keep.loadRemoteData(uid)
        if data and self.keep.verifyRemoteData(data):
            remote = lotting.Lot(stack=self,
                              uid=data['uid'],
                              name=data['name'],
                              ha=data['ha'],
                              sid=data['sid'])
            self.addRemote(remote)
        return remote

    def restoreRemotes(self):
        '''
        Load and add remote for each remote file
        '''
        datadict = self.keep.loadAllRemoteData()
        for data in datadict.values():
            if self.keep.verifyRemoteData(data):
                remote = lotting.Lot(stack=self,
                                  uid=data['uid'],
                                  name=data['name'],
                                  ha=data['ha'],
                                  sid=data['sid'])
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

