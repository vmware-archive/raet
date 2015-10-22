# -*- coding: utf-8 -*-
'''
yarding.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611
# Import python libs
import socket
import os
import errno
import sys

if sys.version_info > (3,):
    long = int

# Import ioflo libs
from ioflo.aid.odicting import odict

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from .. import nacling
from .. import lotting

from ioflo.base.consoling import getConsole
console = getConsole()

YARD_UXD_DIR = os.path.join('/var', 'cache', 'raet')
ALT_YARD_UXD_DIR = os.path.join('~', '.raet', 'uxd')


class Yard(lotting.Lot):
    '''
    RAET protocol Yard ie Lane Lot
    '''

    def  __init__(self,
                  stack,
                  uid=None,
                  prefix='lane',
                  name='',
                  ha='',
                  sid=None,
                  dirpath='',
                  lanename='',
                  bid=0,
                  **kwa):
        '''
        Setup instance

        stack is required parameter
        '''
        uid = uid if uid is not None else stack.nextUid()

        if lanename and  " " in lanename:
            emsg = "Invalid lanename '{0}'".format(lanename)
            raise raeting.YardError(emsg)

        if name and  " " in name:
            emsg = "Invalid yard name '{0}'".format(self.name)
            raise raeting.YardError(emsg)

        if ha: #verify that names are compatible with ha format
            lname, yname = Yard.namesFromHa(ha)
            if name and name != yname:
                emsg =  "Incompatible Yard name '{0}' and ha '{1}'".format(name, ha)
                raise raeting.YardError(emsg)

            if lanename and lanename != lname:
                emsg =  "Incompatible Lane name '{0}' and ha '{1}'".format(lanename, ha)
                raise raeting.YardError(emsg)

            lanename = lname
            name = yname

        name = name or "{0}_{1}".format(prefix, nacling.uuid(18))

        sid = sid if sid is not None else self.nextSid() #if not given unique sid

        super(Yard, self).__init__(stack=stack,
                                   name=name,
                                   uid=uid,
                                   ha=ha,
                                   sid=sid,
                                   **kwa)

        self.lanename = lanename or 'lane'
        self.bid = bid #current book id

        if not ha:
            if not dirpath:
                dirpath = YARD_UXD_DIR
            ha, dirpath = self.computeHa(dirpath, self.lanename, self.name)

        self.dirpath = dirpath
        self.ha = ha

    @staticmethod
    def computeHa(dirpath, lanename, yardname):
        '''
        Compute and return a tuple of the host address and normalize dirpath for yard given the
        dirpath, lanename, and yardname
        '''
        if not sys.platform == 'win32':
            dirpath = os.path.abspath(os.path.expanduser(dirpath))
            if not os.path.exists(dirpath):
                try:
                    os.makedirs(dirpath)
                except OSError as ex:
                    dirpath = os.path.abspath(os.path.expanduser(ALT_YARD_UXD_DIR))
                    if not os.path.exists(dirpath):
                        try:
                            os.makedirs(dirpath)
                        except OSError as ex:
                            err = raeting.get_exception_error(ex)
                            if err == errno.EEXIST:
                                pass # race condition
                            else:
                                raise
            else:
                if not os.access(dirpath, os.R_OK | os.W_OK):
                    dirpath = os.path.abspath(os.path.expanduser(ALT_YARD_UXD_DIR))
                    if not os.path.exists(dirpath):
                        try:
                            os.makedirs(dirpath)
                        except OSError as ex:
                            err = raeting.get_exception_error(ex)
                            if err == errno.EEXIST:
                                pass # race condition
                            else:
                                raise

        ha = os.path.join(dirpath, "{0}.{1}.uxd".format(lanename, yardname))
        return (ha, dirpath)

    @staticmethod
    def namesFromHa(ha):
        '''
        Extract and return the lane and yard names from yard host address ha
        where return is tuple (lanename, yardname)
        '''
        head, tail = os.path.split(ha)
        if not tail:
            emsg = "Invalid format for ha '{0}'. No file".format(ha)
            raise  raeting.YardError(emsg)

        root, ext = os.path.splitext(tail)

        if ext != ".uxd":
            emsg = "Invalid format for ha '{0}'. Ext not 'uxd'".format(ha)
            raise  raeting.YardError(emsg)

        lanename, sep, yardname = root.rpartition('.')
        if not sep:
            emsg = "Invalid format for ha '{0}'. No lane.name".format(ha)
            raise  raeting.YardError(emsg)

        return (lanename, yardname)

    def nextSid(self):
        '''
        Generates next unique sid number.
        '''
        self.sid = nacling.uuid(size=18)
        return self.sid

    def nextBid(self):
        '''
        Generates next book id number.
        '''
        self.bid += 1
        if self.bid > long(0xffffffff):
            self.bid = 1  # rollover to 1
        return self.bid

class RemoteYard(Yard):
    '''
    RAET protocol endpoint remote yard ie Remote Lane Lot

    stack is required parameter
    '''
    def __init__(self, stack, prefix='yard', uid=None, rsid=0, **kwa):
        '''
        Setup instance
        '''
        if uid is None:
            uid = stack.nextUid()
            while uid in stack.remotes or uid == stack.local.uid:
                uid = stack.nextUid()

        super(RemoteYard, self).__init__(stack=stack, prefix=prefix, uid=uid, **kwa)
        self.rsid = rsid # last sid received from remote
        self.books = odict()

    def addBook(self, index, book):
        '''
        Safely add book at index,(si, bi) If not already there
        '''
        if index in self.books:
            emsg = "Cannot add book at index '{0}', alreadys exists".format(index)
            raise raeting.YardError(emsg)
        self.books[index] = book
        console.verbose( "Added book to {0} at '{1}'\n".format(self.name, index))

    def removeBook(self, index, book=None):
        '''
        Safely remove book at index, (si, bi) If book identity same
        If book is None then remove without comparing identity
        '''
        if index in self.books:
            if book:
                if book is self.books[index]:
                    del  self.books[index]
            else:
                del self.books[index]

    def removeStaleBooks(self):
        '''
        Remove stale books associated with remote when index si different than remote.rsid
        where index is tuple (ln, rn, si, bi)       (si, bi)
        '''
        for index, book in self.books.items():
            sid = index[2]
            if sid != self.rsid:
                self.removeBook(index, book)
                emsg = "Stale book at '{0}' in page from remote {1}\n".format(index, self.name)
                console.terse(emsg)
                self.stack.incStat('stale_book')
