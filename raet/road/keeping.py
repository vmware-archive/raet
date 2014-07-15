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
from .. import nacling
from .. import keeping

from ioflo.base.consoling import getConsole
console = getConsole()

class RoadKeep(keeping.Keep):
    '''
    RAET protocol estate on road data persistence for a given estate
    road specific data but not key data

    road/
        keep/
            stackname/
                local/
                    estate.ext
                remote/
                    estate.name.ext
                    estate.name.ext
    '''
    LocalFields = ['uid', 'name', 'ha', 'main', 'sid', 'neid', 'sighex', 'prihex', 'auto']
    RemoteFields = ['uid', 'name', 'ha', 'sid', 'joined', 'acceptance', 'verhex', 'pubhex']
    Auto = False #auto accept

    def __init__(self, prefix='estate', auto=None, **kwa):
        '''
        Setup RoadKeep instance
        '''
        super(RoadKeep, self).__init__(prefix=prefix, **kwa)
        self.auto = auto if auto is not None else self.Auto

    def dumpLocal(self, local):
        '''
        Dump local estate
        '''
        data = odict([
                        ('uid', local.uid),
                        ('name', local.name),
                        ('ha', local.ha),
                        ('main', local.main),
                        ('sid', local.sid),
                        ('neid', local.neid),
                        ('sighex', local.signer.keyhex),
                        ('prihex', local.priver.keyhex),
                        ('auto', self.auto),
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
                        ('sid', remote.sid),
                        ('joined', remote.joined),
                        ('acceptance', remote.acceptance),
                        ('verhex', remote.verfer.keyhex),
                        ('pubhex', remote.pubber.keyhex),
                    ])
        if self.verifyRemoteData(data):
            self.dumpRemoteData(data, remote.name)

    def statusRemote(self, remote, verhex, pubhex, main=True):
        '''
        Evaluate acceptance status of estate per its keys
        persist key data differentially based on status
        '''
        data = self.loadRemoteData(remote.name)
        status = data.get('acceptance') if data else None # pre-existing status

        if main: #main estate logic
            if self.auto:
                status = raeting.acceptances.accepted
                remote.acceptance = status
            else:
                if status is None:
                    status = raeting.acceptances.pending
                    remote.acceptance = status

                elif status == raeting.acceptances.accepted:
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.rejected
                    else: #in case new remote
                        remote.acceptance = status

                elif status == raeting.acceptances.rejected:
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.pending
                        remote.acceptance = status

                else: # pre-existing was pending
                    # waiting for external acceptance
                    remote.acceptance = status

        else: #other estate logic
            if status is None:
                status = raeting.acceptances.accepted
                remote.acceptance = status #change acceptance auto accept new keys

            elif status == raeting.acceptances.accepted:
                if (  data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = raeting.acceptances.rejected
                    # do not change acceptance since old keys kept and were accepted
                else: #in case new remote
                    remote.acceptance = status

            elif status == raeting.acceptances.rejected:
                if (  data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = raeting.acceptances.accepted
                    remote.acceptance = status #change acceptance since new keys
            else: # pre-existing was pending
                status = raeting.acceptances.accepted
                remote.acceptance = status # change acceptance since keys now accepted

        if status != raeting.acceptances.rejected: # save new accepted keys
            if (verhex and verhex != remote.verfer.keyhex):
                remote.verfer = nacling.Verifier(verhex)
            if (pubhex and pubhex != remote.pubber.keyhex):
                remote.pubber = nacling.Publican(pubhex)

        self.dumpRemote(remote)
        return status

    def rejectRemote(self, remote):
        '''
        Set acceptance status to rejected
        '''
        remote.acceptance = raeting.acceptances.rejected
        self.dumpRemote(remote)

    def pendRemote(self, remote):
        '''
        Set acceptance status to pending
        '''
        remote.acceptance = raeting.acceptances.pending
        self.dumpRemote(remote)

    def acceptRemote(self, remote):
        '''
        Set acceptance status to accepted
        '''
        remote.acceptance = raeting.acceptances.accepted
        self.dumpRemote(remote)

def clearAllKeep(dirpath):
    '''
    Convenience function to clear all road keep data in dirpath
    '''
    road = RoadKeep(dirpath=dirpath)
    road.clearLocalData()
    road.clearAllRemoteData()

