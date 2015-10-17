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
from ioflo.aid.odicting import odict

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from .abiding import *  # import globals
from . import raeting, nacling

class Lot(object):
    '''
    RAET protocol stack endpoint
    way is group of lots
    '''
    Uid = 0

    def __init__(self, stack, uid=None, name='', prefix='lot', ha=None, sid=0):
        '''
        Setup Lot instance

        stack is a required parameter
        '''
        self.stack = stack
        self.name = name or "{0}_{1}".format(prefix, nacling.uuid(size=16))
        self.uid = uid if uid is not None else self.stack.nextUid()
        self.ha = ha
        self.sid = sid # current session ID

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
        If old is zero Then new is always valid
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
        And >= means the difference is less than N//2 = 0x80000000
        0 = 0 % anything
        '''
        # If old sid == 0 then new always valid. If new sid == 0 then always valid
        if not old or not new:
            return True
        return (((new - old) % raeting.SID_WRAP_MODULO) <
                                             (raeting.SID_WRAP_DELTA))
