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
    Hk = raeting.headKinds.raet # stack default
    Bk = raeting.bodyKinds.json # stack default
    Fk = raeting.footKinds.nacl # stack default
    Ck = raeting.coatKinds.nacl # stack default
    Bf = False # stack default for bcstflag
    Wf = False # stack default for waitflag

    def __init__(self,
                 name='',
                 main=False,
                 keep=None,
                 dirpath=None,
                 local=None,
                 eid=None,
                 ha=("", raeting.RAET_PORT),
                 bufcnt=2,
                 safe=None,
                 auto=None,
                 **kwa
                 ):
        '''
        Setup StackUdp instance
        '''
        if not name:
            name = "roadstack{0}".format(RoadStack.Count)
            RoadStack.Count += 1

        if not keep:
            keep = keeping.RoadKeep(dirpath=dirpath, stackname=name)

        self.safe = safe or keeping.SafeKeep(dirpath=dirpath,
                                            stackname=name,
                                            auto=auto)

        if not local:
            local = estating.LocalEstate(stack=self, eid=eid, main=main, ha=ha)

        server = aiding.SocketUdpNb(ha=local.ha,
                                    bufsize=raeting.UDP_MAX_PACKET_SIZE * bufcnt)

        super(RoadStack, self).__init__(name=name,
                                        keep=keep,
                                        dirpath=dirpath,
                                        local=local,
                                        server=server,
                                        **kwa)

        self.uids = odict() # remote ids indexed by name
        self.transactions = odict() #transactions

        self.dumpLocal() # save local data
        self.dumpRemotes() # save remote data

    def addRemote(self, remote, uid=None):
        '''
        Add a remote  to .remotes
        '''
        if uid is None:
            uid = remote.uid
        if uid in self.remotes:
            emsg = "Cannot add remote at uid '{0}', alreadys exists".format(uid)
            raise raeting.StackError(emsg)
        remote.stack = self
        self.remotes[uid] = remote
        if remote.name in self.uids:
            emsg = "Cannot add remote with name '{0}', alreadys exists".format(remote.name)
            raise raeting.StackError(emsg)
        self.uids[remote.name] = remote.uid

    def moveRemote(self, old, new):
        '''
        Move remote at key old uid to key new uid but keep same index
        '''
        if new in self.remotes:
            emsg = "Cannot move, remote to '{0}', already exists".format(new)
            raise raeting.StackError(emsg)

        if old not in self.remotes:
            emsg = "Cannot move remote '{0}', does not exist".format(old)
            raise raeting.StackError(emsg)

        remote = self.remotes[old]
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
        del self.remotes[uid]
        del self.uids[remote.name]

    def fetchRemoteByName(self, name):
        '''
        Search for remote with matching name
        Return remote if found Otherwise return None
        '''
        return self.remotes.get(self.uids.get(name))

    def fetchRemoteByHostPort(self, host, port):
        '''
        Search for remote estate with matching (host, port)
        Return estate if found Otherwise return None
        '''
        for estate in self.remotes.values():
            if estate.host == host and estate.port == port:
                return estate

        return None

    def fetchRemoteByKeys(self, sighex, prihex):
        '''
        Search for remote estate with matching (name, sighex, prihex)
        Return estate if found Otherwise return None
        '''
        for estate in self.remotes.values():
            if (estate.signer.keyhex == sighex or
                estate.priver.keyhex == prihex):
                return estate

        return None

    def clearLocal(self):
        '''
        Clear local keeps
        '''
        super(RoadStack, self).clearLocal()
        self.safe.clearLocalData()

    def clearRemote(self, remote):
        '''
        Clear remote keeps of remote estate
        '''
        super(RoadStack, self).clearRemote(remote)
        self.safe.clearRemoteData(remote)

    def clearRemoteKeeps(self):
        '''
        Clear all remote keeps
        '''
        self.keep.clearAllRemoteData()
        self.safe.clearAllRemoteData()

    def dumpLocal(self):
        '''
        Dump keeps of local estate
        '''
        data = odict([
                        ('eid', self.local.eid),
                        ('name', self.local.name),
                        ('main', self.local.main),
                        ('host', self.local.host),
                        ('port', self.local.port),
                        ('sid', self.local.sid)
                    ])
        if self.keep.verify(data):
            self.keep.dumpLocalData(data)

        data = odict([
                        ('eid', self.local.eid),
                        ('name', self.local.name),
                        ('sighex', self.local.signer.keyhex),
                        ('prihex', self.local.priver.keyhex),
                    ])
        if self.safe.verify(data):
            self.safe.dumpLocalData(data)

    def loadLocal(self):
        '''
        Load and Return local estate if keeps found
        '''
        road = self.road.loadLocalData()
        safe = self.safe.loadLocalData()
        if (not road or not self.road.verify(road) or
                not safe or not self.safe.verify(safe)):
            return None
        estate = estating.LocalEstate(stack=self,
                                      eid=road['eid'],
                                      name=road['name'],
                                      main=road['main'],
                                      host=road['host'],
                                      port=road['port'],
                                      sid=road['sid'],
                                      sigkey=safe['sighex'],
                                      prikey=safe['prihex'],)
        return estate

    def dumpRemote(self, remote):
        '''
        Dump keeps of estate
        '''
        data = odict([
                        ('uid', remote.eid),
                        ('name', remote.name),
                        ('host', remote.host),
                        ('port', remote.port),
                        ('sid', remote.sid),
                        ('rsid', estate.rsid),
                    ])
        if self.keep.verify(data):
            self.keep.dumpRemoteData(data, remote.uid)

        data = odict([
                ('eid', remote.eid),
                ('name', remote.name),
                ('acceptance', remote.acceptance),
                ('verhex', remote.verfer.keyhex),
                ('pubhex', remote.pubber.keyhex),
                ])

        if self.safe.verify(data):
            self.safe.dumpRemoteData(data, remote.uid)

    def loadRemotes(self):
        '''
        Load and Return list of remote estates
        remote = estating.RemoteEstate( stack=self.stack,
                                        name=name,
                                        host=data['sh'],
                                        port=data['sp'],
                                        acceptance=acceptance,
                                        verkey=verhex,
                                        pubkey=pubhex,
                                        rsid=self.sid,
                                        rtid=self.tid, )
        self.stack.addRemoteEstate(remote)
        '''
        estates = []
        roads = self.road.loadAllRemoteData()
        safes = self.safe.loadAllRemoteData()
        if not roads or not safes:
            return []
        for key, road in roads.items():
            if key not in safes:
                continue
            safe = safes[key]
            if not self.road.verify(road) or not self.safe.verify(safe):
                continue
            estate = estating.RemoteEstate( stack=self,
                                            eid=road['eid'],
                                            name=road['name'],
                                            host=road['host'],
                                            port=road['port'],
                                            sid=road['sid'],
                                            rsid=road['rsid'],
                                            acceptance=safe['acceptance'],
                                            verkey=safe['verhex'],
                                            pubkey=safe['pubhex'],)
            estates.append(estate)
        return estates

    def addTransaction(self, index, transaction):
        '''
        Safely add transaction at index If not already there
        '''
        self.transactions[index] = transaction
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

    def serviceUdpRx(self):
        '''
        Service the UDP receive and fill the rxes deque
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
            self.processUdpRx()

    def serviceTxMsgs(self):
        '''
        Service .txMsgs queue of outgoing  messages and start message transactions
        '''
        while self.txMsgs:
            body, deid = self.txMsgs.popleft() # duple (body dict, destination eid)
            self.message(body, deid)
            console.verbose("{0} sending\n{1}\n".format(self.name, body))

    def serviceTxes(self):
        '''
        Service the .txes deque to send Udp messages
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

    def serviceUdp(self):
        '''
        Service the UDP receive and transmit queues
        '''
        self.serviceUdpRx()
        self.serviceTxes()

    def serviceRx(self):
        '''
        Service:
           UDP Socket receive
           rxes queue
           process
        '''
        self.serviceUdpRx()
        self.serviceRxes()
        self.process()

    def serviceTx(self):
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
        self.serviceUdpRx()
        self.serviceRxes()
        self.process()

        self.serviceTxMsgs()
        self.serviceTxes()

    def transmit(self, msg, deid=None):
        '''
        Append duple (msg,deid) to .txMsgs deque
        If msg is not mapping then raises exception
        If deid is None then it will default to the first entry in .estates
        '''
        if not isinstance(msg, Mapping):
            emsg = "Invalid msg, not a mapping {0}\n".format(msg)
            console.terse(emsg)
            self.incStat("invalid_transmit_body")
            return
        self.txMsgs.append((msg, deid))

    txMsg = transmit

    def txUdp(self, packed, deid):
        '''
        Queue duple of (packed, da) on stack transmit queue
        Where da is the ip destination (host,port) address associated with
        the estate with deid
        '''
        if deid not in self.remotes:
            msg = "Invalid destination estate id '{0}'".format(deid)
            raise raeting.StackError(msg)
        self.txes.append((packed, self.remotes[deid].ha))

    def processUdpRx(self):
        '''
        Retrieve next packet from stack receive queue if any and parse
        Process associated transaction or reply with new correspondent transaction
        '''
        packet = self.fetchParseUdpRx()
        if not packet:
            return

        console.verbose("{0} received packet data\n{1}\n".format(self.name, packet.data))
        console.verbose("{0} received packet index = '{1}'\n".format(self.name, packet.index))

        trans = self.transactions.get(packet.index, None)
        if trans:
            trans.receive(packet)
            return

        if packet.data['cf']: #correspondent to stale transaction
            self.stale(packet)
            return

        self.reply(packet)

    def fetchParseUdpRx(self):
        '''
        Fetch from UDP deque next packet tuple
        Parse packet
        Return packet if verified and destination eid matches
        Otherwise return None
        '''
        try:
            raw, sa, da = self.rxes.popleft()
        except IndexError:
            return None

        console.verbose("{0} received packet\n{1}\n".format(self.name, raw))

        packet = packeting.RxPacket(stack=self, packed=raw)
        try:
            packet.parseOuter()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_outer_error')
            return None

        deid = packet.data['de']
        if deid != 0 and self.local.uid != 0 and deid != self.local.uid:
            emsg = "Invalid destination eid = {0}. Dropping packet...\n".format(deid)
            console.concise( emsg)
            return None

        sh, sp = sa
        dh, dp = da
        packet.data.update(sh=sh, sp=sp, dh=dh, dp=dp)

        return packet # outer only has been parsed

    def reply(self, packet):
        '''
        Reply to packet with corresponding transaction or action
        '''
        if (packet.data['tk'] == raeting.trnsKinds.join and
                packet.data['pk'] == raeting.pcktKinds.request and
                packet.data['si'] == 0):
            self.replyJoin(packet)

        if (packet.data['tk'] == raeting.trnsKinds.allow and
                packet.data['pk'] == raeting.pcktKinds.hello and
                packet.data['si'] != 0):
            self.replyAllow(packet)

        if (packet.data['tk'] == raeting.trnsKinds.message and
                packet.data['pk'] == raeting.pcktKinds.message and
                packet.data['si'] != 0):
            self.replyMessage(packet)

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

    def join(self, mha=None):
        '''
        Initiate join transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk)
        joiner = transacting.Joiner(stack=self, txData=data, mha=mha)
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

    def allow(self, reid=None):
        '''
        Initiate allow transaction
        '''
        data = odict(hk=self.Hk, bk=raeting.bodyKinds.raw, fk=self.Fk)
        allower = transacting.Allower(stack=self, reid=reid, txData=data)
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
                                        wait=packet.data['wf'],
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        messengent.message()

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

