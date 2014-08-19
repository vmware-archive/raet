# -*- coding: utf-8 -*-
'''
lotting.py provides base class for stack endpoint interface objects
defines interface protocol that stack objects depend on

Lot subclasses or objects that follow Lot protocol must have following
attributes or properties that are both gettable and settable.

.stack
.name
.uid
.ha

'''
# pylint: skip-file
# pylint: disable=W0611

# Import ioflo libs
from ioflo.base.odicting import odict

from ioflo.base.consoling import getConsole
console = getConsole()

from . import raeting

class Lot(object):
    '''
    RAET protocol stack endpoint
    way is group of lots
    '''
    Uid = 0

    def __init__(self, stack=None, uid=None, name='', ha=None, sid=0):
        '''
        Setup Lot instance
        '''
        self.stack = stack
        self.uid = uid if uid is not None else 0
        self.name = name or "lot{0}".format(self.uid)
        self._ha = ha
        self.sid = sid # current session ID

    @property
    def ha(self):
        '''
        property that returns host address
        '''
        return self._ha

    @ha.setter
    def ha(self, value):
        self._ha = value

    def nextSid(self):
        '''
        Generates next session id number.
        Follover at wrap modulor (N-1) = 2^32 -1 = 0xffffffff
        '''
        self.sid += 1
        if self.sid > raeting.SID_ROLLOVER: #0xffffffff
            self.sid = 1  # rollover to 1 as 0 is special
        return self.sid

    def validSid(self, sid):
        '''
        Compare new sid to old .sid and return True
        If new is >= old modulo N where N is 2^32 = 0x100000000
        And >= means the difference is less than N//2 = 0x80000000
        (((new - old) % 0x100000000) < (0x100000000 // 2))
        '''
        return self.validateSid(new=sid, old=self.sid)

    @staticmethod
    def validateSid(new, old):
        '''
        Compare new sid to old sid and return True
        If old is zero Then new is always valid
        If new is >= old modulo N where N is 2^32 = 0x100000000
        And greater means the difference is less than N//2 = 0x80000000

        '''
        if not old: # if current sid is 0 then always valid
            return True
        return (((new - old) % raeting.SID_WRAP_MODULO) <
                                             (raeting.SID_WRAP_DELTA))

class LocalLot(Lot):
    '''
    Raet protocol local endpoint
    '''
    def  __init__(self, stack=None, nuid=None, uid=None, main=None, **kwa):
        '''
        Setup instance
        '''
        if nuid is None:
            if stack:
                nuid = stack.Uid
            else:
                nuid = 1
        self.nuid = nuid

        uid = uid if uid is not None else self.nextUid()

        super(LocalLot, self).__init__(stack=stack, uid=uid, **kwa)
        self.main = main # main lot on way

    def nextUid(self):
        '''
        Generates next unique id number for local or remotes.
        '''
        self.nuid += 1
        if self.nuid > 0xffffffffL:
            self.nuid = 1  # rollover to 1
        return self.nuid
