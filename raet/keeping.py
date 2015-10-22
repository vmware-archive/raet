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

try:
    import msgpack
except ImportError:
    msgpack = None

import shutil

# Import ioflo libs
from ioflo.aid.odicting import odict
from ioflo.aid.aiding import ocfn

# Import raet libs
from .abiding import *  # import globals
from . import raeting
from . import nacling

from ioflo.base.consoling import getConsole
console = getConsole()

class Keep(object):
    '''
    RAET protocol base class for data persistence of objects that follow the Lot
    protocol
    '''
    LocalFields = ['uid', 'name', 'ha', 'sid', 'puid']
    RemoteFields = ['uid', 'name', 'ha']
    Ext = 'json' # default serialization type of json and msgpack
    KeepDir = os.path.join('/var', 'cache', 'raet', 'keep')
    AltKeepDir = os.path.join('~', '.raet', 'keep')

    def __init__(self,
                 basedirpath='',
                 dirpath='',
                 stackname='stack',
                 prefix='data',
                 ext='',
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
                basedirpath = self.KeepDir
            dirpath = os.path.join(basedirpath, stackname)
        dirpath = os.path.abspath(os.path.expanduser(dirpath))

        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath)
            except OSError as ex:
                dirpath = os.path.join(self.AltKeepDir, stackname)
                dirpath = os.path.abspath(os.path.expanduser(dirpath))
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)

        else:
            if not os.access(dirpath, os.R_OK | os.W_OK):
                dirpath = os.path.join(self.AltKeepDir, stackname)
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
        self.ext = ext or self.Ext
        if self.ext == 'msgpack' and not msgpack:
            self.ext = 'json'

        self.localfilepath = os.path.join(self.localdirpath,
                "{0}.{1}".format(self.prefix, self.ext))

    @staticmethod
    def dump(data, filepath):
        '''
        Write data as as type self.ext to filepath. json or msgpack
        '''
        if ' ' in filepath:
            raise raeting.KeepError("Invalid filepath '{0}' "
                                    "contains space".format(filepath))

        if hasattr(data, 'get'):
            for key, val in data.items():  # P3 json.dump no encoding parameter
                if isinstance(val, (bytes, bytearray)):
                    data[key] = val.decode('utf-8')

        root, ext = os.path.splitext(filepath)
        if ext == '.json':
            with ocfn(filepath, "w+") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        elif ext == '.msgpack':
            if not msgpack:
                raise raeting.KeepError("Invalid filepath ext '{0}' "
                            "needs msgpack installed".format(filepath))
            with ocfn(filepath, "w+b", binary=True) as f:
                msgpack.dump(data, f, encoding='utf-8')
                f.flush()
                os.fsync(f.fileno())
        else:
            raise raeting.KeepError("Invalid filepath ext '{0}' "
                        "not '.json' or '.msgpack'".format(filepath))

        #f.flush()
        #os.fsync(f.fileno())

    @staticmethod
    def load(filepath):
        '''
        Return data read from filepath as converted json
        Otherwise return None
        '''

        try:
            root, ext = os.path.splitext(filepath)
            if ext == '.json':
                with ocfn(filepath, "r") as f:
                    it = json.load(f, object_pairs_hook=odict)
            elif ext == '.msgpack':
                if not msgpack:
                    raise raeting.KeepError("Invalid filepath ext '{0}' "
                                "needs msgpack installed".format(filepath))
                with ocfn(filepath, "rb", binary=True) as f:
                    it = msgpack.load(f, object_pairs_hook=odict, encoding='utf-8')
            else:
                it = None
        except EOFError:
            return None
        except ValueError:
            return None
        return it

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

    def scrubData(self, data, defaults):
        '''
        Returns scrubbed copy of data that has the same field set as defaults
        by either copying values for common fields or
        adding fields with defaults
        or leaving out extra fields
        '''
        scrubbed = odict(defaults)
        for key in scrubbed:
            if key in data:
                scrubbed[key] = data[key]
        return scrubbed

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
        filepath = os.path.join(self.remotedirpath,
                "{0}.{1}.{2}".format(self.prefix, name, self.ext))
        if not os.path.exists(filepath):
            return None
        return (self.load(filepath))

    def loadAllRemoteData(self):
        '''
        Load and Return the datadict from the all the remote data files
        indexed by name in filenames
        '''
        keeps = odict()
        for filename in os.listdir(self.remotedirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, name = root.partition('.')
            if not name or prefix != self.prefix:
                continue
            filepath = os.path.join(self.remotedirpath, filename)
            keeps[name] = self.load(filepath)
        return keeps

    def clearRemoteData(self, name):
        '''
        Clear data from the remote data file
        '''
        filepath = os.path.join(self.remotedirpath,
                "{0}.{1}.{2}".format(self.prefix, name, self.ext))
        if os.path.exists(filepath):
            os.remove(filepath)

    def clearAllRemoteData(self):
        '''
        Remove all the remote data files
        '''
        for filename in os.listdir(self.remotedirpath):
            root, ext = os.path.splitext(filename)
            if ext not in ['.json', '.msgpack']:
                continue
            prefix, sep, name = root.partition('.')
            if not name or prefix != self.prefix:
                continue
            filepath = os.path.join(self.remotedirpath, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    def clearRemoteDir(self):
        '''
        Clear the remote directory
        '''
        if os.path.exists(self.remotedirpath):
            os.rmdir(self.remotedirpath)

    def dumpLocal(self, local):
        '''
        Dump local
        '''
        data = odict([
                        ('name', local.name),
                        ('uid', local.uid),
                        ('ha', local.ha),
                        ('sid', local.sid),
                        ('puid', local.stack.puid),
                    ])
        if self.verifyLocalData(data):
            self.dumpLocalData(data)

    def dumpRemote(self, remote):
        '''
        Dump remote
        '''
        data = odict([
                        ('name', remote.name),
                        ('uid', remote.uid),
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

class LotKeep(Keep):
    '''
    RAET protocol endpoint lot persistence
    '''

    def __init__(self, prefix='lot', **kwa):
        '''
        Setup LotKeep instance
        '''
        super(LotKeep, self).__init__(prefix=prefix, **kwa)
