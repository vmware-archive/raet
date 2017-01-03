# -*- coding: utf-8 -*-
'''
estating.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611

import socket
import uuid
from collections import deque
import sys
if sys.version_info > (3,):
    long = int

# Import ioflo libs
from ioflo.aid.odicting import odict
from ioflo.aid.timing import StoreTimer

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import TrnsKind
from .. import nacling
from .. import lotting

from ioflo.base.consoling import getConsole
console = getConsole()


class Estate(lotting.Lot):
    '''
    RAET protocol endpoint estate object ie Road Lot
    '''

    def __init__(self,
                 stack,
                 name="",
                 prefix='estate',
                 ha=None,
                 iha=None,
                 natted=None,
                 fqdn='',
                 dyned=None,
                 uid=None,
                 tid=0,
                 role=None,
                 **kwa):
        '''
        Setup instance

        stack is required parameter
        '''
        name = name or self.nameGuid(prefix=prefix)
        uid = uid if uid is not None else stack.nextUid()
        super(Estate, self).__init__(stack=stack, name=name, ha=ha, uid=uid, **kwa)

        self.tid = tid # current transaction ID

        # if host is unspecified or all then use loopback address as host
        if ha:
            host, port = ha
            host = self.normalizeHost(host)
            if host in ('0.0.0.0',):
                host = '127.0.0.1'
            elif host in ("::", "0:0:0:0:0:0:0:0"):
                host = "::1"
            ha = (host, port)
        self.ha = ha
        if iha:  # future iha should take precedence
            host, port = iha
            host = self.normalizeHost(host)
            if host in ('0.0.0.0',):
                host = '127.0.0.1'
            elif host in ("::", "0:0:0:0:0:0:0:0"):
                host = "::1"
            iha = (host, port)
        self.iha = iha # internal host address duple (host, port)
        self.natted = natted # is estate behind nat router
        self.fqdn = fqdn or socket.getfqdn(self.ha[0]) if self.ha else ''
        self.dyned = dyned
        self.role = role if role is not None else self.name
        self.transactions = odict() # estate transactions keyed by transaction index
        self.doneTransactions = odict()  # temporary storage for done transaction ids

    @property
    def eha(self):
        '''
        property that returns  external ip address (host, port) tuple
        alias for .ha
        '''
        return self.ha

    @eha.setter
    def eha(self, value):
        '''
        Expects value is tuple of (host, port)
        '''
        self.ha = value

    def normalizeHost(self, host):
        '''
        Returns ip address host string in normalized dotted form or empty string
        converts host parameter which may be the dns name not ip address
        Prefers ipv4 addresses over ipv6 in that it will only return the ipv6
        address if no ipv4 address equivalent is available
        '''
        if host == "":
            host = "0.0.0.0"

        try:  # try ipv4
            info =  socket.getaddrinfo(host,
                                       None,
                                       socket.AF_INET,
                                       socket.SOCK_DGRAM,
                                       socket.IPPROTO_IP, 0)
        except socket.gaierror as ex: # try ipv6
            if host in ("", "0.0.0.0"):
                host = "::"

            info =  socket.getaddrinfo(host,
                                        None,
                                        socket.AF_INET6,
                                        socket.SOCK_DGRAM,
                                        socket.IPPROTO_IP, 0)
        if not info:
            emsg = "Cannot resolve address for host '{0}'".format(host)
            raise raeting.EstateError(emsg)

        host = info[0][4][0]
        return host

    def nextTid(self):
        '''
        Generates next transaction id number.
        '''
        self.tid += 1
        if self.tid > long(0xffffffff):
            self.tid = 1  # rollover to 1
        return self.tid

    def addTransaction(self, index, transaction):
        '''
        Safely add transaction at index, If not already there

        index of the form
        (rf, le, re, si, ti, bf)

        Where
        rf = Remotely Initiated Flag, RmtFlag
        le = leid, local estate id LEID
        re = reid, remote estate id REID
        si = sid, Session ID, SID
        ti = tid, Transaction ID, TID
        bf = Broadcast Flag, BcstFlag
        '''
        if index in self.transactions:
            emsg = "Cannot add transaction at index '{0}', alreadys exists".format(index)
            raise raeting.EstateError(emsg)
        self.transactions[index] = transaction
        transaction.remote = self
        console.verbose( "Added transaction to {0} at '{1}'\n".format(self.name, index))

    def removeTransaction(self, index, transaction=None):
        '''
        Safely remove transaction at index, If transaction identity same
        If transaction is None then remove without comparing identity
        '''
        if index in self.transactions: # fast way
            if not transaction or transaction is self.transactions[index]:
                del self.transactions[index]
                console.verbose( "Removed transaction from {0} at"
                                 " '{1}'\n".format(self.name, index))
                return

        if transaction: # find transaction slow way
            for i, trans in self.transactions.items():
                if trans is transaction:
                    del self.transactions[i]
                    console.concise( "Removed transaction from '{0}' at '{1}',"
                            " instead of at '{2}'\n".format(self.name, i, index))

    def addDoneTransaction(self, index):
        self.doneTransactions[index] = StoreTimer(self.stack.store, duration=self.stack.MsgStaleTimeout)

    def cleanupDoneTransactions(self):
        for index, timer in self.doneTransactions.iteritems():
            if not timer.expired:
                break
            del self.doneTransactions[index]
            console.verbose("Removed already done transaction from {0} at '{1}'\n".format(self.name, index))

    def removeStaleTransactions(self):
        '''
        Remove stale transactions associated with estate
        '''
        pass

    def process(self):
        '''
        Call .process or all transactions to allow timer based processing
        '''
        for transaction in self.transactions.values():
            transaction.process()
        self.cleanupDoneTransactions()

    @staticmethod
    def nameGuid(prefix='estate'):
        '''
        Returns string guid name for road estate given prefix using hex of uuid.uuid1
        '''
        return ("{0}_{1}".format(prefix, uuid.uuid1().hex))

class LocalEstate(Estate):
    '''
    RAET protocol endpoint local estate object ie Local Road Lot
    Maintains signer for signing and privateer for encrypt/decrypt
    '''
    def __init__(self,
                 sigkey=None,
                 prikey=None,
                 **kwa):
        '''
        Setup instance

        stack is required argument

        sigkey is either nacl SigningKey or hex encoded key
        prikey is either nacl PrivateKey or hex encoded key
        '''
        if 'ha' not in kwa:
            kwa['ha'] = ('127.0.0.1', raeting.RAET_PORT)
        super(LocalEstate, self).__init__( **kwa)
        self.signer = nacling.Signer(sigkey)
        self.priver = nacling.Privateer(prikey) # Long term key

class RemoteEstate(Estate):
    '''
    RAET protocol endpoint remote estate object ie Remote Road Lot
    Maintains verifier for verifying signatures and publican for encrypt/decrypt

    .alived attribute is the dead or alive status of the remote

    .alived = True, alive, recently have received valid signed packets from remote
    .alive = False, dead, recently have not received valid signed packets from remote

    .fuid is the far uid of the remote as owned by the farside stack
    '''

    def __init__(self,
                 stack,
                 uid=None,
                 fuid=0,
                 main=False,
                 kind=0,
                 verkey=None,
                 pubkey=None,
                 acceptance=None,
                 joined=None,
                 rsid=0,
                 **kwa):
        '''
        Setup instance

        stack is required parameter

        verkey is either nacl VerifyKey or raw or hex encoded key
        pubkey is either nacl PublicKey or raw or hex encoded key

        acceptance is accepted state of remote on Road

        rsid is last received session id used by remotely initiated transaction


        '''
        if uid is None:
            uid = stack.nextUid()
            while uid in stack.remotes or uid == stack.local.uid:
                uid = stack.nextUid()

        if 'ha' not in kwa:
            kwa['ha'] = ('127.0.0.1', raeting.RAET_TEST_PORT)
        super(RemoteEstate, self).__init__(stack, uid=uid, **kwa)
        self.fuid = fuid
        self.main = main
        self.kind = kind
        self.joined = joined
        self.allowed = None
        self.alived = None
        self.reaped = None
        self.acceptance = acceptance
        self.privee = nacling.Privateer() # short term key manager
        self.publee = nacling.Publican() # correspondent short term key  manager
        self.verfer = nacling.Verifier(verkey) # correspondent verify key manager
        self.pubber = nacling.Publican(pubkey) # correspondent long term key manager

        self.rsid = rsid # last sid received from remote when RmtFlag is True

        # persistence keep alive heartbeat timer. Initial duration has offset so
        # not synced with other side persistence heatbeet
        # by default do not use offset on main
        if self.stack.main:
            duration = self.stack.period
        else:
            duration = self.stack.period + self.stack.offset
        self.timer = StoreTimer(store=self.stack.store,
                                       duration=duration)

        self.reapTimer = StoreTimer(self.stack.store,
                                           duration=self.stack.interim)
        self.messages = deque() # deque of saved stale message body data to remote.uid

    @property
    def nuid(self):
        '''
        property that returns nuid, near uid, of remote as owned by nearside stack
        alias for uid
        '''
        return self.uid

    @nuid.setter
    def nuid(self, value):
        '''
        setter for nuid, near uid, property
        '''
        self.uid = value

    @property
    def juid(self):
        '''
        property that returns juid, join uid, duple of (nuid, fuid)
        nuid is near uid
        fuid is far uid as owned by farside stack
        '''
        return (self.nuid, self.fuid)

    @juid.setter
    def juid(self, value):
        '''
        setter for juid, join uid, property, value is duple of (nuid, fuid)
        '''
        self.nuid, self.fuid = value

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
        If old is zero Then new is always valid
        If new is >= old modulo N where N is 2^32 = 0x100000000
        And >= means the difference is less than N//2 = 0x80000000
        (((new - old) % 0x100000000) < (0x100000000 // 2))
        '''
        return self.validateSid(new=rsid, old=self.rsid)

    def refresh(self, alived=True):
        '''
        Restart presence heartbeat timer and conditionally reapTimer
        If alived is None then do not change .alived  but update timer
        If alived is True then set .alived to True and handle implications
        If alived is False the set .alived to False and handle implications
        '''
        self.timer.restart(duration=self.stack.period)
        if alived is None:
            return

        if self.alived or alived: # alive before or after
            self.reapTimer.restart()
            if self.reaped:
                self.unreap()
        #otherwise let timer run both before and after are still dead
        self.alived = alived

    def manage(self, cascade=False, immediate=False):
        '''
        Perform time based processing of keep alive heatbeat
        '''
        if not self.reaped: # only manage alives if not already reaped
            if immediate or self.timer.expired:
                # alive transaction restarts self.timer
                self.stack.alive(uid=self.uid, cascade=cascade)
            if self.stack.interim >  0.0 and self.reapTimer.expired:
                self.reap()

    def reap(self):
        '''
        Remote is dead, reap it if main estate.
        '''
        if self.stack.main: # only main can reap
            console.concise("Stack {0}: Reaping dead remote {1} at {2}\n".format(
                    self.stack.name, self.name, self.stack.store.stamp))
            self.stack.incStat("remote_reap")
            self.reaped = True

    def unreap(self):
        '''
        Remote packet received from remote so not dead anymore.
        '''
        if self.stack.main: # only only main can reap or unreap
            console.concise("Stack {0}: Unreaping dead remote {1} at {2}\n".format(
                    self.stack.name, self.name, self.stack.store.stamp))
            self.stack.incStat("remote_unreap")
            self.reaped = False

    def removeStaleCorrespondents(self):
        '''
        Remove local stale correspondent transactions associated with remote

        Local correspondent is indicated by rf ==True

        Stale means the sid in the transaction is older than the current .rsid
        assuming neither is zero, that is sid in index is older than remote.rsid

        old rsid == 0 means new always valid

        When sid in index is older than remote.rsid
        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        for index, transaction in self.transactions.items():
            sid = index[3]
            rf = index[0] # correspondent
            if rf and not self.validRsid(sid):
                transaction.nack()
                self.removeTransaction(index)
                emsg = ("Stack {0}: Stale correspondent {1} from remote {2} "
                        "with prior rsid {3} at {4}\n".format(self.stack.name,
                                        index,
                                        self.name,
                                        self.rsid,
                                        self.stack.store.stamp))
                console.terse(emsg)
                self.stack.incStat('stale_correspondent')
        self.doneTransactions.clear()

    def replaceStaleInitiators(self):
        '''
        Save and remove any messages from messenger transactions initiated locally
        with remote

        Remove non message stale local initiator transactions associated with remote
        Also save and requeue any stale locally initiated message transactions.

        Local inititors have rf flag == False

        Stale means the sid in the transaction is older than the current .sid
        assuming neither is zero, that is  sid in index is older than remote.sid

        old sid == 0 means new always valid

        Where index is tuple: (rf, le, re, si, ti, bf,)
            rf = Remotely Initiated Flag, RmtFlag
            le = leid, Local estate ID, LEID
            re = reid, Remote estate ID, REID
            si = sid, Session ID, SID
            ti = tid, Transaction ID, TID
            bf = Broadcast Flag, BcstFlag
        '''
        for index, transaction in self.transactions.items():
            rf = index[0]
            sid = index[3]

            if not rf and not self.validSid(sid): # transaction sid newer or equal
                if transaction.kind in [TrnsKind.message]:
                    self.saveMessage(transaction)
                transaction.nack()
                self.removeTransaction(index)
                emsg = ("Stack {0}: Stale initiator {1} to remote {2} with "
                        "prior rsid {3} at {4}\n".format(self.stack.name,
                                    index,
                                    self.name,
                                    self.rsid,
                                    self.stack.store.stamp))
                console.terse(emsg)
                self.stack.incStat('stale_initiator')

    def saveMessage(self, messenger):
        '''
        Save copy of body data from stale initiated messenger onto .messages deque
        for retransmitting later after new session is established
        messenger is instance of Messenger compatible transaction
        '''
        self.messages.append(odict(messenger.tray.body))
        emsg = ("Stack {0}: Saved stale message with remote {1}"
                                                "\n".format(self.stack.name,
                                                            self.name))
        console.concise(emsg)

    def sendSavedMessages(self):
        '''
        Message is Messenger compatible transaction
        Save stale initiated message for retransmitting later after new session is established
        '''
        while self.messages:
            body = self.messages.popleft()
            self.stack.message(body, uid=self.uid)
            emsg = ("Stack {0}: Resent saved message with remote {1}"
                                        "\n".format(self.stack.name, self.name))
            console.concise(emsg)

    def allowInProcess(self):
        '''
        Returns list of transactions for all allow transactions with this remote
        that are already in process
        '''
        return ([t for t in self.transactions.values()
                     if t.kind == TrnsKind.allow])

    def joinInProcess(self):
        '''
        Returns  list of transactions for all join transaction with this remote
        that are already in process
        '''
        return ([t for t in self.transactions.values()
                     if t.kind == TrnsKind.join])

