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
from ioflo.aid.odicting import odict

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import AutoMode, Acceptance
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
    LocalFields = ['name', 'uid', 'ha', 'iha', 'natted', 'fqdn', 'dyned', 'sid',
                   'puid', 'aha', 'role', 'sighex','prihex']
    LocalDumpFields = ['name', 'uid', 'ha', 'iha', 'natted', 'fqdn', 'dyned', 'sid',
                       'puid', 'aha', 'role']
    LocalRoleFields = ['role', 'sighex','prihex']
    RemoteFields = ['name', 'uid', 'fuid', 'ha', 'iha', 'natted', 'fqdn', 'dyned',
                    'sid', 'main', 'kind', 'joined',
                    'role', 'acceptance', 'verhex', 'pubhex']
    RemoteDumpFields = ['name', 'uid', 'fuid', 'ha', 'iha', 'natted', 'fqdn', 'dyned',
                         'sid', 'main', 'kind', 'joined', 'role']
    RemoteRoleFields = ['role', 'acceptance', 'verhex', 'pubhex']
    Auto = AutoMode.never.value #auto accept

    def __init__(self,
                 stackname='stack',
                 prefix='estate',
                 auto=None,
                 baseroledirpath='',
                 roledirpath='',
                 **kwa):
        '''
        Setup RoadKeep instance
        '''
        super(RoadKeep, self).__init__(stackname=stackname,
                                       prefix=prefix,
                                       **kwa)
        self.auto = auto if auto is not None else self.Auto

        if not roledirpath:
            if baseroledirpath:
                roledirpath = os.path.join(baseroledirpath, stackname, 'role')
            else:
                roledirpath = os.path.join(self.dirpath, 'role')
        roledirpath = os.path.abspath(os.path.expanduser(roledirpath))

        if not os.path.exists(roledirpath):
            try:
                os.makedirs(roledirpath)
            except OSError as ex:
                roledirpath = os.path.join(self.AltKeepDir, stackname, 'role')
                roledirpath = os.path.abspath(os.path.expanduser(roledirpath))
                if not os.path.exists(roledirpath):
                    os.makedirs(roledirpath)
        else:
            if not os.access(roledirpath, os.R_OK | os.W_OK):
                roledirpath = os.path.join(self.AltKeepDir, stackname, 'role')
                roledirpath = os.path.abspath(os.path.expanduser(roledirpath))
                if not os.path.exists(roledirpath):
                    os.makedirs(roledirpath)

        self.roledirpath = roledirpath

        remoteroledirpath = os.path.join(self.roledirpath, 'remote')
        if not os.path.exists(remoteroledirpath):
            os.makedirs(remoteroledirpath)
        self.remoteroledirpath = remoteroledirpath

        localroledirpath = os.path.join(self.roledirpath, 'local')
        if not os.path.exists(localroledirpath):
            os.makedirs(localroledirpath)
        self.localroledirpath = localroledirpath

        self.localrolepath = os.path.join(self.localroledirpath,
                "{0}.{1}".format('role', self.ext))

    def clearAllDir(self):
        '''
        Clear all keep directories
        '''
        super(RoadKeep, self).clearAllDir()
        self.clearRoleDir()

    def clearRoleDir(self):
        '''
        Clear the Role directory
        '''
        if os.path.exists(self.roledirpath):
            os.rmdir(self.roledirpath)

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

    def clearLocalRoleDir(self):
        '''
        Clear the Local Role directory
        '''
        if os.path.exists(self.localroledirpath):
            os.rmdir(self.localroledirpath)

    def dumpRemoteRoleData(self, data, role):
        '''
        Dump the role data to file
        '''
        filepath = os.path.join(self.remoteroledirpath,
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
        filepath = os.path.join(self.remoteroledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))
        if not os.path.exists(filepath):
            data.update(role=role)
            return data
        data.update(self.load(filepath))
        return data

    def loadAllRemoteRoleData(self):
        '''
        Load and Return the roles dict from the all the role data files
        indexed by role in filenames
        '''
        roles = odict()
        for filename in os.listdir(self.remoteroledirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, role = root.partition('.')
            if not role or prefix != 'role':
                continue
            filepath = os.path.join(self.remoteroledirpath, filename)
            roles[role] = self.load(filepath)
        return roles

    def clearRemoteRoleData(self, role):
        '''
        Clear data from the role data file
        '''
        filepath = os.path.join(self.remoteroledirpath,
                "{0}.{1}.{2}".format('role', role, self.ext))
        if os.path.exists(filepath):
            os.remove(filepath)

    def clearAllRemoteRoleData(self):
        '''
        Remove all the role data files
        '''
        for filename in os.listdir(self.remoteroledirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, role = root.partition('.')
            if not role or prefix != 'role':
                continue
            filepath = os.path.join(self.remoteroledirpath, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    def clearRemoteRoleDir(self):
        '''
        Clear the Remote Role directory
        '''
        if os.path.exists(self.remoteroledirpath):
            os.rmdir(self.remoteroledirpath)

    def loadLocalData(self):
        '''
        Load and Return the data from the local estate
        '''

        data = super(RoadKeep, self).loadLocalData()
        if not data:
            return None
        roleData = self.loadLocalRoleData() # if not present defaults None values
        data.update([('sighex', roleData.get('sighex')),
                     ('prihex', roleData.get('prihex'))])
        return data

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
            roleData = roles.get(role, odict([('acceptance', None),
                                              ('verhex', None),
                                              ('pubhex', None)]) )
            keeps[name].update([('acceptance', roleData['acceptance']),
                                 ('verhex', roleData['verhex']),
                                 ('pubhex', roleData['pubhex'])])
        return keeps

    def dumpLocalRole(self, local):
        '''
        Dump role data for local
        '''
        data = odict([
                            ('role', local.role),
                            ('sighex', local.signer.keyhex),
                            ('prihex', local.priver.keyhex),
                         ])
        if self.verifyLocalData(data, localFields=self.LocalRoleFields):
            self.dumpLocalRoleData(data)

    def dumpLocal(self, local):
        '''
        Dump local estate
        '''
        data = odict([
                        ('name', local.name),
                        ('uid', local.uid),
                        ('ha', local.ha),
                        ('iha', local.iha),
                        ('natted', local.natted),
                        ('fqdn', local.fqdn),
                        ('dyned', local.dyned),
                        ('sid', local.sid),
                        ('puid', local.stack.puid),
                        ('aha', local.stack.aha),
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
                            ('verhex', str(remote.verfer.keyhex.decode('ISO-8859-1'))),
                            ('pubhex', str(remote.pubber.keyhex.decode('ISO-8859-1'))),
                        ])
        if self.verifyRemoteData(data, remoteFields=self.RemoteRoleFields):
            self.dumpRemoteRoleData(data, remote.role)

    def dumpRemote(self, remote):
        '''
        Dump remote estate
        '''
        data = odict([
                        ('name', remote.name),
                        ('uid', remote.uid),
                        ('fuid', remote.fuid),
                        ('ha', remote.ha),
                        ('iha', remote.iha),
                        ('natted', remote.natted),
                        ('fqdn', remote.fqdn),
                        ('dyned', remote.dyned),
                        ('sid', remote.sid),
                        ('main', remote.main),
                        ('kind', remote.kind),
                        ('joined', remote.joined),
                        ('role', remote.role),
                    ])
        if self.verifyRemoteData(data, remoteFields=self.RemoteDumpFields):
            self.dumpRemoteData(data, remote.name)

        self.dumpRemoteRole(remote)

    def statusRemote(self, remote, dump=True):
        '''
        Calls .statusRole on remote role and keys and updates remote.acceptance
        dump indicates if statusRole should update persisted values when
        appropriate.

        Returns status
        Where status is acceptance status of role and keys
        and has value from raeting.acceptances
        '''
        status = self.statusRole(role=remote.role,
                                 verhex=str(remote.verfer.keyhex.decode('ISO-8859-1')),
                                 pubhex=str(remote.pubber.keyhex.decode('ISO-8859-1')),
                                 dump=dump, )

        remote.acceptance = status

        return status

    def statusRole(self, role, verhex, pubhex, dump=True):
        '''
        Returns status

        Where status is acceptance status of role and keys
        and has value from raeting.acceptances

        If dump  when appropriate
        Then persist key data differentially based on status

        In many cases a status of rejected is returned because the provided keys are
        different but this does not change the acceptance status for
        the persisted keys which keys were not changed.

        Persisted status is only set to rejected by an outside entity. It is never
        set to rejected by this function, that is, a status of rejected may be returned
        but the persisted status on disk is not changed to rejected.
        '''
        data = self.loadRemoteRoleData(role)
        status = data.get('acceptance') if data else None # pre-existing status

        if self.auto == AutoMode.always:
            status = Acceptance.accepted.value

        elif self.auto == AutoMode.once:
            if status is None: # first time so accept once
                status = Acceptance.accepted.value

            elif status == Acceptance.accepted:
                # already been accepted if keys not match then reject
                if (data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = Acceptance.rejected.value
                    console.concise("Rejection Reason: Once keys not match prior accepted.\n")

            elif status == Acceptance.pending:
                # already pending prior mode of never if keys not match then reject
                if (data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = Acceptance.rejected.value
                    console.concise("Rejection Reason: Once keys not match prior pended.\n")
                else: # in once mode convert pending to accepted
                    status = Acceptance.accepted.value
            else:
                console.concise("Rejection Reason: Once keys already rejected.\n")

        elif self.auto == AutoMode.never:
            if status is None: # first time so pend
                status = Acceptance.pending.value

            elif status == Acceptance.accepted:
                # already been accepted if keys not match then reject
                if (data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = Acceptance.rejected.value
                    console.concise("Rejection Reason: Never keys not match prior accepted.\n")

            elif status == Acceptance.pending:
                # already pending if keys not match then reject
                if (data and (
                        (verhex != data.get('verhex')) or
                        (pubhex != data.get('pubhex')) )):
                    status = Acceptance.rejected.value
                    console.concise("Rejection Reason: Never keys not match prior pended.\n")
            else:
                console.concise("Rejection Reason: Never keys already rejected.\n")

        else: # unrecognized autoMode
            raise raeting.KeepError("Unrecognized auto mode '{0}'".format(self.auto))

        if dump:
            dirty = False
            # update changed keys if any when accepted or pending
            if status != Acceptance.rejected:
                if (verhex and verhex != data.get('verhex')):
                    data['verhex'] = verhex
                    dirty = True
                if (pubhex and pubhex != data.get('pubhex')):
                    data['pubhex'] = pubhex
                    dirty = True
                if status != data.get('acceptance'):
                    data['acceptance'] = status
                    dirty = True

            if dirty and self.verifyRemoteData(data,
                                               remoteFields=self.RemoteRoleFields):
                self.dumpRemoteRoleData(data, role)

        return status

    def rejectRemote(self, remote):
        '''
        Set acceptance status to rejected
        '''
        remote.acceptance = Acceptance.rejected.value
        self.dumpRemoteRole(remote)

    def pendRemote(self, remote):
        '''
        Set acceptance status to pending
        '''
        remote.acceptance = Acceptance.pending.value
        self.dumpRemoteRole(remote)

    def acceptRemote(self, remote):
        '''
        Set acceptance status to accepted
        '''
        remote.acceptance = Acceptance.accepted.value
        self.dumpRemoteRole(remote)

def clearAllKeep(dirpath):
    '''
    Convenience function to clear all road keep data in dirpath
    '''
    road = RoadKeep(dirpath=dirpath)
    road.clearLocalData()
    road.clearLocalRoleData()
    road.clearAllRemoteData()
    road.clearAllRemoteRoleData()

