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

        self.rmt = rmt # cf flag
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
        '''
        le = self.stack.local.uid
        if le == 0: # bootstrapping onto channel use ha
            le = self.stack.local.ha
        re = self.remote.uid
        if re == 0: # bootstrapping onto channel use ha from zeroth remote
            re = self.stack.remotes[0].ha
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
            self.remove(packet.index)
            return
        self.txPacket = packet

    def add(self, index=None):
        '''
        Add self to stack transactions
        '''
        if not index:
            index = self.index
        self.stack.addTransaction(index, self)

    def remove(self, index=None):
        '''
        Remove self from stack transactions
        '''
        if not index:
            index = self.index
        self.stack.removeTransaction(index, transaction=self)

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
        kwa['rmt'] = False  # force rmt to False
        super(Initiator, self).__init__(**kwa)

    def process(self):
        '''
        Process time based handling of transaction like timeout or retries
        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.stack.removeTransaction(self.index, transaction=self)

class Correspondent(Transaction):
    '''
    RAET protocol correspondent transaction class
    '''
    Requireds = ['sid', 'tid', 'rxPacket']

    def __init__(self, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['rmt'] = True  # force rmt to True

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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.rxPacket.data['sh'],
                            dp=self.rxPacket.data['sp'],
                            se=self.stack.local.uid,
                            de=self.rxPacket.data['se'],
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada)

    def nack(self):
        '''
        Send nack to stale packet from correspondent.
        This is used when a correspondent packet is received but no matching
        Initiator transaction is found. So create a dummy initiator and send
        a nack packet back. Do not add transaction so don't need to remove it.
        '''
        ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])
        emsg = "{0} Stale Transaction from {1} dropping ...\n".format(self.stack.name, ha )
        console.terse(emsg)
        self.stack.incStat('stale_correspondent_attempt')

        if self.rxPacket.data['se'] not in self.stack.remotes:
            emsg = "Unknown correspondent estate id '{0}'\n".format(self.rxPacket.data['se'])
            console.terse(emsg)
            self.stack.incStat('unknown_correspondent_eid')
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
        console.terse("Nack stale correspondent at {0}\n".format(self.stack.store.stamp))
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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.rxPacket.data['sh'],
                            dp=self.rxPacket.data['sp'],
                            se=self.stack.local.uid,
                            de=self.rxPacket.data['se'],
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada)

    def nack(self):
        '''
        Send nack to stale packet from initiator.
        This is used when a initiator packet is received but with a stale session id
        So create a dummy correspondent and send a nack packet back.
        Do not add transaction so don't need to remove it.
        '''
        ha = (self.rxPacket.data['sh'], self.rxPacket.data['sp'])
        emsg = "{0} Stale Transaction from {1} dropping ...\n".format(self.stack.name, ha )
        console.terse(emsg)
        self.stack.incStat('stale_initiator_attempt')

        if self.rxPacket.data['se'] not in self.stack.remotes:
            emsg = "Unknown initiator estate id '{0}'\n".format(self.rxPacket.data['se'])
            console.terse(emsg)
            self.stack.incStat('unknown_initiator_eid')
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
        console.terse("Nack stale initiator at {0}\n".format(self.stack.store.stamp))
        self.stack.incStat('stale_initiator_nack')

class Joiner(Initiator):
    '''
    RAET protocol Joiner Initiator class Dual of Joinent
    '''
    RedoTimeoutMin = 1.0 # initial timeout
    RedoTimeoutMax = 4.0 # max timeout


    def __init__(self, redoTimeoutMin=None, redoTimeoutMax=None,
                 cascade=False, **kwa):
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

        self.sid = self.remote.sid # 0
        self.tid = self.remote.nextTid()
        self.prep()
        # don't dump remote yet since its ephemeral until we join and get valid eid

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Joiner, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Joiner, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.join:
            if packet.data['pk'] == raeting.pcktKinds.ack: # maybe pending
                self.pend()
            elif packet.data['pk'] == raeting.pcktKinds.response:
                self.accept()
            elif packet.data['pk'] == raeting.pcktKinds.nack: #rejected
                self.reject()
            elif packet.data['pk'] == raeting.pcktKinds.renew: #renew
                self.renew()
            elif packet.data['pk'] == raeting.pcktKinds.refuse: #refused
                self.refuse()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            if self.txPacket and self.txPacket.data['pk'] == raeting.pcktKinds.request:
                self.remove(self.txPacket.index) #index changes after accept
            else:
                self.remove(self.index) # in case never sent txPacket

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
                self.transmit(self.txPacket) #redo
                console.concise("Joiner {0}. Redo Join with {1} at {2}\n".format(
                         self.stack.name, self.remote.name, self.stack.store.stamp))
                self.stack.incStat('redo_join')
            else: #check to see if status has changed to accept after other kind
                if self.local.main: #only if joiner initiated by main stack
                    if self.remote:
                        data = self.stack.safe.loadRemote(self.remote)
                        if data:
                            status = self.stack.safe.statusRemote(self.remote,
                                                                  data['verhex'],
                                                                  data['pubhex'],
                                                                  main=self.stack.local.main)
                            if status == raeting.acceptances.accepted:
                                self.join() # trigger remote to resend accept packet
                            elif status == raeting.acceptances.rejected:
                                "Stack {0}: Estate '{1}' eid '{2}' keys rejected\n".format(
                                    self.stack.name, self.remote.name, self.remote.uid)
                                self.remote.joined = False
                                self.nackAccept()


    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,
                            ck=raeting.coatKinds.nada,
                            fk=raeting.footKinds.nada)

    def join(self):
        '''
        Send join request
        '''
        if self.remote and self.remote.joinInProcess() and self.stack.local.main:
            emsg = "Joiner {0}. Join with {1} already in process\n".format(
                    self.stack.name, self.remote.name)
            console.concise(emsg)
            return

        self.remote.joined = None
        self.add(self.index)
        body = odict([('name', self.stack.local.name),
                      ('verhex', self.stack.local.signer.verhex),
                      ('pubhex', self.stack.local.priver.pubhex)])
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

    def renew(self):
        '''
        Reset to vacuous Road data and try joining again
        '''
        if self.stack.local.main: # main never renews so just reject
            self.reject()
            return

        who = (self.remote.name if self.remote else
                 (self.rxPacket.data['sh'], self.rxPacket.data['sp']))
        console.terse("Joiner {0}. Renew from {1} at {2}\n".format(
                self.stack.name, who, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        if self.remote: # this forces sid to 0 since new remote defaults sid to 0
            self.stack.removeRemote(self.remote.uid)
        self.stack.local.eid = 0
        self.stack.dumpLocal()
        self.remove(self.txPacket.index)
        self.stack.join(ha=self.remote.ha, timeout=0.0)

    def pend(self):
        '''
        Process ack to join packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        pass

    def accept(self):
        '''
        Perform acceptance in response to join response packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        data = self.rxPacket.data
        body = self.rxPacket.body.data

        leid = body.get('leid')
        if not leid: # None or zero
            emsg = "Missing or invalid local estate id in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        reid = body.get('reid')
        if not reid: # None or zero
            emsg = "Missing or invalid remote estate id in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        name = body.get('name')
        if not name:
            emsg = "Missing remote name in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        verhex = body.get('verhex')
        if not verhex:
            emsg = "Missing remote verifier key in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        pubhex = body.get('pubhex')
        if not pubhex:
            emsg = "Missing remote crypt key in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        # we are assuming for now that the joiner cannot talk peer to peer only
        # to main estate otherwise we need to ensure unique eid, name, and ha on road

        # check if remote keys are accepted here
        status = self.stack.safe.statusRemote(self.remote,
                                              verhex=verhex,
                                              pubhex=pubhex,
                                              main=self.stack.local.main)

        if status == raeting.acceptances.rejected:
            self.remote.joined = False
            self.nackAccept()
            return

        if self.stack.local.main: # only if main
            if status == raeting.acceptances.pending: # pending so ignore
                return # forces retry of accept packet so may be accepted later

        else: #not main
            if self.remote.uid != reid: #change id of remote estate
                try:
                    self.stack.moveRemote(old=self.remote.uid, new=reid)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.txPacket.index)
                    return

            if self.remote.name != name: # rename remote estate to new name
                try:
                    self.stack.renameRemote(old=self.remote.name, new=name)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.txPacket.index)
                    return

            if self.stack.local.uid != leid:
                self.stack.local.uid = leid # change id of local estate
                self.stack.dumpLocal() # only dump if changed


        self.remote.replaceStaleInitiators(renew=(self.sid==0))
        self.remote.nextSid() # start new session
        self.stack.dumpRemote(self.remote)
        self.remote.joined = True #accepted

        self.ackAccept()

    def refuse(self):
        '''
        Process nack to join packet refused as join already in progress
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        console.terse("Joiner {0}. Refused by {1} at {2}\n".format(
                 self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remove(self.txPacket.index)

    def reject(self):
        '''
        Process nack to join packet, join rejected
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        console.terse("Joiner {0}. Rejected by {1} at {2}\n".format(
                 self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.remote.joined = False
        self.stack.removeRemote(self.remote.uid)
        self.remove(self.txPacket.index)

    def ackAccept(self):
        '''
        Send ack to accept response
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
            self.remove(self.txPacket.index)
            return

        console.concise("Joiner {0}. Do Accept of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("join_initiate_complete")

        self.transmit(packet)
        self.remove(self.rxPacket.index)

        if self.cascade:
            self.stack.allow(duid=self.remote.uid, cascade=self.cascade)

    def nackAccept(self):
        '''
        Send nack to accept response
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
            self.remove(self.txPacket.index)
            return

        console.terse("Joiner {0}. Do Reject of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.transmit(packet)
        self.remove(self.txPacket.index)

class Joinent(Correspondent):
    '''
    RAET protocol Joinent transaction class, dual of Joiner
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

        self.prep()

    def transmit(self, packet):
        '''
        Augment transmit with restart of redo timer
        '''
        super(Joinent, self).transmit(packet)
        self.redoTimer.restart()

    def receive(self, packet):
        """
        Process received packet belonging to this transaction
        """
        super(Joinent, self).receive(packet) #  self.rxPacket = packet

        if packet.data['tk'] == raeting.trnsKinds.join:
            if packet.data['pk'] == raeting.pcktKinds.ack: #accepted by joiner
                self.complete()
            elif packet.data['pk'] == raeting.pcktKinds.nack: #rejected
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack()
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
                    self.txPacket.data['pk'] == raeting.pcktKinds.response): #accept packet
                self.transmit(self.txPacket) #redo
                console.concise("Joinent {0}. Redo Accept with {1} at {2}\n".format(
                    self.stack.name, self.remote.name, self.stack.store.stamp))
                self.stack.incStat('redo_accept')
            else: #check to see if status has changed to accept after other kind
                if self.remote:
                    data = self.stack.safe.loadRemote(self.remote)
                    if data:
                        status = self.stack.safe.statusRemote(self.remote,
                                                              data['verhex'],
                                                              data['pubhex'],
                                                              main=self.stack.local.main)
                        if status == raeting.acceptances.accepted:
                            self.accept()
                        elif status == raeting.acceptances.rejected:
                            "Stack {0}: Estate '{1}' eid '{2}' keys rejected\n".format(
                                    self.stack.name, self.remote.name, self.remote.uid)
                            self.stack.removeRemote(self.remote.uid) #reap remote
                            self.nack()

    def prep(self):
        '''
        Prepare .txData
        '''
        #since bootstrap transaction use the reversed seid and deid from packet
        self.txData.update(sh=self.stack.local.host,
                           sp=self.stack.local.port,
                           se=self.rxPacket.data['de'],
                           de=self.rxPacket.data['se'],
                           tk=self.kind,
                           cf=self.rmt,
                           bf=self.bcst,
                           wf=self.wait,
                           si=self.sid,
                           ti=self.tid,
                           ck=raeting.coatKinds.nada,
                           fk=raeting.footKinds.nada,)

    def join(self):
        '''
        Process join packet
        Respond based on acceptance status of remote estate.

        Rules for Colliding Estates
        Apply the rules to ensure no colliding estates on (host, port)
        If matching name estate found then return
        Rules:
            Only one estate with given eid is allowed on road
            Only one estate with given name is allowed on road.
            Only one estate with given ha is allowed on road.

            Are multiple estates with same keys but different name (ha) allowed?
            Current logic ignores same keys or not

        Since creating new estate assigns unique eid,
        we are looking for preexisting estates with any eid.

        Processing steps:
        I) Search remote estates for matching name
            A) Found remote
                1) HA not match
                    Search remotes for other matching HA but different name
                    If found other delete
                Reuse found remote to be updated and joined

            B) Not found
                Search remotes for other matching HA
                If found delete for now
                Create new remote and update
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        if self.remote and self.remote.joinInProcess() and not self.stack.local.main:
            emsg = "Joinent {0}. Join with {1} already in process\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('duplicate_join_attempt')
            self.nack(kind=raeting.pcktKinds.refuse)
            return

        #Don't add transaction yet wait till later until remote is not rejected
        data = self.rxPacket.data
        body = self.rxPacket.body.data

        name = body.get('name')
        if not name:
            emsg = "Missing remote name in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(self.rxPacket.index)
            return

        verhex = body.get('verhex')
        if not verhex:
            emsg = "Missing remote verifier key in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(self.rxPacket.index)
            return

        pubhex = body.get('pubhex')
        if not pubhex:
            emsg = "Missing remote crypt key in join packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_join')
            self.remove(self.rxPacket.index)
            return

        host = data['sh']
        port = data['sp']
        self.txData.update( dh=host, dp=port,) # responses use received host port

        reid = data['se']
        leid = data['de']

        if self.stack.local.main:
            if ((leid != 0 and leid != self.stack.local.uid)):
                emsg = "Estate '{0}' renew stale main leid '{1}'\n".format(
                                            name, leid)
                console.terse(emsg)
                self.nack(kind=raeting.pcktKinds.renew) # refuse and renew
                return

            elif (reid != 0 and reid not in self.stack.remotes):
                remote = self.stack.restoreRemote(reid) # see if still on disk
                if not remote:
                    emsg = "Estate '{0}' renew stale reid '{1}'\n".format(
                                                name, reid)
                    console.terse(emsg)
                    self.nack(kind=raeting.pcktKinds.renew) # refuse and renew
                    return
                self.remote = remote

            if reid != 0:
                if self.remote is None:
                    self.remote = self.stack.remotes[reid]
                if name != self.remote.name:
                    if (verhex != self.remote.verfer.keyhex or
                            pubhex != self.remote.pubber.keyhex):
                        emsg = "Estate '{0}' name key mismatch\n".format(name)
                        console.terse(emsg)
                        self.nack() #reject not the same estate because keys not match
                        return
                    else: # check new name unique
                        if name in self.stack.uids:
                            emsg = "Estate '{0}' name unavailable\n".format(name)
                            console.terse(emsg)
                            self.nack() # reject as name already in use by another estate
                            return

                if (host != self.remote.host or port != self.remote.port):
                    if (verhex != self.remote.verfer.keyhex or
                            pubhex != self.remote.pubber.keyhex):
                        emsg = "Estate '{0}' name ha '{1}' mismatch\n".format(
                                name, str((host, port)))
                        console.terse(emsg)
                        self.nack() #reject not the same estate because keys not match
                        return
                    else: # check new (host, port) unique
                        if self.stack.fetchRemoteByHostPort(host, port):
                            emsg = "Estate '{0}' ha '{1}' unavailable\n".format(
                                                            name,  str((host, port)))
                            console.terse(emsg)
                            self.nack() #reject as (host, port) already in use by another estate
                            return
                            # this may go to the wrong estate since potential ambiguous udp
                            # channel but in any event the transaction will fail

                status = self.stack.safe.statusRemote(self.remote,
                                                      verhex=verhex,
                                                      pubhex=pubhex,
                                                      main=self.stack.local.main)

                if status == raeting.acceptances.rejected:
                    "Estate '{0}' eid '{1}' keys rejected\n".format(
                            name, self.remote.uid)
                    self.stack.removeRemote(self.remote.uid) #reap remote
                    self.nack() # reject as keys rejected
                    return

                self.remote.host = host
                self.remote.port = port
                self.remote.rsid = self.sid # fix this?
                if name != self.remote.name:
                    self.stack.renameRemote(old=self.remote.name, new=name)

            else: # reid == 0
                if not self.stack.local.main: #not main so can't process vacuous join
                    emsg = "Estate '{0}' eid '{1}' not joinable\n".format(name, reid)
                    console.terse(emsg)
                    self.nack()
                    return

                remote = self.stack.fetchRemoteByName(name)
                if remote: # remote with same name is it the same one
                    if (verhex != remote.verfer.keyhex or
                            pubhex != remote.pubber.keyhex): # not same remote
                        emsg = "Estate '{0}' name unavailable\n".format(name)
                        console.terse(emsg)
                        self.remote = None
                        self.nack()
                        return

                other = self.stack.fetchRemoteByHostPort(host, port)
                if other and other is not remote: # (host, port) already in use by another estate
                    emsg = "Estate '{0}' ha '{1}' unavailable\n".format(
                                                    name,  str((host, port)))
                    console.terse(emsg)
                    self.remote = None
                    self.nack()
                    return

                if not remote:
                    remote = estating.RemoteEstate(stack=self.stack,
                                                   name=name,
                                                   host=host,
                                                   port=port,
                                                   acceptance=None,
                                                   verkey=verhex,
                                                   pubkey=pubhex,
                                                   rsid=self.sid,
                                                   period=self.stack.period,
                                                   offset=self.stack.offset,)

                    try:
                        self.stack.addRemote(remote) #provisionally add .accepted is None
                    except raeting.StackError as ex:
                        console.terse(str(ex) + '\n')
                        self.stack.incStat(self.statKey())
                        self.remove(self.rxPacket.index)
                        return

                self.remote = remote # auto generated at instance creation above

                status = self.stack.safe.statusRemote(self.remote,
                                                      verhex=verhex,
                                                      pubhex=pubhex,
                                                      main=self.stack.local.main)

                if status == raeting.acceptances.rejected:
                    emsg = "Estate '{0}' eid '{1}' keys rejected\n".format(
                            name, self.remote.uid)
                    console.terse(emsg)
                    self.stack.removeRemote(self.remote.uid) #reap remote
                    self.nack() # reject as keys rejected
                    return

            self.add(self.rxPacket.index) # bootstrap so use packet.index not self.index
            self.stack.dumpRemote(self.remote)

            if status == raeting.acceptances.accepted:
                self.remote.joined = None
                duration = min(
                                max(self.redoTimeoutMin,
                                  self.redoTimer.duration * 2.0),
                                self.redoTimeoutMax)
                self.redoTimer.restart(duration=duration)
                self.accept()
            else: # status == None or status == raeting.acceptances.pending:
                self.remote.joined = None
                self.ackJoin()

        else: # not main stack
            if leid == 0 or reid == 0: #not main so can't process vacuous join
                emsg = ("Estate '{0}' not main, invalid leid '{1}' or "
                        "reid '{2}' from '{3}'\n".format(self.stack.local.name,
                                                         leid, reid, name))
                console.terse(emsg)
                self.remote = None
                self.nack()
                return
            if self.stack.remotes: # already a main since remotes
                if not self.remote: # but reid not from preexisting main
                    emsg = ("Estate '{0}': Received join attempt from non primary "
                            "main remote '{1}'\n".format(self.stack.local.name, name))
                    console.terse(emsg)
                    self.nack(self.nack(kind=raeting.pcktKinds.refuse))
                    return

            else: # no remotes so could be initial join from main
                self.remote = estating.RemoteEstate(stack=self.stack,
                                               eid=reid,
                                               name=name,
                                               host=host,
                                               port=port,
                                               acceptance=None,
                                               verkey=verhex,
                                               pubkey=pubhex,
                                               rsid=self.sid,
                                               period=self.stack.period,
                                               offset=self.stack.offset,)
                try:
                    self.stack.addRemote(self.remote) #provisionally add .acceptance is None
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.rxPacket.index)
                    return

            self.add(self.rxPacket.index) # bootstrap so use packet.index not self.index
            status = self.stack.safe.statusRemote(self.remote,
                                                  verhex=verhex,
                                                  pubhex=pubhex,
                                                  main=self.stack.local.main)

            if status == raeting.acceptances.rejected:
                "Estate '{0}' eid '{1}' keys rejected\n".format(
                        name, remote.uid)
                self.stack.removeRemote(self.remote.uid) #reap remote
                self.nack() # reject as keys rejected
                return

            if self.stack.local.uid != leid:
                self.stack.local.uid = leid  # change local eid
                self.stack.dumpLocal()

            self.remote.rsid = self.sid # fix this ?
            self.remote.host = host
            self.remote.port = port
            if name != self.remote.name:
                self.stack.renameRemote(old=self.remote.name, new=name)
            #remote.nextSid() #set in complete method

            # we only want to dump once so should we wait until complete
            #self.stack.dumpRemote(self.remote)
            #remote.joined = True #accepted set in complete method
            duration = min(
                        max(self.redoTimeoutMin,
                             self.redoTimer.duration * 2.0),
                        self.redoTimeoutMax)
            self.redoTimer.restart(duration=duration)
            self.accept()

    def ackJoin(self):
        '''
        Send ack to join request
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
            self.remove(self.rxPacket.index)
            return

        console.concise("Joinent {0}. Pending Accept of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.transmit(packet)

    def accept(self):
        '''
        Send accept response to join request
        '''
        body = odict([ ('leid', self.remote.uid),
                       ('reid', self.stack.local.uid),
                       ('name', self.stack.local.name),
                       ('verhex', self.stack.local.signer.verhex),
                       ('pubhex', self.stack.local.priver.pubhex)])
        packet = packeting.TxPacket(stack=self.stack,
                                    kind=raeting.pcktKinds.response,
                                    embody=body,
                                    data=self.txData)
        try:
            packet.pack()
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.stack.incStat("packing_error")
            self.remove(self.rxPacket.index)
            return

        console.concise("Joinent {0}. Do Accept of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.transmit(packet)

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to join request.
        Sometimes nack occurs without remote being added so have to nack using ha.
        '''
        ha = None
        if not self.remote or self.remote.uid not in self.stack.remotes:
            self.txData.update( dh=self.rxPacket.data['sh'], dp=self.rxPacket.data['sp'],)
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
            self.remove(self.rxPacket.index)
            return

        if kind == raeting.pcktKinds.renew:
            console.terse("Joinent {0}. Renew '{1}' at {2}\n".format(
                            self.stack.name, ha, self.stack.store.stamp))
        elif kind==raeting.pcktKinds.refuse:
            console.terse("Joinent {0}. Refuse '{1}' at {2}\n".format(
                            self.stack.name, ha, self.stack.store.stamp))
        else:
            console.terse("Joinent {0}. Reject '{1}' at {2}\n".format(
                        self.stack.name, ha, self.stack.store.stamp))

        self.stack.incStat(self.statKey())

        if ha:
            self.stack.txes.append((packet.packed, ha))
        else:
            self.transmit(packet)
        self.remove(self.rxPacket.index)

    def complete(self):
        '''
        process ack to accept response
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        console.terse("Joinent {0}. Done with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("join_correspond_complete")

        self.remote.removeStaleCorrespondents(renew=(self.sid==0))
        self.remote.joined = True # accepted
        self.remote.nextSid()
        self.remote.replaceStaleInitiators()
        self.stack.dumpRemote(self.remote)
        self.remove(self.rxPacket.index)

    def reject(self):
        '''
        Process nack to accept response or stale
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        console.terse("Joinent {0}. Rejected by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

        self.remote.joined = False
        self.stack.dumpRemote(self.remote)
        # use presence to remove remote

        self.remove(self.rxPacket.index)


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
                self.reject()
            elif packet.data['pk'] == raeting.pcktKinds.unjoined: # rejected
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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid, #self.reid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid, )

    def hello(self):
        '''
        Send hello request
        '''
        self.remote.allowed = None
        if not self.remote.joined:
            emsg = "Allower {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_remote')
            self.stack.join(duid=self.remote.uid, cascade=self.cascade)
            return

        if self.remote.allowInProcess() and self.stack.local.main:
            emsg = "Allower {0}. Allow with {1} already in process\n".format(
                    self.stack.name, self.remote.name)
            console.concise(emsg)
            return

        self.remote.rekey() # refresh short term keys and reset .allowed to None
        self.add(self.index)

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
            self.remove()
            return

        if len(body) != raeting.COOKIE_PACKER.size:
            emsg = "Invalid length of cookie packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
            return

        cipher, nonce = raeting.COOKIE_PACKER.unpack(body)

        try:
            msg = self.remote.privee.decrypt(cipher, nonce, self.remote.pubber.key)
        except ValueError as ex:
            emsg = "Invalid cookie stuff: '{0}'\n".format(str(ex))
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
            return

        if len(msg) != raeting.COOKIESTUFF_PACKER.size:
            emsg = "Invalid length of cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
            return

        shortraw, seid, deid, oreo = raeting.COOKIESTUFF_PACKER.unpack(msg)

        if seid != self.remote.uid or deid != self.stack.local.uid:
            emsg = "Invalid seid or deid fields in cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
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

        fqdn = self.remote.fqdn.ljust(128, ' ')

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
        Why do we need this? could we just let transaction timeout on allowent
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
        self.remove()
        console.concise("Allower {0}. Ack Final of {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("allow_initiate_complete")

        self.remote.nextSid() # start new session
        self.remote.replaceStaleInitiators()
        self.stack.dumpRemote(self.remote)
        self.remote.sendSavedMessages() # could include messages saved on rejoin
        if self.cascade:
            self.stack.alive(duid=self.remote.uid, cascade=self.cascade)

    def reject(self):
        '''
        Process nack packet
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
        self.stack.join(duid=self.remote.uid, cascade=self.cascade)

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
                self.reject()

    def process(self):
        '''
        Perform time based processing of transaction

        '''
        if self.timeout > 0.0 and self.timer.expired:
            self.nack()
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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
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

        self.remote.allowed = None

        if not self.remote.joined:
            emsg = "Allowent {0}. Must be joined with {1} first\n".format(
                self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_allow_attempt')
            self.nack(kind=raeting.pcktKinds.unjoined)
            return

        if self.remote.allowInProcess() and not self.stack.local.main:
            emsg = "Allowent {0}. Allow with {1} already in process\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('duplicate_allow_attempt')
            self.nack()
            return

        self.remote.rekey() # refresh short term keys and .allowed
        self.add(self.index)

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        if not isinstance(body, basestring):
            emsg = "Invalid format of hello packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            self.remove()
            return

        if len(body) != raeting.HELLO_PACKER.size:
            emsg = "Invalid length of hello packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            self.remove()
            return

        plain, shortraw, cipher, nonce = raeting.HELLO_PACKER.unpack(body)

        self.remote.publee = nacling.Publican(key=shortraw)
        msg = self.stack.local.priver.decrypt(cipher, nonce, self.remote.publee.key)
        if msg != plain :
            emsg = "Invalid plain not match decrypted cipher\n"
            console.terse(emsg)
            self.stack.incStat('invalid_hello')
            self.remove()
            return

        self.cookie()

    def cookie(self):
        '''
        Send Cookie Packet
        '''
        oreo = self.stack.local.priver.nonce()
        self.oreo = binascii.hexlify(oreo)

        stuff = raeting.COOKIESTUFF_PACKER.pack(self.remote.privee.pubraw,
                                                self.stack.local.uid,
                                                self.remote.uid,
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
            self.remove()
            return

        if len(body) != raeting.INITIATE_PACKER.size:
            emsg = "Invalid length of initiate packet body\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        shortraw, oreo, cipher, nonce = raeting.INITIATE_PACKER.unpack(body)

        if shortraw != self.remote.publee.keyraw:
            emsg = "Mismatch of short term public key in initiate packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        if (binascii.hexlify(oreo) != self.oreo):
            emsg = "Stale or invalid cookie in initiate packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        msg = self.remote.privee.decrypt(cipher, nonce, self.remote.publee.key)
        if len(msg) != raeting.INITIATESTUFF_PACKER.size:
            emsg = "Invalid length of initiate stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        pubraw, vcipher, vnonce, fqdn = raeting.INITIATESTUFF_PACKER.unpack(msg)
        if pubraw != self.remote.pubber.keyraw:
            emsg = "Mismatch of long term public key in initiate stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        fqdn = fqdn.rstrip(' ')
        if fqdn != self.stack.local.fqdn:
            emsg = "Mismatch of fqdn in initiate stuff\n"
            console.terse(emsg)
            #self.stack.incStat('invalid_initiate')
            #self.remove()
            #return

        vouch = self.stack.local.priver.decrypt(vcipher, vnonce, self.remote.pubber.key)
        if vouch != self.remote.publee.keyraw or vouch != shortraw:
            emsg = "Short term key vouch failed\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
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
        console.concise("Allowent {0}. Do Ack with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))

        self.allow()

    def allow(self):
        '''
        Perform allowment
        '''
        self.remote.allowed = True
        self.remote.nextSid() # start new session
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
        console.concise("Allowent {0}. Do Final with {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat("allow_correspond_complete")
        self.remote.sendSavedMessages() # could include messages saved on rejoin

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

        self.transmit(packet)
        self.remove()
        console.concise("Allowent {0}. Reject {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
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
            elif packet.data['pk'] == raeting.pcktKinds.nack: # rejected
                self.refuse()
            elif packet.data['pk'] == raeting.pcktKinds.unjoined: # rejected
                self.unjoin()
            elif packet.data['pk'] == raeting.pcktKinds.unallowed: # rejected
                self.unallow()

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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
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
            self.stack.join(duid=self.remote.uid, cascade=self.cascade)
            return

        if not self.remote.allowed:
            emsg = "Aliver {0}. Must be allowed with {1} first\n".format(
                    self.stack.name, self.remote.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_remote')
            self.stack.allow(duid=self.remote.uid, cascade=self.cascade)
            return

        self.remote.refresh(alived=None) #Restart timer but do not change alived status
        self.add(self.index)

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
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        self.remote.refresh(alived=None) # restart timer do not change status
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
        console.concise("Aliver {0}. Rejected unjoin by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(duid=self.remote.uid, cascade=self.cascade)

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
        console.concise("Aliver {0}. Rejected unallow by {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.allow(duid=self.remote.uid, cascade=self.cascade)

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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
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

        self.add(self.index)

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
            self.remove(self.rxPacket.index)
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

        self.transmit(packet)
        self.remove()
        console.concise("Alivent {0}. Reject {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

class Messenger(Initiator):
    '''
    RAET protocol Messenger Initiator class Dual of Messengent
    Generic messages
    '''
    Timeout = 10.0
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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
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

        if self.index not in self.stack.transactions:
            self.add(self.index)
        elif self.stack.transactions[self.index] != self:
            emsg = "Messenger {0}. Index collision at {1}\n".format(
                                self.stack.name,  self.index)
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

class Messengent(Correspondent):
    '''
    RAET protocol Messengent Correspondent class Dual of Messenger
    Generic Messages
    '''
    Timeout = 10.0
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
                self.rejected()

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
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.remote.host,
                            dp=self.remote.port,
                            se=self.stack.local.uid,
                            de=self.remote.uid,
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

        if self.index not in self.stack.transactions:
            self.add(self.index)
        elif self.stack.transactions[self.index] != self:
            emsg = "Messengent {0}. Index collision at {1}\n".format(
                                self.stack.name,  self.index)
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
            self.stack.rxMsgs.append(body)
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

    def rejected(self):
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
        console.concise("Messagent {0}. Reject {1} at {2}\n".format(
                self.stack.name, self.remote.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

