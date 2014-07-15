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

import shutil

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding

from . import raeting
from . import nacling

from ioflo.base.consoling import getConsole
console = getConsole()

KEEP_DIR = os.path.join('/var', 'cache', 'raet', 'keep')
ALT_KEEP_DIR = os.path.join('~', '.raet', 'keep')

class Keep(object):
    '''
    RAET protocol base class for data persistence of objects that follow the Lot
    protocol
    '''
    LocalFields = ['uid', 'name', 'ha', 'sid']
    RemoteFields = ['uid', 'name', 'ha']

    def __init__(self,
                 dirpath='',
                 basedirpath='',
                 stackname='stack',
                 prefix='data',
                 ext='json',
                 **kwa):
        '''
        Setup Keep instance
        Create directories for saving associated data files
            keep/
                stackname/
                    local/
                        prefix.ext
                    remote/
                        prefix.name.ext
                        prefix.name.ext
        '''
        if not dirpath:
            if not basedirpath:
                basedirpath = KEEP_DIR
            dirpath = os.path.join(basedirpath, stackname)
        dirpath = os.path.abspath(os.path.expanduser(dirpath))

        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath)
            except OSError as ex:
                dirpath = os.path.join(ALT_KEEP_DIR, stackname)
                dirpath = os.path.abspath(os.path.expanduser(dirpath))
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)

        else:
            if not os.access(dirpath, os.R_OK | os.W_OK):
                dirpath = os.path.join(ALT_KEEP_DIR, stackname)
                dirpath = os.path.abspath(os.path.expanduser(dirpath))
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)

        self.dirpath = dirpath

        self.localdirpath = os.path.join(self.dirpath, 'local')
        if not os.path.exists(self.localdirpath):
            os.makedirs(self.localdirpath)

        self.remotedirpath = os.path.join(self.dirpath, 'remote')
        if not os.path.exists(self.remotedirpath):
            os.makedirs(self.remotedirpath)

        self.prefix = prefix
        self.ext = ext
        self.localfilepath = os.path.join(self.localdirpath,
                "{0}.{1}".format(self.prefix, self.ext))

    @staticmethod
    def dump(data, filepath):
        '''
        Write data as json to filepath
        '''
        if ' ' in filepath:
            raise raeting.KeepError("Invalid filepath '{0}' contains space")

        with aiding.ocfn(filepath, "w+") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def load(filepath):
        '''
        Return data read from filepath as converted json
        Otherwise return None
        '''
        with aiding.ocfn(filepath) as f:
            try:
                it = json.load(f, object_pairs_hook=odict)
            except EOFError:
                return None
            except ValueError:
                return None
            return it
        return None

    def clearAllDir(self):
        '''
        Clear all the directories
        '''
        # shutil.rmtree
        if os.path.exists(self.dirpath):
            shutil.rmtree(self.dirpath)

    def defaults(self):
        '''
        Return odict with items preloaded with defaults
        '''
        data = odict()
        for field in fields:
            data[field] = None
        return data

    def verifyLocalData(self, data, localFields=None):
        '''
        Returns True if the fields in .LocalFields match the fields in data
        '''
        localFields = localFields if localFields is not None else self.LocalFields
        return (set(localFields) == set(data.keys()))

    def dumpLocalData(self, data):
        '''
        Dump the local data to file
        '''
        self.dump(data, self.localfilepath)

    def loadLocalData(self):
        '''
        Load and Return the data from the local file
        '''
        if not os.path.exists(self.localfilepath):
            return None
        return (self.load(self.localfilepath))

    def clearLocalData(self):
        '''
        Clear the local file
        '''
        if os.path.exists(self.localfilepath):
            os.remove(self.localfilepath)

    def clearLocalDir(self):
        '''
        Clear the local directory
        '''
        # shutil.rmtree
        if os.path.exists(self.localdirpath):
            os.rmdir(self.localdirpath)

    def verifyRemoteData(self, data, remoteFields=None):
        '''
        Returns True if the fields in .RemoteFields match the fields in data
        '''
        remoteFields = remoteFields if remoteFields is not None else self.RemoteFields
        return (set(remoteFields) == set(data.keys()))

    def dumpRemoteData(self, data, name):
        '''
        Dump the remote data to file
        '''
        #filepath = os.path.join(self.remotedirpath,
                #"{0}.{1}.{2}".format(self.prefix, uid, self.ext))
        filepath = os.path.join(self.remotedirpath,
                "{0}.{1}.{2}".format(self.prefix, name, self.ext))

        self.dump(data, filepath)

    def dumpAllRemoteData(self, datadict):
        '''
        Dump the data in the datadict keyed by name to remote data files
        '''
        for name, data in datadict.items():
            self.dumpRemoteData(data, name)

    def loadRemoteData(self, name):
        '''
        Load and Return the data from the remote file
        '''
        #filepath = os.path.join(self.remotedirpath,
                        #"{0}.{1}.{2}".format(self.prefix, uid, self.ext))
        filepath = os.path.join(self.remotedirpath,
                "{0}.{1}.{2}".format(self.prefix, name, self.ext))
        if not os.path.exists(filepath):
            return None
        return (self.load(filepath))

    def clearRemoteData(self, name):
        '''
        Clear data from the remote data file
        '''
        #filepath = os.path.join(self.remotedirpath,
                        #"{0}.{1}.{2}".format(self.prefix, uid, self.ext))
        filepath = os.path.join(self.remotedirpath,
                "{0}.{1}.{2}".format(self.prefix, name, self.ext))
        if os.path.exists(filepath):
            os.remove(filepath)

    def clearRemoteDir(self):
        '''
        Clear the remote directory
        '''
        # shutil.rmtree
        if os.path.exists(self.remotedirpath):
            os.rmdir(self.remotedirpath)

    def loadAllRemoteData(self):
        '''
        Load and Return the datadict from the all the remote data files
        indexed by name in filenames
        '''
        datadict = odict()
        for filename in os.listdir(self.remotedirpath):
            root, ext = os.path.splitext(filename)
            if ext != '.json' or not root.startswith(self.prefix):
                continue
            prefix, sep, name = root.partition('.')
            if not name or prefix != self.prefix:
                continue
            filepath = os.path.join(self.remotedirpath, filename)
            datadict[name] = self.load(filepath)
        return datadict

    def clearAllRemoteData(self):
        '''
        Remove all the remote data files
        '''
        for filename in os.listdir(self.remotedirpath):
            root, ext = os.path.splitext(filename)
            if ext != '.json' or not root.startswith(self.prefix):
                continue
            prefix, eid = os.path.splitext(root)
            eid = eid.lstrip('.')
            if not eid:
                continue
            filepath = os.path.join(self.remotedirpath, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    def dumpLocal(self, local):
        '''
        Dump local
        '''
        data = odict([
                        ('uid', local.uid),
                        ('name', local.name),
                        ('ha', local.ha),
                        ('sid', local.sid),
                    ])
        if self.verifyLocalData(data):
            self.dumpLocalData(data)

    def dumpRemote(self, remote):
        '''
        Dump remote
        '''
        data = odict([
                        ('uid', remote.uid),
                        ('name', remote.name),
                        ('ha', remote.ha),
                        ('sid', remote.sid)
                    ])

        if self.verifyRemoteData(data):
            self.dumpRemoteData(data, remote.name)

    def loadRemote(self, remote):
        '''
        Load the data from file given by remote.name
        '''
        return (self.loadRemoteData(remote.name))

    def clearRemote(self, remote):
        '''
        Clear the remote estate file
        '''
        self.clearRemoteData(remote.name)

    def replaceRemote(self, remote, old):
        '''
        Replace keep file if renaming should move it
        This is provided for subclasses or mimic classes that store the
        Safe data by name and need to move that data
        '''
        pass


class LotKeep(Keep):
    '''
    RAET protocol endpoint lot persistence

    '''
    Fields = ['uid', 'name', 'ha']

    def __init__(self, prefix='lot', **kwa):
        '''
        Setup LotKeep instance
        '''
        super(LotKeep, self).__init__(prefix=prefix, **kwa)
