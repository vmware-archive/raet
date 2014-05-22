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

from .. import raeting
from .. import nacling
from .. import stacking
from . import keeping
from . import packeting
from . import estating
from . import transacting

from ioflo.base.consoling import getConsole
console = getConsole()

class RoadStack(stacking.Stack):
    '''
    RAET protocol RoadStack for UDP communications
    '''
    Count = 0
    Eid = 1 # class attribute
    Hk = raeting.headKinds.raet # stack default
    Bk = raeting.bodyKinds.json # stack default
    Fk = raeting.footKinds.nacl # stack default
    Ck = raeting.coatKinds.nacl # stack default
    Bf = False # stack default for bcstflag
    Wf = False # stack default for waitflag
    Period = 1.0 # stack default for keep alive
    Offset = 0.5 # stack default for keep alive

    def __init__(self,
                 name='',
                 main=None,
                 keep=None,
                 dirpath=None,
                 local=None,
                 eid=None, #local estate eid
                 ha=("", raeting.RAET_PORT),
                 bufcnt=2,
                 safe=None,
                 auto=None,
                 period=None,
                 offset=None,
                 **kwa
                 ):
        '''
        Setup StackUdp instance
        '''
        self.eid = self.Eid # eid of next estate to add to road

        if not name:
            name = "roadstack{0}".format(RoadStack.Count)
            RoadStack.Count += 1

        if not keep:
            keep = keeping.RoadKeep(dirpath=dirpath, stackname=name)

        if not safe:
            safe = keeping.SafeKeep(dirpath=dirpath,
                                    stackname=name,
                                    auto=auto)
        self.safe = safe

        if not local:
            self.remotes = odict()
            local = estating.LocalEstate(stack=self,
                                         name=name,
                                         eid=eid,
                                         main=main,
                                         ha=ha)
        else:
            if main is not None:
                local.main = True if main else False

        self.period = period if period is not None else self.Period
        self.offset = offset if offset is not None else self.Offset

        super(RoadStack, self).__init__(name=name,
                                        keep=keep,
                                        dirpath=dirpath,
                                        local=local,
                                        bufcnt=bufcnt,
                                        **kwa)

        self.transactions = odict() #transactions

    def nextEid(self):
        '''
        Generates next estate id number.
        '''
        self.eid += 1
        if self.eid > 0xffffffffL:
            self.eid = 1  # rollover to 1
        return self.eid

    def serverFromLocal(self):
        '''
        Create server from local data
        '''
        if not self.local:
            return None

        server = aiding.SocketUdpNb(ha=self.local.ha,
                        bufsize=raeting.UDP_MAX_PACKET_SIZE * self.bufcnt)
        return server

    def addRemote(self, remote, uid=None):
        '''
        Add a remote  to .remotes
        '''
        super(RoadStack, self).addRemote(remote, uid)
        if remote.timer.store is not self.store:
            raise raeting.StackError("Store reference mismatch between remote"
                    " '{0}' and stack '{1}'".format(remote.name, stack.name))

    def removeRemote(self, uid):
        '''
        Remove remote at key uid
        '''
        remote = self.remotes.get(uid)
        super(RoadStack, self).removeRemote(uid)
        if remote:
            for index in remote.indexes:
                if index in self.transactions:
                    self.transactions[index].nack()
                    self.removeTransaction(index)

    def fetchRemoteByHostPort(self, host, port):
        '''
        Search for remote with matching host and port
        Return remote if found Otherwise return None
        '''
        for remote in self.remotes.values():
            if remote.host == host and remote.port == port:
                return remote

        return None

    def fetchRemoteByHa(self, ha):
        '''
        Search for remote with matching host address tuple, ha = (host, port)
        Return remote if found Otherwise return None
        '''
        for remote in self.remotes.values():
            if remote.ha == ha:
                return remote

        return None

    def fetchRemoteByKeys(self, sighex, prihex):
        '''
        Search for remote with matching (name, sighex, prihex)
        Return remote if found Otherwise return None
        '''
        for remote in self.remotes.values():
            if (remote.signer.keyhex == sighex or
                remote.priver.keyhex == prihex):
                return remote

        return None

    def dumpLocal(self):
        '''
        Dump keeps of local estate
        '''
        self.keep.dumpLocal(self.local)
        self.safe.dumpLocal(self.local)

    def loadLocal(self, local=None):
        '''
        Load local estate if keeps found and verified
        otherwise use local if provided
        otherwise create default local
        '''
        keepData = self.keep.loadLocalData()
        safeData = self.safe.loadLocalData()
        if (keepData and self.keep.verifyLocalData(keepData) and
                safeData and self.safe.verifyLocalData(safeData)):
            self.local = estating.LocalEstate(stack=self,
                                          eid=keepData['uid'],
                                          name=keepData['name'],
                                          main=keepData['main'],
                                          ha=keepData['ha'],
                                          sid=keepData['sid'],
                                          sigkey=safeData['sighex'],
                                          prikey=safeData['prihex'],)
            self.safe.auto = safeData['auto']
            self.name = keepData['name']
            self.eid = keepData['neid']

        elif local:
            local.stack = self
            self.local = local

        else:
            self.local = estating.LocalEstate(stack=self)

    def clearLocal(self):
        '''
        Clear local keeps
        '''
        super(RoadStack, self).clearLocal()
        self.safe.clearLocalData()

    def dumpRemote(self, remote):
        '''
        Dump keeps of remote estate
        '''
        self.keep.dumpRemote(remote)
        self.safe.dumpRemote(remote)

    def loadRemotes(self):
        '''
        Load .remotes from valid keep and safe data if any
        '''
        keeps = self.keep.loadAllRemoteData()
        safes = self.safe.loadAllRemoteData()
        if not keeps or not safes:
            return
        for key, keepData in keeps.items():
            if key not in safes:
                continue
            safeData = safes[key]
            if (not self.keep.verifyRemoteData(keepData) or not
                    self.safe.verifyRemoteData(safeData)):
                continue
            remote = estating.RemoteEstate(stack=self,
                                           eid=keepData['uid'],
                                           name=keepData['name'],
                                           ha=keepData['ha'],
                                           sid=keepData['sid'],
                                           rsid=keepData['rsid'],
                                           acceptance=safeData['acceptance'],
                                           verkey=safeData['verhex'],
                                           pubkey=safeData['pubhex'],
                                           period=self.period,
                                           offset=self.offset)
            self.addRemote(remote)

    def clearRemote(self, remote):
        '''
        Clear remote keeps of remote estate
        '''
        super(RoadStack, self).clearRemote(remote)
        self.safe.clearRemote(remote)

    def clearRemoteKeeps(self):
        '''
        Clear all remote keeps
        '''
        super(RoadStack, self).clearRemoteKeeps()
        self.safe.clearAllRemoteData()

    def manage(self, cascade=False, immediate=False):
        '''
        Manage remote estates. Time based processing of remote status such as
        presence (keep alive) etc.

        cascade induces the alive transactions to run join, allow, alive until
        failure or alive success

        immediate indicates to run first attempt immediately and not wait for timer
        '''
        for remote in self.remotes.values(): # should not start anything
            remote.manage(cascade=cascade, immediate=immediate)

    def addTransaction(self, index, transaction):
        '''
        Safely add transaction at index If not already there
        '''
        self.transactions[index] = transaction
        re = index[2]
        remote = None
        if re in self.remotes:
            remote = self.remotes[re]
        else: # may be bootstrapping onto channel so using ha in index but 0th
            remote = self.fetchRemoteByHa(ha=re)
        if remote is not None:
            remote.indexes.add(index)

        console.verbose( "Added {0} transaction to {1} at '{2}'\n".format(
                transaction.__class__.__name__, self.name, index))

    def removeTransaction(self, index, transaction=None):
        '''
        Safely remove transaction at index If transaction identity same
        If transaction is None then remove without comparing identity
        '''
        if index in self.transactions:
            if transaction:
                if transaction is self.transactions[index]:
                    del  self.transactions[index]
            else:
                del self.transactions[index]

            re = index[2]
            remote = None
            if re in self.remotes:
                remote = self.remotes[re]
            else: # may be bootstrapping onto channel so using ha in index but 0th
                remote = self.fetchRemoteByHa(ha=re)
            if remote is not None:
                remote.indexes.discard(index)

    def serviceRxes(self):
        '''
        Process all messages in .rxes deque
        '''
        while self.rxes:
            raw, sa, da = self.rxes.popleft()
            console.verbose("{0} received packet\n{1}\n".format(self.name, raw))

            packet = packeting.RxPacket(stack=self, packed=raw)
            try:
                packet.parseOuter()
            except raeting.PacketError as ex:
                console.terse(str(ex) + '\n')
                self.incStat('parsing_outer_error')
                continue

            deid = packet.data['de']
            if deid != 0 and self.local.uid != 0 and deid != self.local.uid:
                emsg = "Invalid destination eid = {0}. Dropping packet...\n".format(deid)
                console.concise( emsg)
                self.incStat('invalid_destination')

            sh, sp = sa
            dh, dp = da
            packet.data.update(sh=sh, sp=sp, dh=dh, dp=dp)

            self.processRx(packet)

    def processRx(self, received):
        '''
        Process packet via associated transaction or
        reply with new correspondent transaction
        '''
        console.verbose("{0} received packet data\n{1}\n".format(self.name, received.data))
        console.verbose("{0} received packet index = '{1}'\n".format(self.name, received.index))

        trans = self.transactions.get(received.index, None)
        if trans:
            trans.receive(received)
            return

        if received.data['cf']: #correspondent to stale transaction
            self.stale(received)
            return

        self.reply(received)

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing  messages and start message transactions
        '''
        while self.txMsgs:
            body, deid = self.txMsgs.popleft() # duple (body dict, destination eid)
            self.message(body, deid)
            console.verbose("{0} sending\n{1}\n".format(self.name, body))

    def reply(self, packet):
        '''
        Reply to packet with corresponding transaction or action
        '''
        if (packet.data['tk'] == raeting.trnsKinds.join and
                packet.data['pk'] == raeting.pcktKinds.request and
                packet.data['si'] == 0):
            self.replyJoin(packet)
            return

        if (packet.data['tk'] == raeting.trnsKinds.allow and
                packet.data['pk'] == raeting.pcktKinds.hello and
                packet.data['si'] != 0):
            self.replyAllow(packet)
            return

        if (packet.data['tk'] == raeting.trnsKinds.message and
                packet.data['pk'] == raeting.pcktKinds.message and
                packet.data['si'] != 0):
            self.replyMessage(packet)
            return

        if (packet.data['tk'] == raeting.trnsKinds.alive and
                packet.data['pk'] == raeting.pcktKinds.request and
                packet.data['si'] != 0):
            self.replyAlive(packet)
            return

        self.incStat('stale_packet')

    def process(self):
        '''
        Call .process or all transactions to allow timer based processing
        '''
        for transaction in self.transactions.values():
            transaction.process()

    def parseInner(self, packet):
        '''
        Parse inner of packet and return
        Assume all drop checks done
        '''
        try:
            packet.parseInner()
            console.verbose("{0} received packet body\n{1}\n".format(self.name, packet.body.data))
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_inner_error')
            return None
        return packet

    def stale(self, packet):
        '''
        Initiate stale transaction in order to nack a stale correspondent packet
        '''
        data = odict(hk=self.Hk, bk=self.Bk)
        staler = transacting.Staler(stack=self,
                                    kind=packet.data['tk'],
                                    reid=packet.data['se'],
                                    sid=packet.data['si'],
                                    tid=packet.data['ti'],
                                    txData=data,
                                    rxPacket=packet)
        staler.nack()

    def join(self, deid=None, mha=None, timeout=None, cascade=False):
        '''
        Initiate join transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk)
        joiner = transacting.Joiner(stack=self,
                                    reid=deid,
                                    timeout=timeout,
                                    txData=data,
                                    mha=mha,
                                    cascade=cascade)
        joiner.join()

    def replyJoin(self, packet):
        '''
        Correspond to new join transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk)
        joinent = transacting.Joinent(stack=self,
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        joinent.join() #assigns .reid here

    def allow(self, deid=None, mha=None, timeout=None, cascade=False):
        '''
        Initiate allow transaction
        '''
        data = odict(hk=self.Hk, bk=raeting.bodyKinds.raw, fk=self.Fk)
        allower = transacting.Allower(stack=self,
                                      reid=deid,
                                      timeout=timeout,
                                      txData=data,
                                      mha=mha,
                                      cascade=cascade)
        allower.hello()

    def replyAllow(self, packet):
        '''
        Correspond to new allow transaction
        '''
        data = odict(hk=self.Hk, bk=raeting.bodyKinds.raw, fk=self.Fk)
        allowent = transacting.Allowent(stack=self,
                                        reid=packet.data['se'],
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        allowent.hello()

    def message(self, body=None, deid=None):
        '''
        Initiate message transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        messenger = transacting.Messenger(stack=self,
                                          txData=data,
                                          reid=deid,
                                          bcst=self.Bf,
                                          wait=self.Wf)
        messenger.message(body)

    def replyMessage(self, packet):
        '''
        Correspond to new Message transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        messengent = transacting.Messengent(stack=self,
                                        reid=packet.data['se'],
                                        bcst=packet.data['bf'],
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        messengent.message()

    def alive(self, deid=None,  mha=None, timeout=None, cascade=False):
        '''
        Initiate alive transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        aliver = transacting.Aliver(stack=self,
                                    timeout=timeout,
                                    reid=deid,
                                    txData=data,
                                    mha=mha,
                                    cascade=cascade)
        aliver.alive()

    def replyAlive(self, packet):
        '''
        Correspond to new Alive transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        alivent = transacting.Alivent(stack=self,
                                        reid=packet.data['se'],
                                        bcst=packet.data['bf'],
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        alivent.alive()

    def nackStale(self, packet):
        '''
        Send nack to stale correspondent packet
        '''
        body = odict()
        txData = packet.data
        ha = (packet.data['sh'], packet.data['sp'])
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.nack,
                                    embody=body,
                                    data=txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat("packing_error")
            return

        self.txes.append((packet.packed, ha))

