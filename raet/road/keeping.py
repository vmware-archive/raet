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

    keep/
        stackname/
            local/
                estate.ext
                role.ext
            remote/
                estate.name.ext
                estate.name.ext
            role/
                role.role.ext
                role.role.ext
    '''
    LocalFields = ['uid', 'name', 'ha', 'main', 'sid', 'neid',
                         'auto', 'role', 'sighex','prihex']
    LocalDumpFields = ['uid', 'name', 'ha', 'main', 'sid', 'neid', 'auto', 'role']
    LocalRoleFields = ['role', 'sighex','prihex']
    RemoteFields = ['uid', 'name', 'ha', 'sid', 'joined',
                         'role', 'acceptance', 'verhex', 'pubhex']
    RemoteDumpFields = ['uid', 'name', 'ha', 'sid', 'joined','role']
    RemoteRoleFields = ['role', 'acceptance', 'verhex', 'pubhex']
    Auto = False #auto accept

    def __init__(self, prefix='estate', auto=None, **kwa):
        '''
        Setup RoadKeep instance
        '''
        super(RoadKeep, self).__init__(prefix=prefix, **kwa)
        self.auto = auto if auto is not None else self.Auto

        self.localrolepath = os.path.join(self.localdirpath,
                "{0}.{1}".format('role', self.ext))

        self.roledirpath = os.path.join(self.dirpath, 'role')
        if not os.path.exists(self.roledirpath):
            os.makedirs(self.roledirpath)

    def dumpLocalRoleData(self, data):
        '''
        Dump the local role data to file
        '''
        self.dump(data, self.localrolepath)

    def loadLocalRoleData(self):
        '''
        Load and Return the role data from the localrolefile
        '''
        if not os.path.exists(self.localrolepath):
            return None
        return (self.load(self.localrolepath))

    def clearLocalRoleData(self):
        '''
        Clear the local file
        '''
        if os.path.exists(self.localrolepath):
            os.remove(self.localrolepath)

    def dumpRemoteRoleData(self, data, role):
        '''
        Dump the role data to file
        '''
        filepath = os.path.join(self.roledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))

        self.dump(data, filepath)

    def dumpAllRemoteRoleData(self, roles):
        '''
        Dump the data in the roles keyed by role to role data files
        '''
        for role, data in roles.items():
            self.dumpRemoteRoleData(data, role)

    def loadRemoteRoleData(self, role):
        '''
        Load and Return the data from the role file
        '''
        filepath = os.path.join(self.roledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))
        if not os.path.exists(filepath):
            return None
        return (self.load(filepath))

    def loadAllRemoteRoleData(self):
        '''
        Load and Return the roles dict from the all the role data files
        indexed by role in filenames
        '''
        roles = odict()
        for filename in os.listdir(self.roledirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, role = root.partition('.')
            if not role or prefix != 'role':
                continue
            filepath = os.path.join(self.roledirpath, filename)
            roles[role] = self.load(filepath)
        return roles

    def clearRemoteRoleData(self, role):
        '''
        Clear data from the role data file
        '''
        filepath = os.path.join(self.roledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))
        if os.path.exists(filepath):
            os.remove(filepath)

    def clearAllRemoteRoleData(self):
        '''
        Remove all the role data files
        '''
        for filename in os.listdir(self.roledirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, role = root.partition('.')
            if not role or prefix != 'role':
                continue
            filepath = os.path.join(self.roledirpath, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    def clearRemoteRoleDir(self):
        '''
        Clear the Role directory
        '''
        if os.path.exists(self.roledirpath):
            os.rmdir(self.roledirpath)

    def loadLocalData(self):
        '''
        Load and Return the data from the local estate
        '''

        data = super(RoadKeep, self).loadLocalData()
        if not data:
            return None
        roleData = self.loadLocalRoleData() or {}
        data.update(sighex=roleData.get('sighex'), prihex=roleData.get('prihex'))
        return data

    def clearLocalData(self):
        '''
        Clear the local files
        '''
        if os.path.exists(self.localfilepath):
            os.remove(self.localfilepath)
        if os.path.exists(self.localrolepath):
            os.remove(self.localrolepath)

    def loadRemoteData(self, name):
        '''
        Load and Return the data from the remote file
        '''
        data = super(RoadKeep, self).loadRemoteData(name)
        if not data:
            return None

        role = data['role']
        roleData = self.loadRemoteRoleData(role) or odict()

        data.update(acceptance=roleData.get('acceptance'),
                    verhex=roleData.get('verhex'),
                    pubhex=roleData.get('pubhex'))
        return data

    def loadAllRemoteData(self):
        '''
        Load and Return the data from the all the remote estate files
        '''
        keeps = super(RoadKeep, self).loadAllRemoteData()
        roles = self.loadAllRemoteRoleData()
        for name, data in keeps.items():
            role = data['role']
            roleData = roles.get(role, odict(acceptance=None,
                                             verhex=None,
                                             pubhex=None))
            keeps[name].update(acceptance=roleData['acceptance'],
                               verhex=roleData['verhex'],
                               pubhex=roleData['pubhex'])
        return keeps

    def clearAllRemoteData(self):
        '''
        Remove all the remote estate files
        '''
        super(RoadKeep, self).clearAllRemoteData()
        self.clearAllRemoteRoleData()

    def clearRemoteDir(self):
        '''
        Clear the remote directory
        '''
        super(RoadKeep, self).clearRemoteDir()
        self.clearRemoteRoleDir()

    def dumpLocalRole(self, local):
        '''
        Dump role data for local
        '''
        data = odict([
                            ('role', local.role),
                            ('sighex', local.signer.keyhex),
                            ('prihex', local.priver.keyhex),
                         ])
        if self.verifyLocalData(data, localFields =self.LocalRoleFields):
            self.dumpLocalRoleData(data)

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
                        ('auto', self.auto),
                        ('role', local.role),
                    ])
        if self.verifyLocalData(data, localFields =self.LocalDumpFields):
            self.dumpLocalData(data)

        self.dumpLocalRole(local)


    def dumpRemoteRole(self, remote):
        '''
        Dump the role data for remote
        '''
        data = odict([
                            ('role', remote.role),
                            ('acceptance', remote.acceptance),
                            ('verhex', remote.verfer.keyhex),
                            ('pubhex', remote.pubber.keyhex),
                        ])
        if self.verifyRemoteData(data, remoteFields=self.RemoteRoleFields):
            self.dumpRemoteRoleData(data, remote.role)

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
                        ('role', remote.role),
                    ])
        if self.verifyRemoteData(data, remoteFields=self.RemoteDumpFields):
            self.dumpRemoteData(data, remote.name)

        self.dumpRemoteRole(remote)

    def replaceRemoteRole(self, remote, old):
        '''
        Replace old role when remote.role has changed
        '''
        new = remote.role
        if new != old:
            data = odict(role=remote.role,
                             acceptance=remote.acceptance,
                             verhex=remote.verhex,
                             pubhex=remote.pubhex)
            self.dumpRemoteRoleData(data, remote.role)

            self.clearRemoteRoleData(old) # now delete old role file

    def statusRemote(self, remote, verhex, pubhex, main=True, dump=True):
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

        if dump:
            self.dumpRemoteRole(remote)
        return status

    def rejectRemote(self, remote):
        '''
        Set acceptance status to rejected
        '''
        remote.acceptance = raeting.acceptances.rejected
        self.dumpRemoteRole(remote)

    def pendRemote(self, remote):
        '''
        Set acceptance status to pending
        '''
        remote.acceptance = raeting.acceptances.pending
        self.dumpRemoteRole(remote)

    def acceptRemote(self, remote):
        '''
        Set acceptance status to accepted
        '''
        remote.acceptance = raeting.acceptances.accepted
        self.dumpRemoteRole(remote)

def clearAllKeep(dirpath):
    '''
    Convenience function to clear all road keep data in dirpath
    '''
    road = RoadKeep(dirpath=dirpath)
    road.clearLocalData()
    road.clearAllRemoteData()

