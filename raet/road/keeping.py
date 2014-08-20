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
    LocalFields = ['uid', 'name', 'ha', 'sid', 'nuid', 'role', 'sighex','prihex']
    LocalDumpFields = ['uid', 'name', 'ha', 'sid', 'nuid', 'role']
    LocalRoleFields = ['role', 'sighex','prihex']
    RemoteFields = ['uid', 'name', 'ha', 'sid', 'joined',
                         'role', 'acceptance', 'verhex', 'pubhex']
    RemoteDumpFields = ['uid', 'name', 'ha', 'sid', 'joined','role']
    RemoteRoleFields = ['role', 'acceptance', 'verhex', 'pubhex']
    Auto = raeting.autoModes.never #auto accept

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
        data = odict([(key, None) for key in self.LocalRoleFields])
        if not os.path.exists(self.localrolepath):
            return data
        data.update(self.load(self.localrolepath))
        return data

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
        data = odict([(key, None) for key in self.RemoteRoleFields])
        filepath = os.path.join(self.roledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))
        if not os.path.exists(filepath):
            return data
        data.update(self.load(filepath))
        return data

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
        roleData = self.loadLocalRoleData() # if not present defaults None values
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
        roleData = self.loadRemoteRoleData(role) # if not found defaults to None values

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
                        ('sid', local.sid),
                        ('nuid', local.stack.nuid),
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

    def statusRemote(self, remote, verhex, pubhex, main=True, dump=True, extant=False):
        '''
        Calls statusRole and updates remote appropriately

        Returns status
        Where status is acceptance status of role and provided keys
        and has value from raeting.acceptances


        Evaluate acceptance status of estate per its keys
        persist key data differentially based on status

        extant is flag to only update status and acceptance if roleData in preexistent
        Otherwise do nothing and return None
        '''
        status, change = self.statusRole(remote.role, verhex=verhex, pubhex=pubhex,
                                         main=main, dump=dump, extant=extant)

        if status != raeting.acceptances.rejected:
            # update changed keys if any when accepted or pending
            if (verhex and verhex != remote.verfer.keyhex):
                remote.verfer = nacling.Verifier(verhex)
            if (pubhex and pubhex != remote.pubber.keyhex):
                remote.pubber = nacling.Publican(pubhex)

        if change:
            remote.acceptance = status

        return status

    def statusRole(self, role, verhex, pubhex, main=True, dump=True, extant=False):
        '''
        Returns duple of (status, change)
        Where status is acceptance status of role and provided keys
        and has value from raeting.acceptances
        Where change is flag True or False  to indicate that the associated
        remote.acceptance should be changed to status

        Evaluate acceptance status of estate per its keys
        persist key data differentially based on status

        extant is flag to only update status and acceptance if roleData in preexistent
        Otherwise do nothing and return None
        '''
        change = False

        data = self.loadRemoteRoleData(role)
        if extant:
            if (not data.get('acceptance') and
                not data.get('verhex') and
                not data.get('pubhex')):
                return None

        status = data.get('acceptance') if data else None # pre-existing status

        if main: #main estate logic
            if self.auto == raeting.autoModes.always:
                status = raeting.acceptances.accepted
                change = True

            elif self.auto == raeting.autoModes.once:
                if status is None: # first time so accept once
                    status = raeting.acceptances.accepted
                    change = True

                elif status == raeting.acceptances.accepted:
                    # already been accepted if keys not match then reject
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.rejected
                    else: # reapply existing status
                        change = True

                elif status == raeting.acceptances.pending:
                    # already pending prior mode of never if keys not match then reject
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.rejected
                    else: # in once mode convert pending to accepted
                        status = raeting.acceptances.accepted
                        change = True

                else: # status == raeting.acceptances.rejected
                    change = True

            elif self.auto == raeting.autoModes.never:
                if status is None: # first time so pend
                    status = raeting.acceptances.pending
                    change = True

                elif status == raeting.acceptances.accepted:
                    # already been accepted if keys not match then reject
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.rejected
                    else: # reapply existing status
                        change = True

                elif status == raeting.acceptances.pending:
                    # already pending if keys not match then reject
                    if (data and (
                            (verhex != data.get('verhex')) or
                            (pubhex != data.get('pubhex')) )):
                        status = raeting.acceptances.rejected
                    else: # stay pending
                        change = True

                else: # status == raeting.acceptances.rejected
                    change = True

        else: #other estate logic same as once.
            if status is None:
                status = raeting.acceptances.accepted
                change = True

            elif status == raeting.acceptances.accepted:
                if (  data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = raeting.acceptances.rejected
                    # do not change acceptance since old keys kept and were accepted
                else: #in case new remote
                    change = True

            elif status == raeting.acceptances.pending:
                # already pending prior mode of never if keys not match then reject
                if (data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = raeting.acceptances.rejected
                else: # in once mode convert pending to accepted
                    status = raeting.acceptances.accepted
                    change = True

            else: # status == raeting.acceptances.rejected
                change = True

        if dump:
            # update changed keys if any when accepted or pending
            if status != raeting.acceptances.rejected:
                if (verhex and verhex != data.get('verhex')):
                    data['verhex'] = verhex
                if (pubhex and pubhex != data.get('pubhex')):
                    data['pubhex'] = pubhex
            if change:
                data['acceptance'] = status

            if self.verifyRemoteData(data, remoteFields=self.RemoteRoleFields):
                self.dumpRemoteRoleData(data, role)

        return (status, change)

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

