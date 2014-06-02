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

class Lot(object):
    '''
    RAET protocol stack endpoint
    '''
    Count = 0

    def __init__(self, stack=None, uid=None, name="", ha=None, sid=0):
        '''
        Setup Lot instance
        '''
        self.stack = stack
        Lot.Count += 1
        if uid is None:
            uid = Lot.Count
        self._uid = uid
        self.name = name or "lot{0}".format(self._uid)
        self._ha = ha
        self.sid = sid # current session ID

    @property
    def uid(self):
        '''
        property that returns unique identifier
        '''
        return self._uid

    @uid.setter
    def uid(self, value):
        '''
        setter for uid property
        '''
        self._uid = value

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


class LocalLot(Lot):
    '''
    Raet protocol local endpoint
    '''
    def  __init__(self, stack=None, name="", **kwa):
        '''
        Setup instance
        '''
        super(LocalLot, self).__init__(stack=stack, name=name, **kwa)
