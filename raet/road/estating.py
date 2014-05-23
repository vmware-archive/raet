# -*- coding: utf-8 -*-
'''
estating.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611

import socket

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
                 eid=None,
                 name="",
                 sid=0,
                 tid=0,
                 host="",
                 port=raeting.RAET_PORT,
                 ha=None,
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

        self.sid = sid # current session ID
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

    def nextSid(self):
        '''
        Generates next session id number.
        '''
        self.sid += 1
        if self.sid > 0xffffffffL:
            self.sid = 1  # rollover to 1
        return self.sid

    def validSid(self, sid):
        '''
        Compare new sid to old .sid and return True if new is greater than old
        modulo N where N is 2^32 = 0x100000000
        And greater means the difference is less than N/2
        '''
        return (((sid - self.sid) % 0x100000000) < (0x100000000 // 2))

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
        if not name and stack:
            name = stack.name

        super(LocalEstate, self).__init__(stack=stack, name=name, **kwa)
        self.main = True if main else False # main estate for road
        self.signer = nacling.Signer(sigkey)
        self.priver = nacling.Privateer(prikey) # Long term key

class RemoteEstate(Estate):
    '''
    RAET protocol endpoint remote estate object
    Maintains verifier for verifying signatures and publican for encrypt/decrypt
    '''
    Period = 1.0
    Offset = 0.5

    def __init__(self, stack, verkey=None, pubkey=None, acceptance=None,
                 rsid=0, rtid=0, period=None, offset=None, **kwa):
        '''
        Setup Estate instance

        stack is required parameter for RemoteEstate unlike its superclass

        verkey is either nacl VerifyKey or raw or hex encoded key
        pubkey is either nacl PublicKey or raw or hex encoded key
        '''
        if 'host' not in kwa and 'ha' not in kwa:
            kwa['ha'] = ('127.0.0.1', raeting.RAET_TEST_PORT)
        super(RemoteEstate, self).__init__(stack, **kwa)
        self.joined = None
        self.allowed = None
        self.alived = None
        self.acceptance = acceptance
        self.privee = nacling.Privateer() # short term key manager
        self.publee = nacling.Publican() # correspondent short term key  manager
        self.verfer = nacling.Verifier(verkey) # correspondent verify key manager
        self.pubber = nacling.Publican(pubkey) # correspondent long term key manager

        self.rsid = rsid # last sid received from remote when RmtFlag is True
        self.rtid = rtid # last tid received from remote when RmtFlag is True
        self.indexes = set() # indexes to outstanding transactions for this remote

        # persistence keep alive heatbeat timer. Initial duration has offset so
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

    def rekey(self):
        '''
        Regenerate short term keys
        '''
        self.allowed = None
        self.privee = nacling.Privateer() # short term key
        self.publee = nacling.Publican() # correspondent short term key  manager

    def validRsid(self, rsid):
        '''
        Compare new rsid to old .rsid and return True if new is greater than old
        modulo N where N is 2^32 = 0x100000000
        And greater means the difference is less than N/2
        '''
        return (((rsid - self.rsid) % 0x100000000) < (0x100000000 // 2))

    def refresh(self, alived=True):
        '''
        Restart presence heartbeat timer
        '''
        self.timer.restart(duration=self.period)
        self.alived = alived

    def manage(self, cascade=False, immediate=False):
        '''
        Perform time based processing of keep alive heatbeat
        '''
        if immediate or self.timer.expired:
            self.timer.restart(duration=self.period)
            self.stack.alive(deid=self.uid, cascade=cascade)

