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
    Uid = 0

    def __init__(self, stack=None, uid=None, name="", ha=None):
        '''
        Setup Lot instance
        '''
        Lot.Uid += 1
        self._uid = 0
        if uid is None:
            uid = Lot.Uid
        self.uid = uid
        self.stack = stack  # Stack object that manages this estate
        self.name = name or "lot{0}".format(self.uid)
        self.ha = self.ha

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
