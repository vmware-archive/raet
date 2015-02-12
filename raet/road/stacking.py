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

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import PcktKind, TrnsKind, CoatKind, FootKind, BodyKind, HeadKind
from .. import nacling
from .. import stacking
from . import keeping
from . import packeting
from . import estating
from . import transacting

from ioflo.base.consoling import getConsole
console = getConsole()

class RoadStack(stacking.KeepStack):
    '''
    RAET protocol RoadStack for UDP communications. This is the primary
    network communication system in RAET. A stack does not work in the
    same way as a socket, instead transmit (tx) and recive (rx) lists become
    populated or emptied when calls are made to the transmit and recieve
    methods.

    name
        The name to give the stack and local estate, if no name is given it will be
        automatically assigned
    main
        Flag indicating if the local estate is a main estate on the road
    mutable
        Flag indicating if credentials on road can be changed after initial join
    keep
        Pass in a keep object, this object can define how stack data
        including keys is persisted to disk
    dirpath
        The location on the filesystem to use for stack caching
    uid
        The local estate id, if None is specified a default will be assigned
    ha
        The local estate host address, this is a tuple of (network_addr, port) that will
        be bound to by the stack
    bufcnt
        The number of messages to buffer, defaults to 2
    auto
        auto acceptance mode indicating how keys should be accepted
        one of never, once, always
    period
        The default iteration timeframe to use for the background management
        of the presence system. Defaults to 1.0
    offset
        The default offset to the start of period
    interim
        The default timeout to reap a dead remote
    role
        The local estate role identifier for key management
    '''
    Count = 0 # count of Stack instances to give unique stack names
    Hk = HeadKind.raet.value # stack default
    Bk = BodyKind.json.value # stack default
    Fk = FootKind.nacl.value # stack default
    Ck = CoatKind.nacl.value # stack default
    Bf = False # stack default for bcstflag
    BurstSize = 0  # stack default for max segments in each burst, 0 = no limit
    Period = 1.0 # stack default for keep alive
    Offset = 0.5 # stack default for keep alive
    Interim = 3600 # stack default for reap timeout
    JoinerTimeout = 5.0 # stack default for joiner transaction timeout
    JoinentTimeout = 5.0 # stack default for joinent transaction timeout

    def __init__(self,
                 puid=None,
                 keep=None,
                 dirpath='',
                 basedirpath='',
                 auto=None,
                 local=None, #passed up from subclass
                 name='',
                 uid=None, #local estate uid, none means generate it
                 ha=None,
                 eha=None,
                 iha=None,
                 role=None,
                 sigkey=None,
                 prikey=None,
                 bufcnt=2,
                 kind=None,
                 mutable=None,
                 period=None,
                 offset=None,
                 interim=None,
                 **kwa
                 ):
        '''
        Setup instance

        '''
        if getattr(self, 'puid', None) is None:
            self.puid = puid if puid is not None else self.Uid

        keep = keep or keeping.RoadKeep(dirpath=dirpath,
                                        basedirpath=basedirpath,
                                        stackname=name,
                                        auto=auto)

        ha = ha if ha is not None else ("", raeting.RAET_PORT)

        local = local or estating.LocalEstate(stack=self,
                                     name=name,
                                     uid=uid,
                                     ha=eha or ha,
                                     iha=iha,
                                     role=role,
                                     sigkey=sigkey,
                                     prikey=prikey, )
        local.stack = self

        self.aha = ha # init before server is initialized

        # Remotes reference these in there init so create before super
        self.period = period if period is not None else self.Period
        self.offset = offset if offset is not None else self.Offset
        self.interim = interim if interim is not None else self.Interim

        super(RoadStack, self).__init__(puid=puid,
                                        keep=keep,
                                        dirpath=dirpath,
                                        basedirpath=basedirpath,
                                        local=local,
                                        bufcnt=bufcnt,
                                        **kwa)
        self.kind = kind # application kind associated with the local estate
        self.mutable = mutable # road data mutability
        self.joinees = odict() # remotes for vacuous joins, keyed by ha
        self.alloweds = odict() # allowed remotes keyed by name
        self.aliveds =  odict() # alived remotes keyed by name
        self.reapeds =  odict() # reaped remotes keyed by name
        self.availables = set() # set of available remote names

    @property
    def ha(self):
        '''
        property that returns host address
        '''
        return self.aha

    @ha.setter
    def ha(self, value):
        self.aha = value

    @property
    def transactions(self):
        '''
        property that returns list of transactions in all remotes
        '''
        transactions = []
        for remote in self.remotes.values():
            transactions.extend(remote.transactions.values())
        return transactions

    def serverFromLocal(self):
        '''
        Create local listening server for stack
        '''
        server = aiding.SocketUdpNb(ha=self.ha,
                        bufsize=raeting.UDP_MAX_PACKET_SIZE * self.bufcnt)
        return server

    def addRemote(self, remote, dump=False):
        '''
        Add a remote  to .remotes
        '''
        super(RoadStack, self).addRemote(remote=remote, dump=dump)
        if remote.timer.store is not self.store:
            raise raeting.StackError("Store reference mismatch between remote"
                    " '{0}' and stack '{1}'".format(remote.name, stack.name))
        return remote

    def removeRemote(self, remote, clear=True):
        '''
        Remove remote at key uid.
        If clear then also remove from disk
        '''
        super(RoadStack, self).removeRemote(remote=remote, clear=clear)
        for transaction in remote.transactions.values():
            transaction.nack()

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

    def retrieveRemote(self, uid=None):
        '''
        Used when initiating a transaction

        If uid is not None Then returns remote at duid if exists or None
        If uid is None Then uses first remote unless no remotes then None
        '''
        if uid is not None:
            remote = self.remotes.get(uid, None)
        else:
            if self.remotes:
                remote = self.remotes.values()[0] # zeroth is default
            else:
                remote = None
        return remote

    def createRemote(self, ha):
        '''
        Use for vacuous join to create new remote
        '''
        if not ha:
            console.terse("Invalid host address = {0} when creating remote.".format(ha))
            self.incStat("failed_createremote")
            return None

        remote = estating.RemoteEstate(stack=self,
                                       fuid=0, # vacuous join
                                       sid=0, # always 0 for join
                                       ha=ha) #if ha is not None else dha

        try:
            self.addRemote(remote) #provisionally add .accepted is None
        except raeting.StackError as ex:
            console.terse(str(ex) + '\n')
            self.incStat("failed_addremote")
            return None

        return remote

    def dumpLocalRole(self):
        '''
        Dump role keep of local
        '''
        self.keep.dumpLocalRole(self.local)

    def restoreLocal(self):
        '''
        Load local estate if keeps found and verified and return
        otherwise return None
        '''
        local = None
        keepData = self.keep.loadLocalData()
        if keepData:
            if self.keep.verifyLocalData(keepData):
                ha = keepData['ha']
                iha = keepData['iha']
                aha = keepData['aha']
                local = estating.LocalEstate(stack=self,
                                              uid=keepData['uid'],
                                              name=keepData['name'],
                                              ha=tuple(ha) if ha else ha,
                                              iha=tuple(iha) if iha else iha,
                                              natted=keepData['natted'],
                                              fqdn=keepData['fqdn'],
                                              dyned=keepData['dyned'],
                                              sid=keepData['sid'],
                                              role=keepData['role'],
                                              sigkey=keepData['sighex'],
                                              prikey=keepData['prihex'],)
                self.puid = keepData['puid']
                self.aha = tuple(aha) if aha else aha
                self.local = local
            else:
                self.keep.clearLocalData()
        return local

    def clearLocalRoleKeep(self):
        '''
        Clear local keep
        '''
        self.keep.clearLocalRoleData()

    def dumpRemoteRole(self, remote):
        '''
        Dump keeps of remote
        '''
        self.keep.dumpRemoteRole(remote)

    def restoreRemote(self, name):
        '''
        Load, add, and return remote with name if any
        Otherwise return None
        '''
        remote = None
        keepData = self.keep.loadRemoteData(name)
        if keepData:
            if self.keep.verifyRemoteData(keepData):
                ha = keepData['ha']
                iha = keepData['iha']
                remote = estating.RemoteEstate(stack=self,
                                               uid=keepData['uid'],
                                               fuid=keepData['fuid'],
                                               name=keepData['name'],
                                               ha=tuple(ha) if ha else ha,
                                               iha=tuple(iha) if iha else iha,
                                               natted=keepData['natted'],
                                               fqdn=keepData['fqdn'],
                                               dyned=keepData['dyned'],
                                               sid=keepData['sid'],
                                               main=keepData['main'],
                                               kind=keepData['kind'],
                                               joined=keepData['joined'],
                                               acceptance=keepData['acceptance'],
                                               verkey=keepData['verhex'],
                                               pubkey=keepData['pubhex'],
                                               role=keepData['role'])
                self.addRemote(remote)
            else:
                self.keep.clearRemoteData(name)
        return remote

    def restoreRemotes(self):
        '''
        Load .remotes from valid keep  data if any
        '''
        keeps = self.keep.loadAllRemoteData()
        if keeps:
            for name, keepData in keeps.items():
                if self.keep.verifyRemoteData(keepData):
                    ha = keepData['ha']
                    iha = keepData['iha']
                    remote = estating.RemoteEstate(stack=self,
                                                   uid=keepData['uid'],
                                                   fuid=keepData['fuid'],
                                                   name=keepData['name'],
                                                   ha=tuple(ha) if ha else ha,
                                                   iha=tuple(iha) if iha else iha,
                                                   natted=keepData['natted'],
                                                   fqdn=keepData['fqdn'],
                                                   dyned=keepData['dyned'],
                                                   sid=keepData['sid'],
                                                   main=keepData['main'],
                                                   kind=keepData['kind'],
                                                   joined=keepData['joined'],
                                                   acceptance=keepData['acceptance'],
                                                   verkey=keepData['verhex'],
                                                   pubkey=keepData['pubhex'],
                                                   role=keepData['role'])
                    self.addRemote(remote)
                else:
                    self.keep.clearRemoteData(name)

    def clearRemoteRoleKeeps(self):
        '''
        Clear all remote keeps
        '''
        self.keep.clearAllRemoteRoleData()

    def clearAllKeeps(self):
        super(RoadStack, self).clearAllKeeps()
        self.clearLocalRoleKeep()
        self.clearRemoteRoleKeeps()

    def manage(self, cascade=False, immediate=False):
        '''
        Manage remote estates. Time based processing of remote status such as
        presence (keep alive) etc.

        cascade induces the alive transactions to run join, allow, alive until
        failure or alive success

        immediate indicates to run first attempt immediately and not wait for timer

        availables = dict of remotes that are both alive and allowed
        '''
        alloweds = odict()
        aliveds = odict()
        reapeds = odict()
        for remote in self.remotes.values(): # should not start anything
            remote.manage(cascade=cascade, immediate=immediate)
            if remote.allowed:
                alloweds[remote.name] = remote
            if remote.alived:
                aliveds[remote.name] = remote
            if remote.reaped:
                reapeds[remote.name] = remote

        old = set(self.aliveds.keys())
        current = set(aliveds.keys())
        plus = current.difference(old)
        minus = old.difference(current)
        self.availables = current
        self.changeds = odict(plus=plus, minus=minus)
        self.alloweds = alloweds
        self.aliveds = aliveds
        self.reapeds = reapeds

    def _handleOneRx(self):
        '''
        Handle on message from .rxes deque
        Assumes that there is a message on the .rxes deque
        '''
        raw, sa = self.rxes.popleft()
        console.verbose("{0} received packet\n{1}\n".format(self.name, raw))

        packet = packeting.RxPacket(stack=self, packed=raw)
        try:
            packet.parseOuter()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_outer_error')
            return

        sh, sp = sa
        packet.data.update(sh=sh, sp=sp)
        self.processRx(packet)

    def processRx(self, packet):
        '''
        Process packet via associated transaction or
        reply with new correspondent transaction
        '''
        console.profuse("{0} received packet data\n{1}\n".format(self.name, packet.data))
        console.verbose("{0} received packet index: (rf={1[0]}, le={1[1]}, re={1[2]},"
                " si={1[3]}, ti={1[4]}, bf={1[5]})\n".format(self.name, packet.index))
        try:
            tkname = TrnsKind(packet.data['tk'])
        except ValueError as ex:
            tkname = None
        try:
            pkname = PcktKind(packet.data['pk'])
        except ValueError as ex:
            pkname = None
        console.verbose("{0} received trans kind = '{1}' packet kind = '{2}'"
                        "\n".format(self.name, tkname, pkname))

        bf = packet.data['bf']
        if bf:
            return  # broadcast transaction not yet supported

        de = packet.data['de']  # remote nuid
        se = packet.data['se']  # remote fuid
        tk = packet.data['tk']
        pk = packet.data['pk']
        cf = packet.data['cf']
        rsid = packet.data['si']

        remote = None

        if tk in [TrnsKind.join]: # join transaction
            sha = (packet.data['sh'],  packet.data['sp'])
            if rsid != 0: # join  must use sid == 0
                emsg = ("Stack '{0}'. Nonzero join sid '{1}' in packet from {2}."
                       " Dropping...\n".format(self.name, rsid, sha))
                console.terse(emsg)
                self.incStat('join_invalid_sid')
                return

            if cf: # cf = not rf, packet source is joinent, destination (self) is joiner
                if de == 0: # invalid since joiner rxed packet de (nuid) == 0
                    emsg = ("Stack '{0}'. Invalid join correspondence from '{1}',"
                            " nuid zero . Dropping...\n".format(self.name, sha))
                    console.terse(emsg)
                    self.incStat('join_invalid_nuid')
                    return
                if se == 0: # vacuous join since se (fuid) == 0
                    remote = self.joinees.get(sha, None)  # match remote by rha from .joinees
                    if remote and remote.nuid != de: # prior different
                        emsg = ("Stack '{0}'. Invalid join correspondence from '{1}',"
                            "nuid  {2} mismatch prior {3} . Dropping...\n".format(
                                self.name, sha, de, remote.nuid))
                        self.incStat('join_mismatch_nuid') # drop inconsistent nuid
                        return
                else: # non vacuous join match by nuid from .remotes
                    remote = self.remotes.get(de, None)

            else: # (rf = not cf) # source is joiner, destination (self) is joinent
                if se == 0: # invalid join
                    emsg = ("Stack '{0}'. Invalid join initiatance from '{1}',"
                            "fuid zero. Dropping...\n".format(self.name, sha))
                    console.terse(emsg)
                    self.incStat('join_invalid_fuid')
                    return
                if de == 0: # vacuous join match remote by rha from joinees
                    remote = self.joinees.get(sha, None)
                    if remote and remote.fuid != se: # check if prior is stale
                        if remote.fuid != 0:  # stale
                            emsg = ("Stack '{0}'. Prior stale join initiatance from '{1}',"
                                " fuid {2} mismatch prior {3}. Removing prior...\n".format(
                                        self.name, sha, se, remote.fuid))
                            console.terse(emsg)
                            del self.joinees[sha] # remove prior stale vacuous joinee
                            remote = None # reset

                    if not remote: # no current joinees for remote initiator at rha
                        # is it not first packet of join
                        if pk not in [PcktKind.request]:
                            emsg = ("Stack '{0}'. Stale join initiatance from '{1}',"
                                " Not a request and no remote. Dropping...\n".format(
                                        self.name, sha))
                            console.terse(emsg)
                            self.incStat('join_stale')
                            return

                        # create vacuous remote will be assigned to joinees in joinent
                        remote = estating.RemoteEstate(stack=self,
                                                       fuid=0,  # was fuid=se
                                                       sid=rsid,
                                                       ha=sha)

                else: # nonvacuous join match by nuid from .remotes
                    remote = self.remotes.get(de, None)
                    if not remote: # remote with nuid not exist
                        # reject renew , so tell it to retry with vacuous join
                        emsg = ("Stack '{0}'. Stale nuid '{1}' in packet from {2}."
                                " Renewing....\n".format( self.name, de, sha))
                        console.terse(emsg)
                        self.incStat('stale_nuid')
                        remote = estating.RemoteEstate(stack=self,
                                                        fuid=se,
                                                        sid=rsid,
                                                        ha=sha)
                        self.replyStale(packet, remote, renew=True) # nack stale transaction
                        return

        else: # not join transaction
            if rsid == 0: # cannot use sid == 0 on nonjoin transaction
                emsg = ("Stack '{0}'. Invalid Zero sid '{1}' for transaction {2} packet"
                       " {3}. Dropping...\n".format(self.name, rsid, tk, pk ))
                console.terse(emsg)
                self.incStat('invalid_sid')
                return

            if de == 0 or se == 0:
                emsg = ("Stack '{0}'. Invalid nonjoin from remote '{1}'."
                        " Zero nuid {2} or fuid {3}. Dropping...\n".format(
                            self.name, sha, de, se))
                console.terse(emsg)
                self.incStat('invalid_uid')
                return

            remote = self.remotes.get(de, None)

            if remote:
                if not cf: # packet from remotely initiated transaction
                    if not remote.validRsid(rsid): # invalid rsid
                        emsg = ("Stack '{0}'. Invalid nonjoin from '{1}'. Invalid sid "
                                " {2} in packet. Dropping...\n".format(self.name,
                                                            remote.name, rsid,))
                        console.terse(emsg)
                        self.incStat('stale_sid')
                        self.replyStale(packet, remote) # nack stale transaction
                        return

                    if rsid != remote.rsid: # updated valid rsid so change remote.rsid
                        remote.rsid = rsid
                        remote.removeStaleCorrespondents()

                if remote.reaped:
                    remote.unreap() # packet a valid packet so remote is not dead

        if remote:
            trans = remote.transactions.get(packet.index, None)
            if trans:
                trans.receive(packet)
                return

        if cf:  # cf = not rf packet from correspondent to non-existent locally initiated transaction
            self.stale(packet)
            return

        if not remote:
            emsg = ("Stack '{0}'. Unknown remote destination '{1}'. "
                    "Dropping...\n".format(self.name, de))
            console.terse(emsg)
            self.incStat('unknown_destination_uid')
            return

        self.correspond(packet, remote) # correspond to new transaction initiated by remote

    def correspond(self, packet, remote):
        '''
        Create correspondent transaction remote and handle packet
        '''
        if (packet.data['tk'] == TrnsKind.join and
                packet.data['pk'] == PcktKind.request):
            self.replyJoin(packet, remote)
            return

        if (packet.data['tk'] == TrnsKind.allow and
                packet.data['pk'] == PcktKind.hello):
            self.replyAllow(packet, remote)
            return

        if (packet.data['tk'] == TrnsKind.alive and
                packet.data['pk'] == PcktKind.request):
            self.replyAlive(packet, remote)
            return

        if (packet.data['tk'] == TrnsKind.message and
                packet.data['pk'] == PcktKind.message):
            if packet.data['af']:  # packet is a stale resend
                self.replyStale(packet, remote)
            else:
                self.replyMessage(packet, remote)
            return

        self.incStat('stale_packet')

    def process(self):
        '''
        Call .process or all remotes to allow timer based processing
        of their transactions
        '''
        #for transaction in self.transactions.values():
            #transaction.process()
        for remote in self.remotes.values():
            remote.process()

    def parseInner(self, packet):
        '''
        Parse inner of packet and return
        Assume all drop checks done
        '''
        try:
            packet.parseInner()
            console.verbose("Stack '{0}'. Received packet body\n{1}\n".format(
                    self.name, packet.body.data))
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_inner_error')
            return None
        return packet

    def stale(self, packet):
        '''
        Initiate stale transaction in order to nack a stale correspondent packet
        but only for preexisting remotes
        '''
        if packet.data['pk'] in [PcktKind.nack,
                                PcktKind.unjoined,
                                PcktKind.unallowed,
                                PcktKind.renew,
                                PcktKind.refuse,
                                PcktKind.reject,]:
            return # ignore stale nacks
        create = False
        uid = packet.data['de']
        remote = self.retrieveRemote(uid=uid)
        if not remote:
            emsg = "Stack '{0}'. Unknown remote id '{1}', fail to nack stale\n".format(
                      self.name, uid)
            console.terse(emsg)
            self.incStat('invalid_remote_eid')
            return
        data = odict(hk=self.Hk, bk=self.Bk)
        staler = transacting.Staler(stack=self,
                                    remote=remote,
                                    kind=packet.data['tk'],
                                    sid=packet.data['si'],
                                    tid=packet.data['ti'],
                                    txData=data,
                                    rxPacket=packet)
        staler.nack()

    def replyStale(self, packet, remote, renew=False):
        '''
        Correspond to stale initiated transaction
        '''
        if packet.data['pk'] in [PcktKind.nack,
                                 PcktKind.unjoined,
                                 PcktKind.unallowed,
                                 PcktKind.refuse,
                                 PcktKind.reject,]:
            return # ignore stale nacks
        data = odict(hk=self.Hk, bk=self.Bk)
        stalent = transacting.Stalent(stack=self,
                                      remote=remote,
                                      kind=packet.data['tk'],
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        if renew:
            stalent.nack(kind=PcktKind.renew.value) # refuse and renew
        else:
            stalent.nack()

    def join(self, uid=None, timeout=None, cascade=False, renewal=False):
        '''
        Initiate join transaction
        '''
        remote = self.retrieveRemote(uid=uid)
        if not remote:
            emsg = "Invalid remote destination estate id '{0}'\n".format(uid)
            console.terse(emsg)
            self.incStat('invalid_remote_eid')
            return

        timeout = timeout if timeout is not None else self.JoinerTimeout
        data = odict(hk=self.Hk, bk=self.Bk)
        joiner = transacting.Joiner(stack=self,
                                    remote=remote,
                                    timeout=timeout,
                                    txData=data,
                                    cascade=cascade,
                                    renewal=renewal)
        joiner.join()

    def replyJoin(self, packet, remote, timeout=None):
        '''
        Correspond to new join transaction
        '''
        timeout = timeout if timeout is not None else self.JoinentTimeout
        data = odict(hk=self.Hk, bk=self.Bk)
        joinent = transacting.Joinent(stack=self,
                                      remote=remote,
                                      timeout=timeout,
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        joinent.join()

    def allow(self, uid=None, timeout=None, cascade=False):
        '''
        Initiate allow transaction
        '''
        remote = self.retrieveRemote(uid=uid)
        if not remote:
            emsg = "Invalid remote destination estate id '{0}'\n".format(uid)
            console.terse(emsg)
            self.incStat('invalid_remote_eid')
            return
        data = odict(hk=self.Hk, bk=BodyKind.raw.value, fk=self.Fk)
        allower = transacting.Allower(stack=self,
                                      remote=remote,
                                      timeout=timeout,
                                      txData=data,
                                      cascade=cascade)
        allower.hello()

    def replyAllow(self, packet, remote):
        '''
        Correspond to new allow transaction
        '''
        data = odict(hk=self.Hk, bk=BodyKind.raw.value, fk=self.Fk)
        allowent = transacting.Allowent(stack=self,
                                        remote=remote,
                                        sid=packet.data['si'],
                                        tid=packet.data['ti'],
                                        txData=data,
                                        rxPacket=packet)
        allowent.hello()

    def alive(self, uid=None, timeout=None, cascade=False):
        '''
        Initiate alive transaction
        If duid is None then create remote at ha
        '''
        remote = self.retrieveRemote(uid=uid)
        if not remote:
            emsg = "Invalid remote destination estate id '{0}'\n".format(uid)
            console.terse(emsg)
            self.incStat('invalid_remote_eid')
            return
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        aliver = transacting.Aliver(stack=self,
                                    remote=remote,
                                    timeout=timeout,
                                    txData=data,
                                    cascade=cascade)
        aliver.alive()

    def replyAlive(self, packet, remote):
        '''
        Correspond to new Alive transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        alivent = transacting.Alivent(stack=self,
                                      remote=remote,
                                      bcst=packet.data['bf'],
                                      sid=packet.data['si'],
                                      tid=packet.data['ti'],
                                      txData=data,
                                      rxPacket=packet)
        alivent.alive()

    def transmit(self, msg, uid=None, timeout=None):
        '''
        Append duple (msg, uid) to .txMsgs deque
        If msg is not mapping then raises exception
        If uid is None then it will default to the first entry in .remotes
        If timeout is None then it will use Messenger default
        timeout of 0 means never timeout of message transaction
        '''
        if not isinstance(msg, Mapping):
            emsg = "Invalid msg, not a mapping {0}\n".format(msg)
            console.terse(emsg)
            self.incStat("invalid_transmit_body")
            return
        if uid is None:
            if not self.remotes:
                emsg = "No remote to send to\n"
                console.terse(emsg)
                self.incStat("invalid_destination")
                return
            uid = self.remotes.values()[0].uid
        self.txMsgs.append((msg, uid, timeout))

    def  _handleOneTxMsg(self):
        '''
        Take one message from .txMsgs deque and handle it
        Assumes there is a message on the deque
        '''
        # triple (body dict, destination uid, timout)
        body, uid, timeout = self.txMsgs.popleft()
        self.message(body, uid=uid, timeout=timeout)
        console.verbose("{0} sending\n{1}\n".format(self.name, body))

    def message(self, body, uid=None, timeout=None):
        '''
        Initiate message transaction to remote at duid
        If uid is None then create remote at ha
        If timeout is None then use Messenger default
        If timeout is 0 then never timeout
        '''
        remote = self.retrieveRemote(uid=uid)
        if not remote:
            emsg = "Invalid remote destination estate id '{0}'\n".format(uid)
            console.terse(emsg)
            self.incStat('invalid_remote_uid')
            return
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        messenger = transacting.Messenger(stack=self,
                                          remote=remote,
                                          timeout=timeout,
                                          txData=data,
                                          bcst=self.Bf,
                                          burst=self.BurstSize)
        messenger.message(body)

    def replyMessage(self, packet, remote):
        '''
        Correspond to new Message transaction
        '''
        data = odict(hk=self.Hk, bk=self.Bk, fk=self.Fk, ck=self.Ck)
        messengent = transacting.Messengent(stack=self,
                                            remote=remote,
                                            bcst=packet.data['bf'],
                                            sid=packet.data['si'],
                                            tid=packet.data['ti'],
                                            txData=data,
                                            rxPacket=packet)
        messengent.message()

