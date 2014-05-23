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

    def __init__(self, stack=None, kind=None, timeout=None,
                 reid=None, rmt=False, bcst=False, wait=False, sid=None, tid=None,
                 txData=None, txPacket=None, rxPacket=None):
        '''
        Setup Transaction instance
        timeout of 0.0 means no timeout go forever
        '''
        self.stack = stack
        self.kind = kind or raeting.PACKET_DEFAULTS['tk']

        if timeout is None:
            timeout = self.Timeout
        self.timeout = timeout
        self.timer = aiding.StoreTimer(self.stack.store, duration=self.timeout)

        # local estate is the .stack.estate
        self.reid = reid  # remote estate eid

        self.rmt = rmt
        self.bcst = bcst
        self.wait = wait

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
        re = self.reid
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
            self.stack.tx(packet.packed, self.reid)
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
        for key in ['kind', 'reid', 'sid', 'tid', 'rxPacket']:
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
                            de=self.reid,
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

        if self.reid not in self.stack.remotes:
            emsg = "Unknown correspondent estate id '{0}'\n".format(self.reid)
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


class Joiner(Initiator):
    '''
    RAET protocol Joiner Initiator class Dual of Joinent
    '''
    RedoTimeoutMin = 1.0 # initial timeout
    RedoTimeoutMax = 4.0 # max timeout


    def __init__(self, mha=None, redoTimeoutMin=None, redoTimeoutMax=None,
                 cascade=False, **kwa):
        '''
        Setup Transaction instance
        '''
        kwa['kind'] = raeting.trnsKinds.join
        super(Joiner, self).__init__(**kwa)

        self.mha = mha if mha is not None else ('127.0.0.1', raeting.RAET_PORT)
        self.cascade = cascade

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        if self.reid is None:
            if not self.stack.remotes: # no remote estate so make one
                remote = estating.RemoteEstate(stack=self.stack,
                                             eid=0,
                                             ha=self.mha,
                                             period=self.stack.period,
                                             offset=self.stack.offset)
                self.stack.addRemote(remote)
            self.reid = self.stack.remotes.values()[0].uid # zeroth is default
        remote = self.stack.remotes[self.reid]
        remote.joined = None
        self.sid = 0
        self.tid = remote.nextTid()
        self.prep()
        self.add(self.index)
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
            elif packet.data['pk'] == raeting.pcktKinds.renew: #refused renew
                self.renew()

    def process(self):
        '''
        Perform time based processing of transaction
        '''
        if self.timeout > 0.0 and self.timer.expired:
            if self.txPacket and self.txPacket.data['pk'] == raeting.pcktKinds.request:
                self.remove(self.txPacket.index) #index changes after accept
            else:
                self.remove(self.index) # in case never sent txPacket

            console.concise("Joiner {0}. Timed out at {1}\n".format(
                    self.stack.name, self.stack.store.stamp))

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
                console.concise("Joiner {0}. Redo Join at {1}\n".format(
                        self.stack.name, self.stack.store.stamp))
                self.stack.incStat('redo_join')

    def prep(self):
        '''
        Prepare .txData
        '''
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=self.stack.remotes[self.reid].host,
                            dp=self.stack.remotes[self.reid].port,
                            se=self.stack.local.uid,
                            de=self.reid,
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
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat(self.statKey())
            self.remove()
            return

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
        self.transmit(packet)
        console.concise("Joiner {0}. Do Join at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
    def renew(self):
        '''
        Reset to vacuous Road data and try joining again
        '''
        if self.stack.local.main: # main never renews so just reject
            self.reject()
            return

        if self.reid:
            self.stack.removeRemote(self.reid)
        self.stack.local.eid = 0
        self.stack.dumpLocal()
        self.remove(self.txPacket.index)
        console.terse("Joiner {0}. Refused at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(mha=self.mha)

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
        #import wingdbstub

        if not self.stack.parseInner(self.rxPacket):
            return
        data = self.rxPacket.data
        body = self.rxPacket.body.data

        leid = body.get('leid')
        if not leid:
            emsg = "Missing local estate id in accept packet\n"
            console.terse(emsg)
            self.stack.incStat('invalid_accept')
            self.remove(self.txPacket.index)
            return

        reid = body.get('reid')
        if not reid:
            emsg = "Missing remote estate id in accept packet\n"
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

        remote = self.stack.remotes[self.reid]

        # we are assuming for now that the joiner cannot talk peer to peer only
        # to main estate otherwise we need to ensure unique eid, name, and ha on road

        # check if remote keys of main estate are accepted here
        status = self.stack.safe.statusRemote(remote,
                                              verhex=verhex,
                                              pubhex=pubhex,
                                              main=self.stack.local.main)

        if status == raeting.acceptances.rejected:
            remote.joined = False
            self.nackAccept()
            return

        if not self.stack.local.main: #only should do this if not main
            if remote.uid != reid: #move remote estate to new index
                try:
                    self.stack.moveRemote(old=remote.uid, new=reid)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.txPacket.index)
                    return

            if remote.name != name: # rename remote estate to new name
                try:
                    self.stack.renameRemote(old=remote.name, new=name)
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.txPacket.index)
                    return

            self.stack.local.uid = leid
            self.stack.dumpLocal()

        self.reid = reid
        remote = self.stack.remotes[self.reid]
        remote.nextSid()
        self.stack.dumpRemote(remote)
        remote.joined = True #accepted

        self.ackAccept()

    def reject(self):
        '''
        Process nack to join packet
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.joined = False
        self.stack.removeRemote(self.reid)
        self.remove(self.txPacket.index)
        console.terse("Joiner {0}. Rejected at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def ackAccept(self):
        '''
        Send ack to accept response
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove(self.txPacket.index)
            return

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

        self.transmit(packet)
        self.remove(self.rxPacket.index)
        console.concise("Joiner {0}. Do Accept at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat("join_initiate_complete")
        if self.cascade:
            self.stack.allow(deid=self.reid, cascade=self.cascade)

    def nackAccept(self):
        '''
        Send nack to accept response
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove(self.txPacket.index)
            return

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

        self.transmit(packet)
        self.remove(self.txPacket.index)
        console.terse("Joiner {0}. Do Reject at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat(self.statKey())


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
        # Since corresponding bootstrap transaction use packet.index not self.index
        self.add(self.rxPacket.index)

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
            console.concise("Joinent {0}. Timed out at {0}\n".format(
                    self.stack.name, self.stack.store.stamp))
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

                self.transmit(self.txPacket) #redo
                console.concise("Joinent Redo Accept at {0}\n".format(self.stack.store.stamp))
                self.stack.incStat('redo_accept')
            else: #check to see if status has changed to accept
                remote = self.stack.remotes[self.reid]
                if remote:
                    data = self.stack.safe.loadRemote(remote)
                    if data:
                        status = self.stack.safe.statusRemote(remote,
                                                              data['verhex'],
                                                              data['pubhex'],
                                                              main=self.stack.local.main)
                        if status == raeting.acceptances.accepted:
                            self.accept()

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
            Only one estate with given ha on road is allowed on road.

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

        self.reid = reid

        if self.stack.local.main:
            if ((reid != 0 and not reid in self.stack.remotes) or
                    (leid !=  0 and leid != self.stack.local.uid)):
                if self.stack.safe.auto:
                    emsg = "Estate '{0}' renew stale eid '{1}'\n".format(
                            name, reid)
                    console.terse(emsg)
                    self.nack(kind=raeting.pcktKinds.renew) # refuse and renew
                else:
                    emsg = "Estate '{0}' reject unknown or stale eid '{1}'\n".format(
                            name, reid)
                    console.terse(emsg)
                    self.nack() # reject
                return

            if reid != 0:
                remote = self.stack.remotes[reid]
                if name != remote.name:
                    if (verhex != remote.verfer.keyhex or
                            pubhex != remote.pubber.keyhex):
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

                if (host != remote.host or port != remote.port):
                    if (verhex != remote.verfer.keyhex or
                            pubhex != remote.pubber.keyhex):
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

                status = self.stack.safe.statusRemote(remote,
                                                      verhex=verhex,
                                                      pubhex=pubhex,
                                                      main=self.stack.local.main)

                if status == raeting.acceptances.rejected:
                    "Estate '{0}' eid '{1}' keys rejected\n".format(
                            name, remote.uid)
                    self.stack.removeRemote(remote.uid) #reap remote
                    self.nack() # reject as keys rejected
                    return

                remote.host = host
                remote.port = port
                remote.rsid = self.sid
                remote.rtid = self.tid
                if name != remote.name:
                    self.stack.renameRemote(old=remote.name, new=name)

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
                        self.nack()
                        return

                other = self.stack.fetchRemoteByHostPort(host, port)
                if other and other is not remote: # (host, port) already in use by another estate
                    emsg = "Estate '{0}' ha '{1}' unavailable\n".format(
                                                    name,  str((host, port)))
                    console.terse(emsg)
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
                                                   rtid=self.tid,
                                                   period=self.stack.period,
                                                   offset=self.stack.offset,)

                    try:
                        self.stack.addRemote(remote) #provisionally add .accepted is None
                    except raeting.StackError as ex:
                        console.terse(str(ex) + '\n')
                        self.stack.incStat(self.statKey())
                        self.remove(self.rxPacket.index)
                        return

                self.reid = remote.uid # auto generated at instance creation above

                status = self.stack.safe.statusRemote(remote,
                                                      verhex=verhex,
                                                      pubhex=pubhex,
                                                      main=self.stack.local.main)

                if status == raeting.acceptances.rejected:
                    emsg = "Estate '{0}' eid '{1}' keys rejected\n".format(
                            name, remote.uid)
                    console.terse(emsg)
                    self.stack.removeRemote(remote.uid) #reap remote
                    self.nack() # reject as keys rejected
                    return

            self.stack.dumpRemote(remote)

            if status == raeting.acceptances.accepted:
                remote.joined = None
                duration = min(
                                max(self.redoTimeoutMin,
                                  self.redoTimer.duration * 2.0),
                                self.redoTimeoutMax)
                self.redoTimer.restart(duration=duration)
                self.accept()
            else: # status == None or status == raeting.acceptances.pending:
                remote.joined = None
                self.ackJoin()

        else: # not main stack
            if leid == 0 or reid == 0: #not main so can't process vacuous join
                emsg = ("Estate '{0}' not main, invalid leid '{1}' or "
                        "reid '{2}' from '{3}'\n".format(self.stack.local.name,
                                                         leid, reid, name))
                console.terse(emsg)
                self.nack()
                return
            if self.stack.remotes:
                if reid not in self.stack.remotes:
                    emsg = "Estate '{0}' not primary main '{1}' join attempt \n".format(
                            self.stack.local.name, name)
                    console.terse(emsg)
                    self.nack()
                    return
                else:
                    remote = self.stack.remotes[reid]
            else:
                remote = estating.RemoteEstate(stack=self.stack,
                                               eid=reid,
                                               name=name,
                                               host=host,
                                               port=port,
                                               acceptance=None,
                                               verkey=verhex,
                                               pubkey=pubhex,
                                               rsid=self.sid,
                                               rtid=self.tid,
                                               period=self.stack.period,
                                               offset=self.stack.offset,)
                try:
                    self.stack.addRemote(remote) #provisionally add .acceptance is None
                except raeting.StackError as ex:
                    console.terse(str(ex) + '\n')
                    self.stack.incStat(self.statKey())
                    self.remove(self.rxPacket.index)
                    return

            status = self.stack.safe.statusRemote(remote,
                                                  verhex=verhex,
                                                  pubhex=pubhex,
                                                  main=self.stack.local.main)

            if status == raeting.acceptances.rejected:
                "Estate '{0}' eid '{1}' keys rejected\n".format(
                        name, remote.uid)
                self.stack.removeRemote(remote.uid) #reap remote
                self.nack() # reject as keys rejected
                return

            if self.stack.local.uid != leid:
                self.stack.local.uid = leid
                self.stack.dumpLocal()

            remote.host = host
            remote.port = port
            remote.rsid = self.sid
            remote.rtid = self.tid
            if name != remote.name:
                self.stack.renameRemote(old=remote.name, new=name)
            #remote.nextSid() #set in complete method
            self.stack.dumpRemote(remote)
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
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove(self.rxPacket.index)
            return

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
        console.concise("Joinent {0}. Pending Accept at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))

    def accept(self):
        '''
        Send accept response to join request
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove(self.rxPacket.index)
            return

        body = odict([ ('leid', self.reid),
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

        self.transmit(packet)
        console.concise("Joinent {0}. Do Accept at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to join request.
        Sometimes nack occurs without remote being added so have to nack using ha.
        '''
        ha = None
        if self.reid not in self.stack.remotes:
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

        if ha:
            self.stack.txes.append((packet.packed, ha))

        else:
            self.transmit(packet)

        if kind == raeting.pcktKinds.renew:
            console.terse("Joinent {0}. Refuse '{1}' at {2}\n".format(
                            self.stack.name, ha, self.stack.store.stamp))
        else:
            console.terse("Joinent {0}. Reject at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))

        self.remove(self.rxPacket.index)
        self.stack.incStat(self.statKey())

    def complete(self):
        '''
        process ack to accept response
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.joined = True # accepted
        remote.nextSid()
        self.stack.dumpRemote(remote)

        self.remove(self.rxPacket.index)
        console.terse("Joinent {0}. Done at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat("join_correspond_complete")

    def reject(self):
        '''
        Process nack to accept response or stale
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.joined = False
        # use presence to remove remote

        self.remove(self.rxPacket.index)
        console.terse("Joinent {0}. Rejected at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat(self.statKey())


class Allower(Initiator):
    '''
    RAET protocol Allower Initiator class Dual of Allowent
    CurveCP handshake
    '''
    Timeout = 4.0
    RedoTimeoutMin = 0.25 # initial timeout
    RedoTimeoutMax = 1.0 # max timeout

    def __init__(self, mha=None, redoTimeoutMin=None, redoTimeoutMax=None,
                 cascade=False, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.allow
        super(Allower, self).__init__(**kwa)

        self.mha = mha if mha is not None else ('127.0.0.1', raeting.RAET_PORT)
        self.cascade = cascade

        self.oreo = None # cookie from correspondent needed until handshake completed

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        if self.reid is None:
            if not self.stack.remotes: # no remote estate so make one
                remote = estating.RemoteEstate(stack=self.stack,
                                               eid=0,
                                               ha=self.mha,
                                               period=self.stack.period,
                                               offset=self.stack.offset)
                self.stack.addRemote(remote)
            self.reid = self.stack.remotes.values()[0].uid # zeroth is default
        remote = self.stack.remotes[self.reid]
        remote.rekey() # reset .allowed to None and refresh short term keys

        self.sid = remote.sid
        self.tid = remote.nextTid()
        self.prep() # prepare .txData
        self.add(self.index)

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
            console.concise("Allower {0}. Timed out at {1}\n".format(
                    self.stack.name, self.stack.store.stamp))
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
                    console.concise("Allower {0}. Redo Hello at {1}\n".format(
                            self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_hello')

                if self.txPacket.data['pk'] == raeting.pcktKinds.initiate:
                    self.transmit(self.txPacket) # redo
                    console.concise("Allower {0}. Redo Initiate at {1}\n".format(
                            self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_initiate')

                if self.txPacket.data['pk'] == raeting.pcktKinds.ack:
                    self.transmit(self.txPacket) # redo
                    console.concise("Allower {0}. Redo Ack Final at {1}\n".format(
                            self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_final')

    def prep(self):
        '''
        Prepare .txData
        '''
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
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
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

        remote = self.stack.remotes[self.reid]
        if not remote.joined:
            emsg = "Allower {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_remote')
            self.remove()
            self.stack.join(deid=self.reid, cascade=self.cascade)
            return

        remote = self.stack.remotes[self.reid]
        plain = binascii.hexlify("".rjust(32, '\x00'))
        cipher, nonce = remote.privee.encrypt(plain, remote.pubber.key)
        body = raeting.HELLO_PACKER.pack(plain, remote.privee.pubraw, cipher, nonce)

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
        console.concise("Allower {0}. Do Hello at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))

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

        remote = self.stack.remotes[self.reid]

        msg = remote.privee.decrypt(cipher, nonce, remote.pubber.key)
        if len(msg) != raeting.COOKIESTUFF_PACKER.size:
            emsg = "Invalid length of cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
            return

        shortraw, seid, deid, oreo = raeting.COOKIESTUFF_PACKER.unpack(msg)

        if seid != remote.uid or deid != self.stack.local.uid:
            emsg = "Invalid seid or deid fields in cookie stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_cookie')
            self.remove()
            return

        self.oreo = binascii.hexlify(oreo)
        remote.publee = nacling.Publican(key=shortraw)

        self.initiate()

    def initiate(self):
        '''
        Send initiate request to cookie response to hello request
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

        remote = self.stack.remotes[self.reid]

        vcipher, vnonce = self.stack.local.priver.encrypt(remote.privee.pubraw,
                                                remote.pubber.key)

        fqdn = remote.fqdn.ljust(128, ' ')

        stuff = raeting.INITIATESTUFF_PACKER.pack(self.stack.local.priver.pubraw,
                                                  vcipher,
                                                  vnonce,
                                                  fqdn)

        cipher, nonce = remote.privee.encrypt(stuff, remote.publee.key)

        oreo = binascii.unhexlify(self.oreo)
        body = raeting.INITIATE_PACKER.pack(remote.privee.pubraw,
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
        console.concise("Allower {0}. Do Initiate at {1}\n".format(self.stack.name,
                                                            self.stack.store.stamp))

    def allow(self):
        '''
        Process ackInitiate packet
        Perform allowment in response to ack to initiate packet
        Transmits ack to complete transaction so correspondent knows
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.allowed = True
        self.ackFinal()

    def ackFinal(self):
        '''
        Send ack to ack Initiate to terminate transaction
        Why do we need this? could we just let transaction timeout on allowent
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Allower {0}. Ack Final at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat("allow_initiate_complete")
        if self.cascade:
            self.stack.alive(deid=self.reid, cascade=self.cascade)

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.allowed = False
        self.remove()
        console.concise("Allower {0}. Rejected at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def unjoin(self):
        '''
        Process unjoin packet
        terminate in response to unjoin
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        remote = self.stack.remotes[self.reid]
        remote.joined = False
        self.remove()
        console.concise("Allower {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(deid=self.reid, cascade=self.cascade)

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
        if 'reid' not  in kwa:
            emsg = "Missing required keyword argumens: '{0}'".format('reid')
            raise TypeError(emsg)
        super(Allowent, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        remote = self.stack.remotes[self.reid]
        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        remote.rsid = self.sid #update last received rsid for estate
        remote.rtid = self.tid #update last received rtid for estate
        self.oreo = None #keep locally generated oreo around for redos
        remote.rekey() # refresh short term keys and .allowed
        self.prep() # prepare .txData
        self.add(self.index)

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
            console.concise("Allowent {0}. Timed out at {0}\n".format(
                    self.stack.name, self.stack.store.stamp))
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
                    console.concise("Allowent {0}. Redo Cookie at {1}\n".format(
                            self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_cookie')

                if self.txPacket.data['pk'] == raeting.pcktKinds.ack:
                    self.transmit(self.txPacket) #redo
                    console.concise("Allowent {0}. Redo Ack at {1}\n".format(
                            self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_allow')

    def prep(self):
        '''
        Prepare .txData
        '''
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
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
        remote = self.stack.remotes[self.reid]
        if not remote.joined:
            emsg = "Allowent {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_allow_attempt')
            self.nack(kind=raeting.pcktKinds.unjoined)
            return

        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        if not remote.validRsid(self.sid):
            emsg = "Stale sid '{0}' in packet\n".format(self.sid)
            console.terse(emsg)
            self.stack.incStat('stale_sid_allow_attempt')
            self.remove()
            return

        if not self.stack.parseInner(self.rxPacket):
            return
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

        remote = self.stack.remotes[self.reid]
        remote.publee = nacling.Publican(key=shortraw)
        msg = self.stack.local.priver.decrypt(cipher, nonce, remote.publee.key)
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
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

        remote = self.stack.remotes[self.reid]
        oreo = self.stack.local.priver.nonce()
        self.oreo = binascii.hexlify(oreo)

        stuff = raeting.COOKIESTUFF_PACKER.pack(remote.privee.pubraw,
                                                self.stack.local.uid,
                                                remote.uid,
                                                oreo)

        cipher, nonce = self.stack.local.priver.encrypt(stuff, remote.publee.key)
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
        console.concise("Allowent {0}. Do Cookie at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))

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

        remote = self.stack.remotes[self.reid]

        if shortraw != remote.publee.keyraw:
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

        msg = remote.privee.decrypt(cipher, nonce, remote.publee.key)
        if len(msg) != raeting.INITIATESTUFF_PACKER.size:
            emsg = "Invalid length of initiate stuff\n"
            console.terse(emsg)
            self.stack.incStat('invalid_initiate')
            self.remove()
            return

        pubraw, vcipher, vnonce, fqdn = raeting.INITIATESTUFF_PACKER.unpack(msg)
        if pubraw != remote.pubber.keyraw:
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

        vouch = self.stack.local.priver.decrypt(vcipher, vnonce, remote.pubber.key)
        if vouch != remote.publee.keyraw or vouch != shortraw:
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
        if self.reid not in self.stack.remotes:
            msg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Allowent {0}. Do Ack at {1}\n".format(
                self.stack.name, self.stack.store.stamp))

        self.allow()

    def allow(self):
        '''
        Perform allowment
        '''
        remote = self.stack.remotes[self.reid]
        remote.allowed = True

    def final(self):
        '''
        Process ackFinal packet
        So that both sides are waiting on acks at the end so does not restart
        transaction if ack initiate is dropped
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        self.remove()
        console.concise("Allowent {0}. Do Final at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat("allow_correspond_complete")

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.allowed = False

        self.remove()
        console.concise("Allowent {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to terminate allow transaction
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Allowent {0}. Reject at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
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

        if self.reid is None:
            self.reid = self.stack.remotes.values()[0].uid # zeroth is main estate
        remote = self.stack.remotes[self.reid]
        self.sid = remote.sid
        self.tid = remote.nextTid()
        self.prep() # prepare .txData
        self.tray = packeting.TxTray(stack=self.stack)
        self.add(self.index)

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
            console.concise("Messenger {0}. Timed out at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
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
                    console.concise("Messenger {0}. Redo Segment {1} at {2}\n".format(
                        self.stack.name, self.tray.last, self.stack.store.stamp))
                    self.stack.incStat('redo_segment')

    def prep(self):
        '''
        Prepare .txData
        '''
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def message(self, body=None):
        '''
        Send message
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

        remote = self.stack.remotes[self.reid]
        if not remote.allowed:
            emsg = "Messenger {0}. Must be allowed first\n".format(self.stack.name)
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
            return

        burst = 1 if self.wait else len(self.tray.packets) - self.tray.current

        for packet in self.tray.packets[self.tray.current:self.tray.current + burst]:
            self.transmit(packet) #if self.tray.current %  2 else None
            self.tray.last = self.tray.current
            self.stack.incStat("message_segment_tx")
            console.concise("Messenger {0}. Do Message Segment {1} at {2}\n".format(
                    self.stack.name, self.tray.last, self.stack.store.stamp))
            self.tray.current += 1

    def another(self):
        '''
        Process ack packet send next one
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True)

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

        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True)

        data = self.rxPacket.data
        body = self.rxPacket.body.data

        misseds = body.get('misseds')
        if misseds:

            if self.reid not in self.stack.remotes:
                emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
                console.terse(emsg)
                self.stack.incStat('invalid_remote_eid')
                self.remove()
                return

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
                console.concise("Messenger {0}. Resend Message Segment {1} at {2}\n".format(
                        self.stack.name, m, self.stack.store.stamp))

    def complete(self):
        '''
        Complete transaction and remove
        '''
        self.remove()
        console.concise("Messenger {0}. Done at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat("message_initiate_complete")

    def reject(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True)

        self.remove()
        console.concise("Messenger {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
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
        if 'reid' not  in kwa:
            emsg = "Missing required keyword argumens: '{0}'".format('reid')
            raise TypeError(emsg)
        super(Messengent, self).__init__(**kwa)

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        remote = self.stack.remotes[self.reid]
        # .bcast .wait set from packet by stack when created transaction
        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        remote.rsid = self.sid #update last received rsid for estate
        remote.rtid = self.tid #update last received rtid for estate
        self.prep() # prepare .txData
        self.tray = packeting.RxTray(stack=self.stack)
        self.add(self.index)

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
            console.concise("Messengent {0}. Timed out at {1}\n".format(
                    self.stack.name, self.stack.store.stamp))
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
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
                            tk=self.kind,
                            cf=self.rmt,
                            bf=self.bcst,
                            wf=self.wait,
                            si=self.sid,
                            ti=self.tid,)

    def message(self):
        '''
        Process message packet
        '''
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True)

        if not remote.allowed:
            emsg = "Messengent {0}. Must be allowed first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_message_attempt')
            self.nack()
            return
        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        if not remote.validRsid(self.sid):
            emsg = "Stale sid '{0}' in packet\n".format(self.sid)
            console.terse(emsg)
            self.stack.incStat('stale_sid_message_attempt')
            self.remove()
            return

        try:
            body = self.tray.parse(self.rxPacket)
        except raeting.PacketError as ex:
            console.terse(str(ex) + '\n')
            self.incStat('parsing_message_error')
            self.remove()
            return

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
        if self.reid not in self.stack.remotes:
            msg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Messengent {0}. Do Ack Segment {1} at {2}\n".format(
                self.stack.name, self.tray.last, self.stack.store.stamp))

    def resend(self, misseds):
        '''
        Send resend request(s) for missing packets
        '''
        if self.reid not in self.stack.remotes:
            msg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
            console.concise("Messengent {0}. Do Resend Segments {1} at {2}\n".format(
                    self.stack.name, misseds, self.stack.store.stamp))
            misseds = remainders

    def complete(self):
        '''
        Complete transaction and remove
        '''
        self.remove()
        console.concise("Messengent {0}. Complete at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat("messagent_correspond_complete")

    def rejected(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return

        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True)

        self.remove()
        console.concise("Messengent {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def nack(self):
        '''
        Send nack to terminate messenger transaction
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Messagent {0}. Reject at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
        self.stack.incStat(self.statKey())

class Aliver(Initiator):
    '''
    RAET protocol Aliver Initiator class Dual of Alivent
    Sends keep alive heatbeat messages to detect presence
    '''
    Timeout = 2.0
    RedoTimeoutMin = 0.25 # initial timeout
    RedoTimeoutMax = 1.0 # max timeout

    def __init__(self, mha=None, redoTimeoutMin=None, redoTimeoutMax=None,
                cascade=False, **kwa):
        '''
        Setup instance
        '''
        kwa['kind'] = raeting.trnsKinds.alive
        super(Aliver, self).__init__(**kwa)

        self.mha = mha if mha is not None else ('127.0.0.1', raeting.RAET_PORT)
        self.cascade = cascade

        self.redoTimeoutMax = redoTimeoutMax or self.RedoTimeoutMax
        self.redoTimeoutMin = redoTimeoutMin or self.RedoTimeoutMin
        self.redoTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.redoTimeoutMin)

        if self.reid is None:
            if not self.stack.remotes: # no remote estate so make one
                remote = estating.RemoteEstate(stack=self.stack,
                                               eid=0,
                                               ha=self.mha,
                                               period=self.stack.period,
                                               offset=self.stack.offset)
                self.stack.addRemote(remote)
            self.reid = self.stack.remotes.values()[0].uid # zeroth is main estate
        remote = self.stack.remotes[self.reid]
        remote.alived = None # reset alive status until done with transaction
        # .bcast set from packet by stack when created transaction
        self.sid = remote.sid
        self.tid = remote.nextTid()
        self.prep() # prepare .txData
        self.add(self.index)

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
            console.concise("Aliver {0}. Timed out at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
            self.remove()
            remote = self.stack.remotes[self.reid]
            remote.refresh(alived=False) # mark as dead
            #self.reap() #remote is dead so reap it
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
                    console.concise("Aliver {0}. Redo at {1}\n".format(
                        self.stack.name, self.stack.store.stamp))
                    self.stack.incStat('redo_alive')

    def prep(self):
        '''
        Prepare .txData
        '''
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
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
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

        remote = self.stack.remotes[self.reid]
        if not remote.joined:
            emsg = "Aliver {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_remote')
            self.remove()
            self.stack.join(deid=self.reid, cascade=self.cascade)
            return

        if not remote.allowed:
            emsg = "Aliver {0}. Must be allowed first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_remote')
            self.remove()
            self.stack.allow(deid=self.reid, cascade=self.cascade)
            return

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
        console.concise("Aliver {0}. Do Alive at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
    def complete(self):
        '''
        Process ack packet. Complete transaction and remove
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=True) # restart timer mark as alive
        self.remove()
        console.concise("Aliver {0}. Done at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat("alive_complete")

    def reap(self):
        '''
        Remote dead. Reap it.
        '''
        self.remove()
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=False) # mark as dead
        console.concise("Aliver {0}. Reaping dead remote '{1}' at {2}\n".format(
                self.stack.name, remote.name, self.stack.store.stamp))
        self.stack.incStat("alive_reap")
        self.stack.removeRemote(remote.uid)

    def refuse(self):
        '''
        Process nack packet
        terminate in response to nack
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=None) # restart timer mark as indeterminate
        self.remove()
        console.concise("Aliver {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())

    def unjoin(self):
        '''
        Process unjoin packet
        terminate in response to unjoin
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=None) # restart timer mark as indeterminate
        remote.joined = False
        self.remove()
        console.concise("Aliver {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.join(deid=self.reid, cascade=self.cascade)

    def unallow(self):
        '''
        Process unallow nack packet
        terminate in response to unallow
        '''
        if not self.stack.parseInner(self.rxPacket):
            return
        remote = self.stack.remotes[self.reid]
        remote.refresh(alived=None) # restart timer mark as indeterminate
        remote.allowed = False
        self.remove()
        console.concise("Aliver {0}. Rejected at {1}\n".format(
                self.stack.name, self.stack.store.stamp))
        self.stack.incStat(self.statKey())
        self.stack.allow(deid=self.reid, cascade=self.cascade)

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
        if 'reid' not  in kwa:
            emsg = "Missing required keyword argumens: '{0}'".format('reid')
            raise TypeError(emsg)
        super(Alivent, self).__init__(**kwa)

        remote = self.stack.remotes[self.reid]
        #remote.alive = None # reset alive status until done with transaction
        # .bcast set from packet by stack when created transaction
        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        remote.rsid = self.sid #update last received rsid for estate
        remote.rtid = self.tid #update last received rtid for estate
        self.prep() # prepare .txData
        self.add(self.index)

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
            self.nack()
            console.concise("Alivent {0}. Timed out at {1}\n".format(
                    self.stack.name, self.stack.store.stamp))
            return

    def prep(self):
        '''
        Prepare .txData
        '''
        remote = self.stack.remotes[self.reid]
        self.txData.update( sh=self.stack.local.host,
                            sp=self.stack.local.port,
                            dh=remote.host,
                            dp=remote.port,
                            se=self.stack.local.uid,
                            de=self.reid,
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
        data = self.rxPacket.data
        body = self.rxPacket.body.data

        remote = self.stack.remotes[self.reid]

        if not remote.joined:
            remote.refresh(alived=None) # indeterminate
            emsg = "Alivent {0}. Must be joined first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unjoined_alive_attempt')
            self.nack(kind=raeting.pcktKinds.unjoined)
            return

        if not remote.allowed:
            remote.refresh(alived=None) # indeterminate
            emsg = "Alivent {0}. Must be allowed first\n".format(self.stack.name)
            console.terse(emsg)
            self.stack.incStat('unallowed_alive_attempt')
            self.nack(kind=raeting.pcktKinds.unallowed)
            return

        #Current .sid was set by stack from rxPacket.data sid so it is the new rsid
        if not remote.validRsid(self.sid):
            emsg = "Stale sid '{0}' in packet\n".format(self.sid)
            console.terse(emsg)
            self.stack.incStat('stale_sid_message_attempt')
            self.remove()
            return

        if self.reid not in self.stack.remotes:
            msg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Alivent {0}. Do ack alive at {1}\n".format(self.stack.name,
                                                        self.stack.store.stamp))
        remote.refresh(alived=True)
        self.remove()
        console.concise("Alivent {0}. Done at {1}\n".format(
                        self.stack.name, self.stack.store.stamp))
        self.stack.incStat("alive_complete")

    def nack(self, kind=raeting.pcktKinds.nack):
        '''
        Send nack to terminate alive transaction
        '''
        if self.reid not in self.stack.remotes:
            emsg = "Invalid remote destination estate id '{0}'\n".format(self.reid)
            console.terse(emsg)
            self.stack.incStat('invalid_remote_eid')
            self.remove()
            return

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
        console.concise("Alivent {0}. Reject at {1}\n".format(self.stack.name,
                                                    self.stack.store.stamp))
        self.stack.incStat(self.statKey())
