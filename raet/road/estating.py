# -*- coding: utf-8 -*-
'''
estating.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611

import socket

from collections import deque

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding
from ioflo.base import storing

from .. import raeting
from .. import nacling
from .. import lotting

from ioflo.base.consoling import getConsole
console = getConsole()

class Estate(lotting.Lot):
    '''
    RAET protocol endpoint estate object
    '''

    def __init__(self,
                 stack=None,
                 name="",
                 ha=None,
                 eid=None,
                 tid=0,
                 host="",
                 port=raeting.RAET_PORT,
                 **kwa):
        '''
        Setup Estate instance
        '''
        if eid is None:
            if stack:
                eid = stack.nextEid()
                while eid in stack.remotes:
                    eid = stack.nextEid()
            else:
                eid = 0
        self.eid = eid # estate ID

        name = name or "estate{0}".format(self.uid)

        super(Estate, self).__init__(stack=stack, name=name, ha=ha, **kwa)

        self.tid = tid # current transaction ID

        if ha:  # takes precedence
            host, port = ha
        self.host = socket.gethostbyname(host)
        self.port = port
        if self.host == '0.0.0.0':
            host = '127.0.0.1'
        else:
            host = self.host
        self.fqdn = socket.getfqdn(host)

    @property
    def uid(self):
        '''
        property that returns unique identifier
        '''
        return self.eid

    @uid.setter
    def uid(self, value):
        '''
        setter for uid property
        '''
        self.eid = value

    @property
    def ha(self):
        '''
        property that returns ip address (host, port) tuple
        '''
        return (self.host, self.port)

    @ha.setter
    def ha(self, value):
        '''
        Expects value is tuple of (host, port)
        '''
        self.host, self.port = value

    def nextTid(self):
        '''
        Generates next transaction id number.
        '''
        self.tid += 1
        if self.tid > 0xffffffffL:
            self.tid = 1  # rollover to 1
        return self.tid

class LocalEstate(Estate):
    '''
    RAET protocol endpoint local estate object
    Maintains signer for signing and privateer for encrypt/decrypt
    '''
    def __init__(self, stack=None, name="", main=None,
                 sigkey=None, prikey=None, **kwa):
        '''
        Setup Estate instance

        sigkey is either nacl SigningKey or hex encoded key
        prikey is either nacl PrivateKey or hex encoded key
        '''
        super(LocalEstate, self).__init__(stack=stack, name=name, **kwa)
        self.main = True if main else False # main estate for road
        self.signer = nacling.Signer(sigkey)
        self.priver = nacling.Privateer(prikey) # Long term key

class RemoteEstate(Estate):
    '''
    RAET protocol endpoint remote estate object
    Maintains verifier for verifying signatures and publican for encrypt/decrypt

    .alived attribute is the dead or alive status of the remote

    .alived = True, alive, recently have received valid signed packets from remote
    .alive = False, dead, recently have not received valid signed packets from remote
    '''
    Period = 1.0
    Offset = 0.5
    Interim = 3600.0

    def __init__(self, stack, verkey=None, pubkey=None, acceptance=None, joined=None,
                 rsid=0, period=None, offset=None, interim=None, **kwa):
        '''
        Setup Estate instance

        stack is required parameter for RemoteEstate unlike its superclass

        verkey is either nacl VerifyKey or raw or hex encoded key
        pubkey is either nacl PublicKey or raw or hex encoded key

        acceptance is accepted state of remote on Road

        rsid is last received session id used by remotely initiated transaction

        period is timeout of keep alive heartbeat timer
        offset is initial offset of keep alive heartbeat timer

        interim is timeout of reapTimer (remove from memory if dead for reap time)
        '''
        if 'host' not in kwa and 'ha' not in kwa:
            kwa['ha'] = ('127.0.0.1', raeting.RAET_TEST_PORT)
        super(RemoteEstate, self).__init__(stack, **kwa)
        self.joined = joined
        self.allowed = None
        self.alived = None
        self.acceptance = acceptance
        self.privee = nacling.Privateer() # short term key manager
        self.publee = nacling.Publican() # correspondent short term key  manager
        self.verfer = nacling.Verifier(verkey) # correspondent verify key manager
        self.pubber = nacling.Publican(pubkey) # correspondent long term key manager

        self.rsid = rsid # last sid received from remote when RmtFlag is True
        self.indexes = set() # indexes to outstanding transactions for this remote

        # persistence keep alive heartbeat timer. Initial duration has offset so
        # not synced with other side persistence heatbeet
        self.period = period if period is not None else self.Period
        self.offset = offset if offset is not None else self.Offset
        # by default do not use offset on main unless it is explicity provided
        if self.stack.local.main and offset is None:
            duration = self.period
        else:
            duration = self.period + self.offset
        self.timer = aiding.StoreTimer(store=self.stack.store,
                                       duration=duration)

        self.interim = interim if interim is not None else self.Interim
        self.reapTimer = aiding.StoreTimer(self.stack.store,
                                           duration=self.interim)
        self.messages = deque() # deque of saved stale message body data to remote.uid

    def rekey(self):
        '''
        Regenerate short term keys
        '''
        self.allowed = None
        self.privee = nacling.Privateer() # short term key
        self.publee = nacling.Publican() # correspondent short term key  manager

    def validRsid(self, rsid):
        '''
        Compare new rsid to old .rsid and return True
        If new is >= old modulo N where N is 2^32 = 0x100000000
        And >= means the difference is less than N//2 = 0x80000000
        (((new - old) % 0x100000000) < (0x100000000 // 2))
        '''
        return self.validateSid(new=rsid, old=self.rsid)

    def refresh(self, alived=True):
        '''
        Restart presence heartbeat timer
        If alived is None then do not change .alived  but update timer
        If alived is True then set .alived to True and handle implications
        If alived is False the set .alived to False and handle implications
        '''
        self.timer.restart(duration=self.period)
        if alived is None:
            return

        if self.alived or alived: # alive before or after
            self.reapTimer.restart()
        #otherwise let timer run both before and after are still dead
        self.alived = alived

    def manage(self, cascade=False, immediate=False):
        '''
        Perform time based processing of keep alive heatbeat
        '''
        if immediate or self.timer.expired:
            # alive transaction restarts self.timer
            self.stack.alive(duid=self.uid, cascade=cascade)
        if self.interim >  0.0 and self.reapTimer.expired:
            self.reap()

    def reap(self):
        '''
        Remote is dead, reap it if main estate.
        '''
        if self.stack.local.main: #only reap main remotes
            console.concise("Stack {0}: Reaping dead remote {1} at {2}\n".format(
                    self.stack.name, self.name, self.stack.store.stamp))
            self.stack.incStat("remote_reap")
            self.stack.removeRemote(self.uid, clear=False) #remove from memory but not disk

    def removeStaleCorrespondents(self, renew=False):
        '''
        Remove stale correspondent transactions associated with remote

        If renew then remove all correspondents from this remote with nonzero sid

        Stale means the sid in the transaction is older than the current .rsid
        or if renew (rejoining with .rsid == zero)

        When sid in index is older than remote.rsid
        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        indexes = set(self.indexes) # make copy so not changed in place

        for index in indexes:
            sid = index[3]
            rf = index[0]
            if rf and  ((renew and sid != 0) or (not renew and not self.validRsid(sid))):
                if index in self.stack.transactions:
                    self.stack.transactions[index].nack()
                    self.stack.removeTransaction(index) # this discards it from self.indexes
                    emsg = ("Stack {0}: Stale correspondent {1} from remote {1} at {2}"
                            "\n".format(self.stack.name,
                                        index,
                                        self.name,
                                        self.stack.store.stamp))
                    console.terse(emsg)
                    self.stack.incStat('stale_correspondent')
                else:
                    self.indexes.discard(index)

    def replaceStaleInitiators(self, renew=False):
        '''
        Save and remove any messages from messenger transactions initiated locally
        with remote

        Remove non message stale initiator transactions associated with remote

        If renew Then remove all initiators from this remote with nonzero sid

        Stale means the sid in the transaction is older than the current .sid
        or if renew (rejoining with .sid == zero)

        When sid in index is older than remote.sid
        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        indexes = set(self.indexes) # make copy so not changed in place

        for index in indexes:
            sid = index[3]
            rf = index[0]
            if not rf and ((renew and sid != 0) or (not renew and not self.validSid(sid))):
                if index in self.stack.transactions:
                    transaction = self.stack.transactions[index]
                    if transaction.kind in [raeting.trnsKinds.message]:
                        self.saveMessage(transaction)
                    transaction.nack()
                    self.stack.removeTransaction(index) # this discards it from self.indexes
                    emsg = ("Stack {0}: Stale initiator {1} to remote {2} at {3}"
                            "\n".format(self.stack.name,
                                        index,
                                        self.name,
                                        self.stack.store.stamp))
                    console.terse(emsg)
                    self.stack.incStat('stale_initiator')
                else:
                    self.indexes.discard(index)

    def saveMessage(self, messenger):
        '''
        Message is Messenger compatible transaction
        Save copy of body data from stale initiated message on .messages deque
        for retransmitting later after new session is established
        '''
        self.messages.append(odict(messenger.tray.body))
        emsg = ("Stack {0}: Saved stale message with remote {1} at {2}"
                                                "\n".format(self.stack.name, index, self.name))
        console.concise(emsg)

    def sendSavedMessages(self):
        '''
        Message is Messenger compatible transaction
        Save stale initiated message for retransmitting later after new session is established
        '''
        while self.messages:
            body = self.messages.popleft()
            self.stack.message(body=body, duid=self.uid)
            emsg = ("Stack {0}: Resent saved message with remote {1} at {2}"
                                        "\n".format(self.stack.name, index, self.name))
            console.concise(emsg)

    def allowInProcess(self):
        '''
        Returns transaction if an allow transaction with this remote is already in process
        Otherwise returns None
        '''
        transactions = []
        for index in self.indexes:
            transaction = self.stack.transactions[index]
            if transaction.kind == raeting.trnsKinds.allow:
                transactions.append(transaction)
        return transactions

    def joinInProcess(self):
        '''
        Returns transaction if join transaction with this remote is already in process
        Otherwise returns None
        '''
        transactions = []
        for index in self.indexes:
            transaction = self.stack.transactions[index]
            if transaction.kind == raeting.trnsKinds.join:
                transactions.append(transaction)
        return transactions
