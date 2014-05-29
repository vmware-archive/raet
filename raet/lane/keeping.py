# -*- coding: utf-8 -*-
'''
keeping.py raet protocol keep classes
'''
# pylint: skip-file
# pylint: disable=W0611

# Import python libs
import os
from collections import deque

try:
    import simplejson as json
except ImportError:
    import json

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding

from .. import raeting
from .. import keeping

from ioflo.base.consoling import getConsole
console = getConsole()

class LaneKeep(keeping.Keep):
    '''
    RAET protocol yard on lane data persistence for a given yeard

    keep/
        stackname/
            local/
                yard.ext
            remote/
                yard.name.ext
                yard.name.ext
    '''
    LocalFields = ['uid', 'name', 'ha', 'main', 'mid', 'lanename', 'nyid', 'accept']
    RemoteFields = ['uid', 'name', 'ha', 'mid',  'rmid']

    def __init__(self, prefix='yard', **kwa):
        '''
        Setup LaneKeep instance
        '''
        super(LaneKeep, self).__init__(prefix=prefix, **kwa)

    def dumpLocal(self, local):
        '''
        Dump local estate
        '''
        data = odict([
                        ('uid', local.uid),
                        ('name', local.name),
                        ('ha', local.ha),
                        ('main', local.main),
                        ('mid', local.mid),
                        ('lanename', local.lanename),
                        ('nyid', local.stack.nyid),
                        ('accept', local.stack.accept),
                    ])
        if self.verifyLocalData(data):
            self.dumpLocalData(data)

    def dumpRemote(self, remote):
        '''
        Dump remote estate
        '''
        data = odict([
                        ('uid', remote.uid),
                        ('name', remote.name),
                        ('ha', remote.ha),
                        ('mid', remote.mid),
                        ('rmid', remote.rmid),
                    ])
        if self.verifyRemoteData(data):
            self.dumpRemoteData(data, remote.uid)

def clearAllKeep(dirpath):
    '''
    Convenience function to clear all lane keep data in dirpath
    '''
    keep = LaneKeep(dirpath=dirpath)
    keep.clearLocalData()
    keep.clearAllRemoteData()
