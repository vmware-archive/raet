# -*- coding: utf-8 -*-
'''
stacking.py raet protocol stacking classes
'''
# pylint: skip-file
# pylint: disable=W0611

# Import python libs
import socket
import binascii
import struct

try:
    import simplejson as json
except ImportError:
    import json

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding
from ioflo.base.aiding import packByte, unpackByte

from .. import raeting
from .. import nacling
from . import packeting
from . import estating

from ioflo.base.consoling import getConsole
console = getConsole()

class Transaction(object):
    '''
    RAET protocol transaction class
    '''
    Timeout =  5.0 # default timeout

    def __init__(self, stack=None, remote=None, kind=None, timeout=None,
                 rmt=False, bcst=False, wait=False, sid=None, tid=None,
                 txData=None, txPacket=None, rxPacket=None):
        '''
        Setup Transaction instance
        timeout of 0.0 means no timeout go forever
        '''
        self.stack = stack
        self.remote = remote
        self.kind = kind or raeting.PACKET_DEFAULTS['tk']

        if timeout is None:
            timeout = self.Timeout
        self.timeout = timeout
        self.timer = aiding.StoreTimer(self.stack.store, duration=self.timeout)

        self.rmt = rmt # remote initiator
        self.bcst = bcst # bf flag
        self.wait = wait # wf flag

        self.sid = sid
        self.tid = tid

        self.txData = txData or odict() # data used to prepare last txPacket
        self.txPacket = txPacket  # last tx packet needed for retries
        self.rxPacket = rxPacket  # last rx packet needed for index

    @property
    def index(self):
        '''
        Property is transaction tuple (rf, le, re, si, ti, bf,)
        Not to be used in join (Joiner and Joinent) since bootstrapping
        Use the txPacket (Joiner) or rxPacket (Joinent) .data instead
        '''
        le = self.remote.nuid
        re = self.remote.fuid
        return ((self.rmt, le, re, self.sid, self.tid, self.bcst,))

    def process(self):
        '''
        Process time based handling of transaction like timeout or retries
        '''
        pass

    def receive(self, packet):
        '''
        Process received packet Subclasses should super call this
        '''
        self.rxPacket = packet

    def transmit(self, packet):
        '''
        Queue tx duple on stack transmit queue
        '''
        try:
            self.stack.tx(packet.packed, self.remote.uid)
        except raeting.StackError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat(self.statKey())
            self.remove(remote=self.remote, index=packet.index)
            return
        self.txPacket = packet

    def add(self, remote=None, index=None):
        '''
        Add self to remote transactions
        '''
        if not index:
            index = self.index
        if not remote:
            remote = self.remote
        remote.addTransaction(index, self)

    def remove(self, remote=None, index=None):
        '''
        Remove self from remote transactions
        '''
        if not index:
            index = self.index
        if not remote:
            remote = self.remote
        if remote:
            remote.removeTransaction(index, transaction=self)

    def statKey(self):
        '''
        Return the stat name key from class name
        '''
        return ("{0}_transaction_failure".format(self.__class__.__name__.lower()))

    def nack(self, **kwa):
        '''
        Placeholder override in sub class
        nack to terminate transaction with other side of transaction
        '''
        pass

class Initiator(Transaction):
    '''
    RAET protocol initiator transaction class
    '''
    def __init__(self, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['rmt'] = False  # force rmt to False since local initator
        super(Initiator, self).__init__(**kwa)

    def process(self):
        '''
        Process time based handling of transaction like timeout or retries
        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.remove()

class Correspondent(Transaction):
    '''
    RAET protocol correspondent transaction class
    '''
    Requireds = ['sid', 'tid', 'rxPacket']

    def __init__(self, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['rmt'] = True  # force rmt to True since remote initiator

        missing = []
        for arg in self.Requireds:
            if arg not in kwa:
                missing.append(arg)
        if missing:
            emsg = "Missing required keyword arguments: '{0}'".format(missing)
            raise TypeError(emsg)

        super(Correspondent, self).__init__(**kwa)

class Staler(Initiator):
    '''
    RAET protocol Staler initiator transaction class
    '''
    def __init__(self, **kwa):
        '''
        Setup Transaction instance
        '''
        for key in ['kind', 'sid', 'tid', 'rxPacket']:
            if key not  in kwa:
                emsg = "Missing required keyword arguments: '{0}'".format(key)
                raise TypeError(emsg)
        super(Staler, self).__init__(**kwa)

        self.prep()

    def prep(self):
        '''
        Prepare .txData for nack to stale
        '''
        self.txData.update(
                            dh=self.rxPacket.data['sh'], # may need for index
                            dp=self.rxPacket.data['sp'], # may need for index
                            se=self.remote.nuid,
                            de=self.rxPacket.data['se'],
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada
                          )

    def nack(self):
        '''
        Send nack to stale packet from correspondent.
        This is used when a correspondent packet is received but no matching
        Initiator transaction is found. So create a dummy initiator and send
        a nack packet back. Do not add transaction so don't need to remove it.
        '''
        ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])
        emsg = "Staler {0}. Stale transaction from {1} nacking...\n".format(self.stack.name, ha )
        console.terse(emsg)
        self.stack.incStat('stale_correspondent_attempt')

        if self.rxPacket.data['se'] not in self.stack.remotes:
            emsg = "Staler {0}. Unknown correspondent estate id '{1}'\n".format(
                    self.stack.name, self.rxPacket.data['se'])
            console.terse(emsg)
            self.stack.incStat('unknown_correspondent_uid')
            #return #maybe we should return and not respond at all in this case

        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.nack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            return

        self.stack.txes.append((packet.packed, ha))
        console.terse("Staler {0}. Do Nack stale correspondent {1} at {2}\n".format(
                self.stack.name, ha, self.stack.store.stamp))
        self.stack.incStat('stale_correspondent_nack')


class Stalent(Correspondent):
    '''
    RAET protocol Stalent correspondent transaction class
    '''
    Requireds = ['kind', 'sid', 'tid', 'rxPacket']

    def __init__(self, **kwa):
        '''
        Setup Transaction instance
        '''
        super(Stalent, self).__init__(**kwa)

        self.prep()

    def prep(self):
        '''
        Prepare .txData for nack to stale
        '''
        self.txData.update(
                            dh=self.rxPacket.data['sh'], # may need for index
                            dp=self.rxPacket.data['sp'], # may need for index
                            se=self.rxPacket.data['de'],
                            de=self.rxPacket.data['se'],
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada
                           )

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to stale packet from initiator.
        This is used when a initiator packet is received but with a stale session id
        So create a dummy correspondent and send a nack packet back.
        Do not add transaction so don't need to remove it.
        '''
        ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])
        emsg = "Stalent {0}. Stale transaction from '{1}' nacking ...\n".format(
                self.stack.name, ha )
        console.terse(emsg)
        self.stack.incStat('stale_initiator_attempt')

        if self.rxPacket.data['se'] not in self.stack.remotes:
            emsg = "Stalent {0} Unknown initiator estate id '{1}'\n".format(
                    self.stack.name,
                    self.rxPacket.data['se'])
            console.terse(emsg)
            self.stack.incStat('unknown_initiator_uid')
            #return #maybe we should return and not respond at all in this case

        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            return

        if kind == raeting.pcktKinds.renew:
            console.terse("Stalent {0}. Do Renew of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.refuse:
            console.terse("Stalent {0}. Do Refuse of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.reject:
            console.terse("Stalent {0}. Do Reject of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Stalent {0}. Do Nack of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        else:
            console.terse("Stalent {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack

        self.stack.txes.append((packet.packed, ha))
        self.stack.incStat('stale_initiator_nack')

class Joiner(Initiator):
    '''
    RAET protocol Joiner Initiator class Dual of Joinent

    Joiner must always add new remote since always must anticipate response to
    request.
    '''
    RedoTimeoutMin = 1.0 # initial timeout
    RedoTimeoutMax = 4.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None,
                 cascade=False, renewal=False, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['kind'] = raeting.trnsKinds.join
        super(Joiner, self).__init__(**kwa)

        self.cascade = cascade

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.sid = 0 #always 0 for join
        self.tid = self.remote.nextTid()
        # fuid is assigned during join but want to preserve vacuousness for remove
        self.vacuous = (self.remote.fuid == 0)
        self.renewal = renewal # is current join a renew, vacuous rejoin
        self.pended = False # Farside Correspondent has pended remote acceptance
        self.prep()
        # don't dump remote yet since its ephemeral until we join and get valid uid

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Joiner, self).transmit(packet)
        self.redoTimer.restart()

    def add(self, remote=None, index=None):
        '''
        Augment with add self.remote to stack.joinees if vacuous
        '''
        super(Joiner, self).add(remote=remote, index=index)
        # self.remote is now assigned
        if self.vacuous: # vacuous
            self.stack.joinees[self.remote.ha] = self.remote

    def remove(self, remote=None, index=None):
        '''
        Remove self from stack transactions
        '''
        super(Joiner, self).remove(remote=remote, index=index)
        # self.remote is now assigned
        if self.vacuous: # vacuous
            if self.remote.ha in self.stack.joinees:
                del self.stack.joinees[self.remote.ha]

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Joiner, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.join:
            if packet.data['pk'] == raeting.pcktKinds.pend: # pending
                self.stack.incStat('joiner_rx_pend')
                self.pend()
            elif packet.data['pk'] == raeting.pcktKinds.response: # accepted
                self.stack.incStat('joiner_rx_response')
                self.accept()
            elif packet.data['pk'] == raeting.pcktKinds.nack: #stale
                self.stack.incStat('joiner_rx_nack')
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: #refused
                self.stack.incStat('joiner_rx_refuse')
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.renew: #renew
                self.stack.incStat('joiner_rx_renew')
                self.renew()
            elif packet.data['pk'] == raeting.pcktKinds.reject: #rejected
                self.stack.incStat('joiner_rx_reject')
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            if self.txPacket and self.txPacket.data['pk'] == raeting.pcktKinds.request:
                self.remove(index=self.txPacket.index)#index changes after accept
            else:
                self.remove(index=self.index) # in case never sent txPacket

            console.concise("Joiner {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))

            return

        # need keep sending join until accepted or timed out
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            if (self.txPacket and
                    self.txPacket.data['pk'] == raeting.pcktKinds.request):
                if not self.pended: # resend join
                    self.transmit(self.txPacket) #redo
                    console.concise("Joiner {0}. Redo Join with {1} at {2}\n".format(
                             self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('joiner_tx_join_redo')
            else: #check to see if status has changed to accept after other kind
                if self.remote:
                    status = self.stack.keep.statusRemote(self.remote, dump=True)
                    if status == raeting.acceptances.accepted:
                        self.completify()
                    elif status == raeting.acceptances.rejected:
                        "Joiner {0}: Estate '{1}' uid '{2}' keys rejected\n".format(
                                self.stack.name, self.remote.name, self.remote.uid)
                        self.stack.removeRemote(self.remote, clear=True)
                        # removeRemote also nacks

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update(
                            dh=self.remote.ha[0], # may need for index
                            dp=self.remote.ha[1], # may need for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada
                          )

    def join(self):
        '''
        Send join request
        '''
        joins = self.remote.joinInProcess()
        if joins:
            emsg = ("Joiner {0}. Join with {1} already in process. "
                    "Aborting...\n".format(
                                           self.stack.name,
                                           self.remote.name))
            console.concise(emsg)
            return

        self.remote.joined = None

        if self.stack.kind is None:
            self.stack.kind = 0
        else:
            if self.stack.kind < 0 or self.stack.kind > 255:
                emsg = ("Joiner {0}. Invalid application kind field value {1} for {2}. "
                                "Aborting...\n".format(
                                                       self.stack.name,
                                                       self.stack.kind,
                                                       self.remote.name))
                console.concise(emsg)
                return

        flags = [0, 0, 0, 0, 0, 0, 0, self.stack.main] # stack operation mode flags
        operation = packByte(fmt='11111111', fields=flags)
        body = odict([('name', self.stack.local.name),
                      ('mode', operation),
                      ('kind', self.stack.kind),
                      ('verhex', self.stack.local.signer.verhex),
                      ('pubhex', self.stack.local.priver.pubhex),
                      ('role', self.stack.local.role)])
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.request,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return
        console.concise("Joiner {0}. Do Join with {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
        self.transmit(packet)
        self.add(index=self.txPacket.index)

    def renew(self):
        '''
        Perform renew in response to nack renew
        Reset to vacuous Road data and try joining again if not main
        Otherwise act as if rejected
        '''
        if not self.stack.mutable: # renew not allowed on immutable road
            self.stack.incStat('join_renew_unallowed')
            emsg = ("Joiner {0}. Renew from '{1}' not allowed on immutable"
                    " road\n".format(self.stack.name, self.remote.name))
            console.terse(emsg)
            self.refuse()
            return

        console.terse("Joiner {0}. Renew from {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat('join_renew_attempt')
        self.remove(index=self.txPacket.index)
        if self.remote:
            self.remote.fuid = 0 # forces vacuous join
            self.stack.dumpRemote(self.remote) # since change fuid
        self.stack.join(uid=self.remote.uid, timeout=self.timeout, renewal=True)

    def pend(self):
        '''
        Process ack pend to join packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.pended = True

    def accept(self):
        '''
        Perform acceptance in response to join response packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        name = body.get('name')
        if not name:
            emsg = "Missing remote name in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.txPacket.index)
            return

        mode = body.get('mode')
        if mode is None or not isinstance(mode, int) or mode < 0 or mode > 255:
            emsg = "Missing or invalid remote stack operation mode in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.rxPacket.index)
            return
        flags = unpackByte(fmt='11111111', byte=mode, boolean=True)
        main = flags[7]

        kind = body.get('kind')
        if kind is None:
            emsg = "Missing or invalid remote application kind in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.rxPacket.index)
            return

        fuid = body.get('uid')
        if not fuid: # None or zero
            emsg = "Missing or invalid remote farside uid in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.txPacket.index)
            return

        verhex = body.get('verhex')
        if not verhex:
            emsg = "Missing remote verifier key in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.txPacket.index)
            return

        pubhex = body.get('pubhex')
        if not pubhex:
            emsg = "Missing remote crypt key in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.txPacket.index)
            return

        role = body.get('role')
        if not role:
            emsg = "Missing remote role in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.txPacket.index)
            return

        rha = (data['sh'], data['sp'])
        reid = data['se']
        leid = data['de']

        if self.vacuous:
            self.remote.fuid = fuid
            if not self.renewal: # ephemeral like
                if name != self.remote.name:
                    if name in self.stack.nameRemotes:
                        emsg = ("Joiner {0}.  New name '{1}' unavailable for "
                                "remote {2}\n".format(self.stack.name,
                                                      name,
                                                      self.remote.name))
                        console.terse(emsg)
                        self.nack(kind=raeting.pcktKinds.reject)
                        return
                    try:
                        self.stack.renameRemote(self.remote, new=name)
                    except raeting.StackError as ex:
                        console.terse(str(ex) + '\n')
                        self.stack.incStat(self.statKey())
                        self.remove(index=self.txPacket.index)
                        return
                self.remote.main = main
                self.remote.kind = kind
                self.remote.fuid = fuid
                self.remote.role = role
                self.remote.verfer = nacling.Verifier(verhex) # verify key manager
                self.remote.pubber = nacling.Publican(pubhex) # long term crypt key manager

        sameRoleKeys = (role == self.remote.role and
                        verhex == self.remote.verfer.keyhex and
                        pubhex == self.remote.pubber.keyhex)

        sameAll = (sameRoleKeys and
                   name == self.remote.name and
                   rha == self.remote.ha and
                   fuid == self.remote.fuid and
                   main == self.remote.main and
                   kind == self.remote.kind)

        if not sameAll and not self.stack.mutable:
            emsg = ("Joiner {0}. Attempt to change immutable road by "
                                   "'{1}'\n".format(self.stack.name,
                                                    self.remote.name))
            console.terse(emsg)
            self.nack(kind=raeting.pcktKinds.reject) # reject not mutable road
            self.remove(index=self.txPacket.index)
            return

        status = self.stack.keep.statusRole(role=role,
                                                    verhex=verhex,
                                                    pubhex=pubhex,
                                                    dump=True)

        if status == raeting.acceptances.rejected:
            if sameRoleKeys:
                self.stack.removeRemote(self.remote, clear=True)
                # remove also nacks so will also reject
            else:
                self.nack(kind=raeting.pcktKinds.reject) # reject
            return

        # accepted or pending
        self.remote.acceptance = status # change acceptance of remote

        if not sameAll: # (and mutable)
            if (name in self.stack.nameRemotes and
                    self.stack.nameRemotes[name] is not self.remote): # non unique name
                emsg = "Joiner {0}. Name '{1}' unavailable for remote {2}\n".format(
                                self.stack.name, name, self.remote.name)
                console.terse(emsg)
                self.nack(kind=raeting.pcktKinds.reject)
                return

            if name != self.remote.name:
                try:
                    self.stack.renameRemote(self.remote, new=name)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(index=self.txPacket.index)
                    return

            if rha != self.remote.ha:
                self.remote.ha = rha
            if fuid != self.remote.fuid:
                self.remote.fuid = fuid
            if main != self.remote.main:
                self.remote.main = main
            if kind != self.remote.kind:
                self.remote.kind = kind
            if self.remote.role != role:
                self.remote.role = role # rerole
            if verhex != self.remote.verfer.keyhex:
                self.remote.verfer = nacling.Verifier(verhex) # verify key manager
            if pubhex != self.remote.pubber.keyhex:
                self.remote.pubber = nacling.Publican(pubhex) # long term crypt key manager
            # don't dump until complete

        if status == raeting.acceptances.accepted: # accepted
            self.completify()
            return

        # else status == raeting.acceptance.pending or None
        self.pendify()

    def pendify(self):
        '''
        Perform pending on remote
        '''
        self.stack.dumpRemote(self.remote)
        self.ackPend()

    def ackPend(self):
        '''
        Send ack pending to accept response
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.pend,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.txPacket.index)
            return

        console.concise("Joiner {0}. Do Ack Pend of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

        self.transmit(packet)

    def completify(self):
        '''
        Finalize full acceptance
        '''
        if self.remote.sid == 0: # session id  must be non-zero after join
            self.remote.nextSid() # start new session
            self.remote.replaceStaleInitiators() # this join not stale since sid == 0
        if self.vacuous:
            self.remote.rsid = 0 # reset .rsid on vacuous join so allow will work
        self.remote.joined = True #accepted
        self.stack.dumpRemote(self.remote)
        self.ackAccept()

    def ackAccept(self):
        '''
        Send ack accepted to accept response
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.ack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.txPacket.index)
            return

        console.concise("Joiner {0}. Do Ack Accept, Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("join_initiate_complete")

        self.transmit(packet)
        self.remove(index=self.txPacket.index) # self.rxPacket.index

        if self.cascade:
            self.stack.allow(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)

    def refuse(self):
        '''
        Process nack to join packet refused as join already in progress or some
        other problem that does not change the joined attribute
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        console.terse("Joiner {0}. Refused by {1} at {2}\n".format(
                 self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remove(index=self.txPacket.index)

    def reject(self):
        '''
        Process nack to join packet, join rejected
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        console.terse("Joiner {0}. Rejected by {1} at {2}\n".format(
                 self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remove(index=self.txPacket.index)
        self.stack.removeRemote(self.remote, clear=True)

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to accept response
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.txPacket.index)
            return

        if kind == raeting.pcktKinds.refuse:
            console.terse("Joiner {0}. Do Nack Refuse of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif  kind == raeting.pcktKinds.reject:
            console.terse("Joiner {0}. Do Nack Reject of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Joiner {0}. Do Nack of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        else:
            console.terse("Joiner {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack
        self.stack.incStat(self.statKey())
        self.transmit(packet)
        self.remove(index=self.txPacket.index)

class Joinent(Correspondent):
    '''
    RAET protocol Joinent transaction class, dual of Joiner

    Joinent does not add new remote to .remotes if rejected
    '''
    RedoTimeoutMin = 0.1 # initial timeout
    RedoTimeoutMax = 2.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['kind'] = raeting.trnsKinds.join
        super(Joinent, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store, duration=0.0)
        self.vacuous = None # gets set in join method
        self.pended = False # Farside initiator has pended remote acceptance
        self.prep()

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Joinent, self).transmit(packet)
        self.redoTimer.restart()

    def add(self, remote=None, index=None):
        '''
        Augment with add self.remote to stack.joinees if vacuous
        '''
        super(Joinent, self).add(remote=remote, index=index)
        # self.remote is now assigned
        if self.vacuous: # vacuous
            self.stack.joinees[self.remote.ha] = self.remote

    def remove(self, remote=None, index=None):
        '''
        Remove self from stack transactions
        '''
        super(Joinent, self).remove(remote=remote, index=index)
        # self.remote is now assigned
        if self.vacuous: # vacuous
            if self.remote.ha in self.stack.joinees:
                del self.stack.joinees[self.remote.ha]

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Joinent, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.join:
            if packet.data['pk'] == raeting.pcktKinds.request:
                self.stack.incStat('joinent_rx_request')
                self.join()
            elif packet.data['pk'] == raeting.pcktKinds.pend: # maybe pending
                self.stack.incStat('joinent_rx_pend')
                self.pend()
            elif packet.data['pk'] == raeting.pcktKinds.ack: #accepted by joiner
                self.stack.incStat('joinent_rx_ack')
                self.complete()
            elif packet.data['pk'] == raeting.pcktKinds.nack: #stale
                self.stack.incStat('joinent_rx_nack')
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: #refused
                self.stack.incStat('joinent_rx_refuse')
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.reject: #rejected
                self.stack.incStat('joinent_rx_reject')
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack() # stale
            console.concise("Joinent {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

        # need to perform the check for accepted status and then send accept
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)

            if (self.txPacket and
                    self.txPacket.data['pk'] == raeting.pcktKinds.response):
                if not self.pended: # resend accept packet
                    self.transmit(self.txPacket) #redo
                    console.concise("Joinent {0}. Redo Accept with {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('joinent_tx_accept_redo')
            else: #check to see if status has changed to accept
                if self.remote:
                    status = self.stack.keep.statusRemote(self.remote, dump=True)
                    if status == raeting.acceptances.accepted:
                        self.ackAccept()
                    elif status == raeting.acceptances.rejected:
                        "Stack {0}: Estate '{1}' uid '{2}' keys rejected\n".format(
                                self.stack.name, self.remote.name, self.remote.uid)
                        self.stack.removeRemote(self.remote,clear=True)
                        # removeRemote also nacks

    def prep(self):
        '''
        Prepare .txData
        '''
        #since bootstrap transaction use the reversed seid and deid from packet
        self.txData.update(
                            dh=self.rxPacket.data['sh'], # may need for index
                            dp=self.rxPacket.data['sp'], # may need for index
                            se=self.rxPacket.data['de'],
                            de=self.rxPacket.data['se'],
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada,
                          )

    def join(self):
        '''
        Process join packet
        Each estate must have a set of unique credentials on the road
        The credentials are.
        uid (estate id), name, ha (host address, port)
        Each of the three credentials must be separably unique on the Road, that is
        the uid must be unique, the name must be unique, the ha must be unique.

        The other credentials are the role and keys. Multiple estates may share
        the same role and associated keys. The keys are the signing key and the
        encryption key.

        Once an estate has joined the first time it will be assigned an uid.
        Changing any of the credentials after this requires that the Road be mutable.

        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        # Don't add transaction yet wait till later until transaction is permitted
        # as not a duplicate and role keys are not rejected

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        name = body.get('name')
        if not name:
            emsg = "Missing remote name in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(index=self.rxPacket.index)
            return

        mode = body.get('mode')
        if mode is None or not isinstance(mode, int) or mode < 0 or mode > 255:
            emsg = "Missing or invalid remote stack operation mode in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.rxPacket.index)
            return
        flags = unpackByte(fmt='11111111', byte=mode, boolean=True)
        main = flags[7]

        kind = body.get('kind')
        if kind is None:
            emsg = "Missing or invalid remote application kind in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(index=self.rxPacket.index)
            return

        verhex = body.get('verhex')
        if not verhex:
            emsg = "Missing remote verifier key in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(index=self.rxPacket.index)
            return

        pubhex = body.get('pubhex')
        if not pubhex:
            emsg = "Missing remote crypt key in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(index=self.rxPacket.index)
            return

        role = body.get('role')
        if not role:
            emsg = "Missing remote role in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(index=self.rxPacket.index)
            return

        rha = (data['sh'], data['sp'])
        reid = data['se']
        leid = data['de']

        self.vacuous = (leid == 0)

        joins = self.remote.joinInProcess()
        for join in joins: # only one join at a time is permitted
            if join is self: # duplicate join packet so drop
                emsg = ("Joinent {0}. Duplicate join from {1}. "
                        "Dropping...\n".format(self.stack.name, self.remote.name))
                console.concise(emsg)
                self.stack.incStat('duplicate_join_attempt')
                return

            if join.rmt: # is already a correspondent to a join
                emsg = ("Joinent {0}. Another joinent already in process with {1}. "
                       "Aborting...\n".format(self.stack.name, self.remote.name))
                console.concise(emsg)
                self.stack.incStat('redundant_join_attempt')
                self.nack(kind=raeting.pcktKinds.refuse)
                return

            else: # already initiator join in process, resolve race condition
                if self.vacuous and not join.vacuous: # non-vacuous beats vacuous
                    emsg = ("Joinent {0}. Already initiated non-vacuous join with {1}. "
                            "Aborting because vacuous...\n".format(
                                self.stack.name, self.remote.name))
                    console.concise(emsg)
                    self.stack.incStat('redundant_join_attempt')
                    self.nack(kind=raeting.pcktKinds.refuse)
                    return

                if not self.vacuous and join.vacuous: # non-vacuous beats vacuous
                    emsg = ("Joinent {0}. Removing vacuous initiator join with"
                            " {1}. Proceeding because not vacuous...\n".format(
                                            self.stack.name, self.remote.name))
                    console.concise(emsg)
                    join.nack(kind=raeting.pcktKinds.refuse)

                else: # both vacuous or non-vacuous, so use name to resolve
                    if self.stack.local.name < name: # abort correspondent
                        emsg = ("Joinent {0}. Already initiated join with {1}. "
                                "Aborting because lesser local name...\n".format(
                                    self.stack.name, self.remote.name))
                        console.concise(emsg)
                        self.stack.incStat('redundant_join_attempt')
                        self.nack(kind=raeting.pcktKinds.refuse)
                        return

                    else: # abort initiator, could let other side nack do this
                        emsg = ("Joinent {0}. Removing initiator join with {1}. "
                                "Proceeding because lesser local name...\n".format(
                                    self.stack.name, self.remote.name))
                        console.concise(emsg)
                        join.nack(kind=raeting.pcktKinds.refuse)

        if self.vacuous: # vacuous join
            if not self.stack.main:
                emsg = "Joinent {0}. Invalid vacuous join not main\n".format(self.stack.name)
                console.terse(emsg)
                self.nack(kind=raeting.pcktKinds.reject)
                return

            if name in self.stack.nameRemotes: # non ephemeral name match
                self.remote = self.stack.nameRemotes[name] # replace so not ephemeral

            else: # ephemeral and unique name
                self.remote.name = name
                self.remote.main = main
                self.remote.kind = kind
                self.remote.rha = rha
                self.remote.role = role
                self.remote.verfer = nacling.Verifier(verhex) # verify key manager
                self.remote.pubber = nacling.Publican(pubhex) # long term crypt key manager
                if self.remote.fuid != reid: # created in stack with fuid = reid
                    emsg = ("Joinent {0}. Mishandled join reid='{1}' !=  fuid='{2}' for "
                           "remote {2}\n".format(self.stack.name, reid, remote.fuid, name))
                    console.terse(emsg)
                    self.nack(kind=raeting.pcktKinds.reject)
                    return

        else: # non vacuous join
            if self.remote is not self.stack.remotes[leid]: # something is wrong
                emsg = "Joinent {0}. Mishandled join leid '{1}' for remote {2}\n".format(
                                                    self.stack.name, leid, name)
                console.terse(emsg)
                self.nack(kind=raeting.pcktKinds.reject)
                return


        sameRoleKeys = (role == self.remote.role and
                        verhex == self.remote.verfer.keyhex and
                        pubhex == self.remote.pubber.keyhex)

        sameAll = (sameRoleKeys and
                   name == self.remote.name and
                   rha == self.remote.ha and
                   reid == self.remote.fuid and
                   main == self.remote.main and
                   kind == self.remote.kind)

        if not sameAll and not self.stack.mutable:
            emsg = ("Joinent {0}. Attempt to change immutable road by "
                                   "'{1}'\n".format(self.stack.name,
                                                    self.remote.name))
            console.terse(emsg)
            # reject not mutable road
            self.nack(kind=raeting.pcktKinds.reject)
            return

        status = self.stack.keep.statusRole(role=role,
                                            verhex=verhex,
                                            pubhex=pubhex,
                                            dump=True)


        if status == raeting.acceptances.rejected:
            emsg = ("Joinent {0}. Keys of role='{1}' rejected for remote name='{2}'"
                    " nuid='{3}' fuid='{4}' ha='{5}'\n".format(self.stack.name,
                                                              self.remote.role,
                                                              self.remote.name,
                                                              self.remote.nuid,
                                                              self.remote.fuid,
                                                              self.remote.ha))
            console.concise(emsg)
            if sameRoleKeys and self.remote.uid in self.stack.remotes:
                self.stack.removeRemote(self.remote, clear=True) #clear remote
                # removeRemote also nacks which is a reject
            else: # reject as keys rejected
                self.nack(kind=raeting.pcktKinds.reject)
            return

        #accepted or pended
        self.remote.acceptance = status

        if sameAll: #ephemeral will always be sameAll because assigned above
            if self.remote.uid not in self.stack.remotes: # ephemeral
                try:
                    self.stack.addRemote(self.remote)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    return

                emsg = ("Joinent {0}. Added new remote name='{1}' nuid='{2}' fuid='{3}' "
                        "ha='{4}' role='{5}'\n".format(self.stack.name,
                                          self.remote.name,
                                          self.remote.nuid,
                                          self.remote.fuid,
                                          self.remote.ha,
                                          self.remote.role))
                console.concise(emsg)
                # do dump until complete

        else: # not sameAll (and mutable)
            # do both unique name check first so only change road if new unique
            if (name in self.stack.nameRemotes and
                    self.stack.nameRemotes[name] is not self.remote): # non unique name
                emsg = "Joinent {0}.  Name '{1}' unavailable for remote {2}\n".format(
                                self.stack.name, name, self.remote.name)
                console.terse(emsg)
                self.nack(kind=raeting.pcktKinds.reject)
                return

            if name != self.remote.name:
                try:
                    self.stack.renameRemote(self.remote, new=name)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    return

            if rha != self.remote.ha:
                self.remote.ha = rha
            if reid != self.remote.fuid:
                self.remote.fuid = reid
            if main != self.remote.main:
                self.remote.main = main
            if kind != self.remote.kind:
                self.remote.kind = kind
            if role != self.remote.role: # rerole
                self.remote.role = role
            if verhex != self.remote.verfer.keyhex:
                self.remote.verfer = nacling.Verifier(verhex) # verify key manager
            if pubhex != self.remote.pubber.keyhex:
                self.remote.pubber = nacling.Publican(pubhex) # long term crypt key manager

        # add transaction
        self.add(remote=self.remote, index=self.rxPacket.index)
        self.remote.joined = None

        if status == raeting.acceptances.accepted:
            duration = min(
                            max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                            self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            self.ackAccept()
            return

        # status == raeting.acceptance.pending or status == None:
        self.pendify()  # change to ackPend

    def pendify(self):
        '''
        Performing pending operation on remote
        '''
        self.stack.dumpRemote(self.remote)
        self.ackPend()

    def ackPend(self):
        '''
        Send ack to join request
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.pend,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.rxPacket.index)
            return

        console.concise("Joinent {0}. Do Ack Pending accept of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.transmit(packet)

    def ackAccept(self):
        '''
        Send accept response to join request
        '''
        if self.stack.kind is None:
            self.stack.kind = 0
        else:
            if self.stack.kind < 0 or self.stack.kind > 255:
                emsg = ("Joinent {0}. Invalid application kind field value {1} for {2}. "
                                "Aborting...\n".format(
                                                       self.stack.name,
                                                       self.stack.kind,
                                                       self.remote.name))
                console.concise(emsg)
                return

        flags = [0, 0, 0, 0, 0, 0, 0, self.stack.main] # stack operation mode flags
        operation = packByte(fmt='11111111', fields=flags)
        body = odict([ ('name', self.stack.local.name),
                       ('mode', operation),
                       ('kind', self.stack.kind),
                       ('uid', self.remote.uid),
                       ('verhex', self.stack.local.signer.verhex),
                       ('pubhex', self.stack.local.priver.pubhex),
                       ('role', self.stack.local.role)])
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.response,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.rxPacket.index)
            return

        console.concise("Joinent {0}. Do Accept of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.transmit(packet)

    def pend(self):
        '''
        Process ack pend to join packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.pended = True

    def complete(self):
        '''
        process ack to accept response
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        console.terse("Joinent {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("join_correspond_complete")

        if self.remote.sid == 0: # session id  must be non-zero after join
            self.remote.nextSid() # start new session
            self.remote.replaceStaleInitiators()
        if self.vacuous:
            self.remote.rsid = 0 # reset .rsid on vacuous join so allow will work
        self.remote.joined = True # accepted
        self.stack.dumpRemote(self.remote)
        self.remove(index=self.rxPacket.index)

    def reject(self):
        '''
        Process reject nack because keys rejected
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        console.terse("Joinent {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remove(index=self.rxPacket.index)
        self.stack.removeRemote(self.remote, clear=True)

    def refuse(self):
        '''
        Process refuse nack because join already in progress or stale
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        console.terse("Joinent {0}. Refused by {1} at {2}\n".format(
                 self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remove(index=self.rxPacket.index)

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to join request.
        Sometimes nack occurs without remote being added so have to nack using
        rxPacket source ha.
        '''
        #if not self.remote or self.remote.uid not in self.stack.remotes:
            #self.txData.update( dh=self.rxPacket.data['sh'], dp=self.rxPacket.data['sp'],)
            #ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])
        #else:
            #ha = self.remote.ha

        ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])

        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.rxPacket.index)
            return

        if kind == raeting.pcktKinds.renew:
            console.terse("Joinent {0}. Do Nack Renew of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.refuse:
            console.terse("Joinent {0}. Do Nack Refuse of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.reject:
            console.terse("Joinent {0}. Do Nack Reject of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Joinent {0}. Do Nack of {1} at {2}\n".format(
                    self.stack.name, ha, self.stack.store.stamp))
        else:
            console.terse("Joinent {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack

        self.stack.incStat(self.statKey())

        if ha:
            self.stack.txes.append((packet.packed, ha))
        else:
            self.transmit(packet)
        self.remove(index=self.rxPacket.index)

class Allower(Initiator):
    '''
    RAET protocol Allower Initiator class Dual of Allowent
    CurveCP handshake
    '''
    Timeout = 4.0
    RedoTimeoutMin = 0.25 # initial timeout
    RedoTimeoutMax = 1.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None,
                 cascade=False, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.allow
        super(Allower, self).__init__(**kwa)

        self.cascade = cascade

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.sid = self.remote.sid
        self.tid = self.remote.nextTid()
        self.oreo = None # cookie from correspondent needed until handshake completed
        self.prep() # prepare .txData

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Allower, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Allower, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.allow:
            if packet.data['pk'] == raeting.pcktKinds.cookie:
                self.cookie()
            elif packet.data['pk'] == raeting.pcktKinds.ack:
                self.allow()
            elif packet.data['pk'] == raeting.pcktKinds.nack: # rejected
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: # refused
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.reject: #rejected
                self.reject()
            elif packet.data['pk'] == raeting.pcktKinds.unjoined: # unjoined
                self.unjoin()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.remove()
            console.concise("Allower {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

        # need keep sending join until accepted or timed out
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            if self.txPacket:
                if self.txPacket.data['pk'] == raeting.pcktKinds.hello:
                    self.transmit(self.txPacket) # redo
                    console.concise("Allower {0}. Redo Hello with {1} at {2}\n".format(
                            self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_hello')

                if self.txPacket.data['pk'] == raeting.pcktKinds.initiate:
                    self.transmit(self.txPacket) # redo
                    console.concise("Allower {0}. Redo Initiate with {1} at {2}\n".format(
                             self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_initiate')

                if self.txPacket.data['pk'] == raeting.pcktKinds.ack:
                    self.transmit(self.txPacket) # redo
                    console.concise("Allower {0}. Redo Ack Final with {1} at {2}\n".format(
                             self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_final')

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update(
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                          )

    def hello(self):
        '''
        Send hello request
        '''
        joins = self.remote.joinInProcess()
        if joins:
            emsg = ("Allower {0}. Attempt to allow while join still in process with {1}.  "
                                    "Aborting...\n".format(self.stack.name, self.remote.name))
            console.concise(emsg)
            self.stack.incStat('invalid_allow_attempt')
            return

        allows = self.remote.allowInProcess()
        if allows:
            emsg = ("Allower {0}. Allow with {1} already in process\n".format(
                                    self.stack.name, self.remote.name))
            console.concise(emsg)
            return

        self.remote.allowed = None
        if not self.remote.joined:
            emsg = "Allower {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_remote')
            self.stack.join(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)
            return

        self.remote.rekey() # refresh short term keys and reset .allowed to None
        self.add()

        plain = binascii.hexlify("".rjust(32, '\x00'))
        cipher, nonce = self.remote.privee.encrypt(plain, self.remote.pubber.key)
        body = raeting.HELLO_PACKER.pack(plain, self.remote.privee.pubraw, cipher, nonce)

        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.hello,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return
        self.transmit(packet)
        console.concise("Allower {0}. Do Hello with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

    def cookie(self):
        '''
        Process cookie packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        if not isinstance(body, basestring):
            emsg = "Invalid format of cookie packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        if len(body) != raeting.COOKIE_PACKER.size:
            emsg = "Invalid length of cookie packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        cipher, nonce = raeting.COOKIE_PACKER.unpack(body)

        try:
            msg = self.remote.privee.decrypt(cipher, nonce, self.remote.pubber.key)
        except ValueError as ex:
            emsg = "Invalid cookie stuff: '{0}'\n".format(str(ex))
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        if len(msg) != raeting.COOKIESTUFF_PACKER.size:
            emsg = "Invalid length of cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        shortraw, seid, deid, oreo = raeting.COOKIESTUFF_PACKER.unpack(msg)

        if seid != self.remote.fuid or deid != self.remote.nuid:
            emsg = "Invalid seid or deid fields in cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        self.oreo = binascii.hexlify(oreo)
        self.remote.publee = nacling.Publican(key=shortraw)

        self.initiate()

    def initiate(self):
        '''
        Send initiate request to cookie response to hello request
        '''
        vcipher, vnonce = self.stack.local.priver.encrypt(self.remote.privee.pubraw,
                                                self.remote.pubber.key)

        fqdn = self.remote.fqdn
        if isinstance(fqdn, unicode):
            fqdn = fqdn.encode('ascii', 'ignore')
        fqdn = fqdn.ljust(128, ' ')[:128]

        stuff = raeting.INITIATESTUFF_PACKER.pack(self.stack.local.priver.pubraw,
                                                  vcipher,
                                                  vnonce,
                                                  fqdn)

        cipher, nonce = self.remote.privee.encrypt(stuff, self.remote.publee.key)

        oreo = binascii.unhexlify(self.oreo)
        body = raeting.INITIATE_PACKER.pack(self.remote.privee.pubraw,
                                            oreo,
                                            cipher,
                                            nonce)

        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.initiate,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        self.transmit(packet)
        console.concise("Allower {0}. Do Initiate with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

    def allow(self):
        '''
        Process ackInitiate packet
        Perform allowment in response to ack to initiate packet
        Transmits ack to complete transaction so correspondent knows
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.allowed = True
        self.ackFinal()

    def ackFinal(self):
        '''
        Send ack to ack Initiate to terminate transaction
        This is so both sides wait on acks so transaction is not restarted until
        boths sides see completion.
        '''
        body = ""
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.ack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        self.remove()
        self.transmit(packet)

        console.concise("Allower {0}. Do Ack Final, Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("allow_initiate_complete")

        self.remote.nextSid() # start new session always on successful allow
        self.remote.replaceStaleInitiators()
        self.stack.dumpRemote(self.remote)
        self.remote.sendSavedMessages() # could include messages saved on rejoin
        if self.cascade:
            self.stack.alive(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to accept response
        '''
        body = ""
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        if kind == raeting.pcktKinds.refuse:
            console.terse("Allower {0}. Do Nack Refuse of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.reject:
            console.terse("Allower {0}. Do Nack Reject of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Allower {0}. Do Nack of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        else:
            console.terse("Allower {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack

        self.remove()
        self.stack.incStat(self.statKey())
        self.transmit(packet)

    def refuse(self):
        '''
        Process nack refule to packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remove()
        console.concise("Allower {0}. Refused by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def reject(self):
        '''
        Process nack reject to packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.allowed = False
        self.remove()
        console.concise("Allower {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def unjoin(self):
        '''
        Process unjoin packet
        terminate in response to unjoin
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.joined = False
        self.remove()
        console.concise("Allower {0}. Rejected unjoin by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)

class Allowent(Correspondent):
    '''
    RAET protocol Allowent Correspondent class Dual of Allower
    CurveCP handshake
    '''
    Timeout = 4.0
    RedoTimeoutMin = 0.25 # initial timeout
    RedoTimeoutMax = 1.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.allow
        super(Allowent, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.oreo = None #keep locally generated oreo around for redos
        self.prep() # prepare .txData

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Allowent, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Allowent, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.allow:
            if packet.data['pk'] == raeting.pcktKinds.hello:
                self.hello()
            elif packet.data['pk'] == raeting.pcktKinds.initiate:
                self.initiate()
            elif packet.data['pk'] == raeting.pcktKinds.ack:
                self.final()
            elif packet.data['pk'] == raeting.pcktKinds.nack: # rejected
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: # refused
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.reject: # rejected
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack(kind=raeting.pcktKinds.refuse)
            console.concise("Allowent {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

        # need to perform the check for accepted status and then send accept
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)

            if self.txPacket:
                if self.txPacket.data['pk'] == raeting.pcktKinds.cookie:
                    self.transmit(self.txPacket) #redo
                    console.concise("Allowent {0}. Redo Cookie with {1} at {2}\n".format(
                             self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_cookie')

                if self.txPacket.data['pk'] == raeting.pcktKinds.ack:
                    self.transmit(self.txPacket) #redo
                    console.concise("Allowent {0}. Redo Ack with {1} at {2}\n".format(
                             self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_allow')

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( #sh=self.stack.local.ha[0],
                            #sp=self.stack.local.ha[1],
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid, )

    def hello(self):
        '''
        Process hello packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        joins = self.remote.joinInProcess()
        if joins:
            emsg = ("Allowent {0}. Attempt to allow while join already in process with {1}.  "
                                    "Aborting...\n".format(self.stack.name, self.remote.name))
            console.concise(emsg)
            self.stack.incStat('invalid_allow_attempt')
            self.nack(kind=raeting.pcktKinds.refuse)

        allows = self.remote.allowInProcess()
        for allow in allows:
            if allow is self:
                emsg = ("Allowent {0}. Duplicate allow hello from {1}. "
                        "Dropping...\n".format(self.stack.name, self.remote.name))
                console.concise(emsg)
                self.stack.incStat('duplicate_allow_attempt')
                return

            if allow.rmt: # is already a correspondent to an allow
                emsg = ("Allowent {0}. Another allowent already in process with {1}. "
                        "Aborting...\n".format(self.stack.name, self.remote.name))
                console.concise(emsg)
                self.stack.incStat('redundant_allow_attempt')
                self.nack(kind=raeting.pcktKinds.refuse)
                return

            else: # already initiator allow in process, resolve race condition
                if self.stack.local.name < self.remote.name: # abort correspondent
                    emsg = ("Allowent {0}. Already initiated allow with {1}. "
                            "Aborting because lesser local name...\n".format(
                                self.stack.name, self.remote.name))
                    console.concise(emsg)
                    self.stack.incStat('redundant_allow_attempt')
                    self.nack(kind=raeting.pcktKinds.refuse)
                    return

                else: # abort initiator, could let otherside nack do this
                    emsg = ("Allowent {0}. Removing initiator allow with {1}. "
                            "Proceeding because lesser local name...\n".format(
                                self.stack.name, self.remote.name))
                    console.concise(emsg)
                    allow.nack(kind=raeting.pcktKinds.refuse)

        self.remote.allowed = None

        if not self.remote.joined:
            emsg = "Allowent {0}. Must be joined with {1} first\n".format(
                self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_allow_attempt')
            self.nack(kind=raeting.pcktKinds.unjoined)
            return

        self.remote.rekey() # refresh short term keys and .allowed
        self.add()

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        if not isinstance(body, basestring):
            emsg = "Invalid format of hello packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        if len(body) != raeting.HELLO_PACKER.size:
            emsg = "Invalid length of hello packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        plain, shortraw, cipher, nonce = raeting.HELLO_PACKER.unpack(body)

        self.remote.publee = nacling.Publican(key=shortraw)
        msg = self.stack.local.priver.decrypt(cipher, nonce, self.remote.publee.key)
        if msg != plain :
            emsg = "Invalid plain not match decrypted cipher\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        self.cookie()

    def cookie(self):
        '''
        Send Cookie Packet
        '''
        oreo = self.stack.local.priver.nonce()
        self.oreo = binascii.hexlify(oreo)

        stuff = raeting.COOKIESTUFF_PACKER.pack(self.remote.privee.pubraw,
                                                self.remote.nuid,
                                                self.remote.fuid,
                                                oreo)

        cipher, nonce = self.stack.local.priver.encrypt(stuff, self.remote.publee.key)
        body = raeting.COOKIE_PACKER.pack(cipher, nonce)
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.cookie,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return
        self.transmit(packet)
        console.concise("Allowent {0}. Do Cookie with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

    def initiate(self):
        '''
        Process initiate packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        data = self.rxPacket.data
        body = self.rxPacket.body.data

        if not isinstance(body, basestring):
            emsg = "Invalid format of initiate packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        if len(body) != raeting.INITIATE_PACKER.size:
            emsg = "Invalid length of initiate packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        shortraw, oreo, cipher, nonce = raeting.INITIATE_PACKER.unpack(body)

        if shortraw != self.remote.publee.keyraw:
            emsg = "Mismatch of short term public key in initiate packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        if (binascii.hexlify(oreo) != self.oreo):
            emsg = "Stale or invalid cookie in initiate packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        msg = self.remote.privee.decrypt(cipher, nonce, self.remote.publee.key)
        if len(msg) != raeting.INITIATESTUFF_PACKER.size:
            emsg = "Invalid length of initiate stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        pubraw, vcipher, vnonce, fqdn = raeting.INITIATESTUFF_PACKER.unpack(msg)
        if pubraw != self.remote.pubber.keyraw:
            emsg = "Mismatch of long term public key in initiate stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        fqdn = fqdn.rstrip(' ')
        lfqdn = self.stack.local.fqdn
        if isinstance(lfqdn, unicode):
            lfqdn = lfqdn.encode('ascii', 'ignore')
        lfqdn = lfqdn.ljust(128, ' ')[:128].rstrip(' ')
        if fqdn != lfqdn:
            emsg = "Mismatch of fqdn in initiate stuff\n"
            console.terse(emsg)
            #self.stack.incStat('invalid_initiate')
            #self.remove()
            #self.nack(kind=raeting.pcktKinds.reject)
            #return

        vouch = self.stack.local.priver.decrypt(vcipher, vnonce, self.remote.pubber.key)
        if vouch != self.remote.publee.keyraw or vouch != shortraw:
            emsg = "Short term key vouch failed\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            #self.remove()
            self.nack(kind=raeting.pcktKinds.reject)
            return

        self.ackInitiate()

    def ackInitiate(self):
        '''
        Send ack to initiate request
        '''

        body = ""
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.ack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        self.transmit(packet)
        console.concise("Allowent {0}. Do Ack Initiate with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

        self.allow()

    def allow(self):
        '''
        Perform allowment
        '''
        self.remote.allowed = True
        self.remote.nextSid() # start new session always on successful allow
        self.remote.replaceStaleInitiators()
        self.stack.dumpRemote(self.remote)

    def final(self):
        '''
        Process ackFinal packet
        So that both sides are waiting on acks at the end so does not restart
        transaction if ack initiate is dropped
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remove()
        console.concise("Allowent {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("allow_correspond_complete")
        self.remote.sendSavedMessages() # could include messages saved on rejoin

    def refuse(self):
        '''
        Process nack refuse packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remove()
        console.concise("Allowent {0}. Refused by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.allowed = False
        self.remove()
        console.concise("Allowent {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to terminate allow transaction
        '''
        body = ""
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        if kind==raeting.pcktKinds.refuse:
            console.terse("Allowent {0}. Do Nack Refuse of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind==raeting.pcktKinds.reject:
            console.concise("Allowent {0}. Do Nack Reject {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind==raeting.pcktKinds.unjoined:
            console.concise("Allowent {0}. Do Nack Unjoined {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Allowent {0}. Do Nack of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        else:
            console.terse("Allowent {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack

        self.remove()
        self.transmit(packet)
        self.stack.incStat(self.statKey())

class Aliver(Initiator):
    '''
    RAET protocol Aliver Initiator class Dual of Alivent
    Sends keep alive heatbeat messages to detect presence


    update alived status of .remote
    only use .remote.refresh to update

    '''
    Timeout = 2.0
    RedoTimeoutMin = 0.25 # initial timeout
    RedoTimeoutMax = 1.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None,
                cascade=False, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.alive
        super(Aliver, self).__init__(**kwa)

        self.cascade = cascade

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.sid = self.remote.sid
        self.tid = self.remote.nextTid()
        self.prep() # prepare .txData

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Aliver, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Aliver, self).receive(packet)

        if packet.data['tk'] == raeting.trnsKinds.alive:
            if packet.data['pk'] == raeting.pcktKinds.ack:
                self.complete()
            elif packet.data['pk'] == raeting.pcktKinds.nack: # refused
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: # refused
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.unjoined: # unjoin
                self.unjoin()
            elif packet.data['pk'] == raeting.pcktKinds.unallowed: # unallow
                self.unallow()
            elif packet.data['pk'] == raeting.pcktKinds.reject: # rejected
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            console.concise("Aliver {0}. Timed out with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
            self.remove()
            self.remote.refresh(alived=False) # mark as dead
            return

        # need keep sending message until completed or timed out
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            if self.txPacket:
                if self.txPacket.data['pk'] == raeting.pcktKinds.request:
                    self.transmit(self.txPacket) # redo
                    console.concise("Aliver {0}. Redo with {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_alive')

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( #sh=self.stack.local.ha[0],
                            #sp=self.stack.local.ha[1],
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def alive(self, body=None):
        '''
        Send message
        '''
        if not self.remote.joined:
            emsg = "Aliver {0}. Must be joined with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_remote')
            self.stack.join(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)
            return

        if not self.remote.allowed:
            emsg = "Aliver {0}. Must be allowed with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_remote')
            self.stack.allow(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)
            return

        self.remote.refresh(alived=None) #Restart timer but do not change alived status
        self.add()

        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.request,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return
        self.transmit(packet)
        console.concise("Aliver {0}. Do Alive with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

    def complete(self):
        '''
        Process ack packet. Complete transaction and remove
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=True) # restart timer mark as alive
        self.remove()
        console.concise("Aliver {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("alive_complete")

    def refuse(self):
        '''
        Process nack refuse packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=None) # restart timer do not change status
        self.remove()
        console.concise("Aliver {0}. Refused by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def reject(self):
        '''
        Process nack reject packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=False) # restart timer set status to False
        self.remove()
        console.concise("Aliver {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def unjoin(self):
        '''
        Process unjoin packet
        terminate in response to unjoin
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=None) # restart timer do not change status
        self.remote.joined = False
        self.remove()
        console.concise("Aliver {0}. Refused unjoin by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)

    def unallow(self):
        '''
        Process unallow nack packet
        terminate in response to unallow
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=None) # restart timer do not change status
        self.remote.allowed = False
        self.remove()
        console.concise("Aliver {0}. Refused unallow by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.allow(uid=self.remote.uid, cascade=self.cascade, timeout=self.timeout)

class Alivent(Correspondent):
    '''
    RAET protocol Alivent Correspondent class Dual of Aliver
    Keep alive heartbeat
    '''
    Timeout = 10.0

    def __init__(self, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.alive
        super(Alivent, self).__init__(**kwa)

        self.prep() # prepare .txData

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Alivent, self).receive(packet)

        if packet.data['tk'] == raeting.trnsKinds.alive:
            if packet.data['pk'] == raeting.pcktKinds.request:
                self.alive()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack() #manage restarts alive later
            console.concise("Alivent {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( #sh=self.stack.local.ha[0],
                            #sp=self.stack.local.ha[1],
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def alive(self):
        '''
        Process alive packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        if not self.remote.joined:
            self.remote.refresh(alived=None) # received signed packet so its alive
            emsg = "Alivent {0}. Must be joined with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_alive_attempt')
            self.nack(kind=raeting.pcktKinds.unjoined)
            return

        if not self.remote.allowed:
            self.remote.refresh(alived=None) # received signed packet so its alive
            emsg = "Alivent {0}. Must be allowed with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_alive_attempt')
            self.nack(kind=raeting.pcktKinds.unallowed)
            return

        self.add()

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.ack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(index=self.rxPacket.index)
            return

        self.transmit(packet)
        console.concise("Alivent {0}. Do ack alive with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.remote.refresh(alived=True)
        self.remove()
        console.concise("Alivent {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("alive_complete")

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to terminate alive transaction
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=kind,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        if kind == raeting.pcktKinds.refuse:
                console.terse("Alivent {0}. Do Refuse of {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.unjoined:
                console.terse("Alivent {0}. Do Unjoined of {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.unallowed:
                console.terse("Alivent {0}. Do Unallowed of {1} at {2}\n".format(
                        self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.reject:
            console.concise("Alivent {0}. Do Reject {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        elif kind == raeting.pcktKinds.nack:
            console.terse("Alivent {0}. Do Nack of {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
        else:
            console.terse("Alivent {0}. Invalid nack kind of {1} nacking anyway "
                    " at {2}\n".format(self.stack.name,
                                       kind,
                                       self.stack.store.stamp))
            kind == raeting.pcktKinds.nack

        self.transmit(packet)
        self.remove()

        self.stack.incStat(self.statKey())

class Messenger(Initiator):
    '''
    RAET protocol Messenger Initiator class Dual of Messengent
    Generic messages
    '''
    Timeout = 0.0
    RedoTimeoutMin = 1.0 # initial timeout
    RedoTimeoutMax = 3.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.message
        super(Messenger, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.sid = self.remote.sid
        self.tid = self.remote.nextTid()
        self.prep() # prepare .txData
        self.tray = packeting.TxTray(stack=self.stack)

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Messenger, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Messenger, self).receive(packet)

        if packet.data['tk'] == raeting.trnsKinds.message:
            if packet.data['pk'] == raeting.pcktKinds.ack:
                self.another()
            elif packet.data['pk'] == raeting.pcktKinds.nack: # rejected
                self.reject()
            elif packet.data['pk'] == raeting.pcktKinds.resend: # missed resend
                self.resend()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.remove()
            console.concise("Messenger {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

        # need keep sending message until completed or timed out
        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            if self.txPacket:
                if self.txPacket.data['pk'] == raeting.pcktKinds.message:
                    self.transmit(self.txPacket) # redo
                    console.concise("Messenger {0}. Redo Segment {1} with {2} at {3}\n".format(
                            self.stack.name, self.tray.last, self.remote.name, self.stack.store.stamp))
                    self.stack.incStat('redo_segment')

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( #sh=self.stack.local.ha[0],
                            #sp=self.stack.local.ha[1],
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def message(self, body=None):
        '''
        Send message or part of message. So repeatedly called untill complete
        '''

        if not self.remote.allowed:
            emsg = "Messenger {0}. Must be allowed with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_remote')
            self.remove()
            return

        if not self.tray.packets:
            try:
                self.tray.pack(data=self.txData, body=body)
            except raeting.PacketError as ex:
                console.terse(str(ex) + '\n')
                self.stack.incStat("packing_error")
                self.remove()
                return

        if self.tray.current >= len(self.tray.packets):
            emsg = "Messenger {0}. Current packet {1} greater than num packets {2}\n".format(
                                self.stack.name, self.tray.current, len(self.tray.packets))
            console.terse(emsg)
            self.remove()
            return

        if self.index not in self.remote.transactions:
            self.add()
        elif self.remote.transactions[self.index] != self:
            emsg = "Messenger {0}. Remote {1} Index collision at {2}\n".format(
                                self.stack.name, self.remote.name,  self.index)
            console.terse(emsg)
            self.incStat('message_index_collision')
            self.remove()
            return

        burst = 1 if self.wait else len(self.tray.packets) - self.tray.current

        for packet in self.tray.packets[self.tray.current:self.tray.current + burst]:
            self.transmit(packet) #if self.tray.current %  2 else None
            self.tray.last = self.tray.current
            self.stack.incStat("message_segment_tx")
            console.concise("Messenger {0}. Do Message Segment {1} with {2} at {3}\n".format(
                    self.stack.name, self.tray.last, self.remote.name, self.stack.store.stamp))
            self.tray.current += 1

    def another(self):
        '''
        Process ack packet send next one
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.refresh(alived=True)

        if self.tray.current >= len(self.tray.packets):
            self.complete()
        else:
            self.message()

    def resend(self):
        '''
        Process resend packet and send misseds list of missing packets
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.refresh(alived=True)

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        misseds = body.get('misseds')
        if misseds:
            if not self.tray.packets:
                emsg = "Invalid resend request '{0}'\n".format(misseds)
                console.terse(emsg)
                self.stack.incStat('invalid_resend')
                return

            for m in misseds:
                try:
                    packet = self.tray.packets[m]
                except IndexError as ex:
                    #console.terse(str(ex) + '\n')
                    console.terse("Invalid misseds segment number {0}\n".format(m))
                    self.stack.incStat("invalid_misseds")
                    return

                self.transmit(packet)
                self.stack.incStat("message_segment_tx")
                console.concise("Messenger {0}. Resend Message Segment {1} with {2} at {3}\n".format(
                        self.stack.name, m, self.remote.name, self.stack.store.stamp))

    def complete(self):
        '''
        Complete transaction and remove
        '''
        self.remove()
        console.concise("Messenger {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("message_initiate_complete")

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.refresh(alived=True)

        self.remove()
        console.concise("Messenger {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def nack(self):
        '''
        Send nack to terminate transaction
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.nack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        self.transmit(packet)
        self.remove()
        console.concise("Messenger {0}. Do Reject {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

class Messengent(Correspondent):
    '''
    RAET protocol Messengent Correspondent class Dual of Messenger
    Generic Messages
    '''
    Timeout = 0.0
    RedoTimeoutMin = 1.0 # initial timeout
    RedoTimeoutMax = 3.0 # max timeout

    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.message
        super(Messengent, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        self.prep() # prepare .txData
        self.tray = packeting.RxTray(stack=self.stack)

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Messengent, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Messengent, self).receive(packet)

        # resent message
        if packet.data['tk'] == raeting.trnsKinds.message:
            if packet.data['pk'] == raeting.pcktKinds.message:
                self.message()
            elif packet.data['pk'] == raeting.pcktKinds.nack: # rejected
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack()
            console.concise("Messengent {0}. Timed out with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
            return

        if self.redoTimer.expired:
            duration = min(
                         max(self.redoTimeoutMin,
                              self.redoTimer.duration * 2.0),
                         self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)

            misseds = self.tray.missing()
            if misseds:
                self.resend(misseds)

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( #sh=self.stack.local.ha[0],
                            #sp=self.stack.local.ha[1],
                            dh=self.remote.ha[0], # maybe needed for index
                            dp=self.remote.ha[1], # maybe needed for index
                            se=self.remote.nuid,
                            de=self.remote.fuid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def message(self):
        '''
        Process message packet. Called repeatedly for each packet in message
        '''
        if not self.remote.allowed:
            emsg = "Messengent {0}. Must be allowed with {1} first\n".format(
                    self.stack.name,  self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_message_attempt')
            self.nack()
            return

        try:
            body = self.tray.parse(self.rxPacket)
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_message_error')
            self.nack()
            return

        if self.index not in self.remote.transactions:
            self.add()
        elif self.remote.transactions[self.index] != self:
            emsg = "Messengent {0}. Remote {1} Index collision at {2}\n".format(
                                self.stack.name, self.remote.name, self.index)
            console.terse(emsg)
            self.incStat('message_index_collision')
            self.nack()
            return

        self.remote.refresh(alived=True)

        self.stack.incStat("message_segment_rx")

        if self.tray.complete:
            self.ackMessage()
            console.verbose("{0} received message body\n{1}\n".format(
                    self.stack.name, body))
            # application layer authorizaiton needs to know who sent the message
            self.stack.rxMsgs.append((body, self.remote.name))
            self.complete()

        elif self.wait:
            self.ackMessage()

        else:
            misseds = self.tray.missing(begin=self.tray.prev, end=self.tray.last)
            if misseds:
                self.resend(misseds)

    def ackMessage(self):
        '''
        Send ack to message
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.ack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return
        self.transmit(packet)
        self.stack.incStat("message_segment_ack")
        console.concise("Messengent {0}. Do Ack Segment {1} with {2} at {3}\n".format(
                self.stack.name, self.tray.last, self.remote.name, self.stack.store.stamp))

    def resend(self, misseds):
        '''
        Send resend request(s) for missing packets
        '''
        while misseds:
            if len(misseds) > 64:
                remainders = misseds[64:] # only do at most 64 at a time
                misseds = misseds[:64]
            else:
                remainders = []

            body = odict(misseds=misseds)
            packet = packeting.TxPacket(stack=self.stack,
                                        kind=raeting.pcktKinds.resend,
                                        embody=body,
                                        data=self.txData)
            try:
                packet.pack()
            except raeting.PacketError as ex:
                console.terse(str(ex) + '\n')
                self.stack.incStat("packing_error")
                self.remove()
                return
            self.transmit(packet)
            self.stack.incStat("message_resend")
            console.concise("Messengent {0}. Do Resend Segments {1} with {2} at {3}\n".format(
                    self.stack.name, misseds, self.remote.name, self.stack.store.stamp))
            misseds = remainders

    def complete(self):
        '''
        Complete transaction and remove
        '''
        self.remove()
        console.concise("Messengent {0}. Complete with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("messagent_correspond_complete")

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remote.refresh(alived=True)

        self.remove()
        console.concise("Messengent {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def nack(self):
        '''
        Send nack to terminate messenger transaction
        '''
        body = odict()
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.nack,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove()
            return

        self.transmit(packet)
        self.remove()
        console.concise("Messagent {0}. Do Reject {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

