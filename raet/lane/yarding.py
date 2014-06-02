# -*- coding: utf-8 -*-
'''
yarding.py raet protocol estate classes
'''
# pylint: skip-file
# pylint: disable=W0611
# Import python libs
import socket
import os

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base import aiding

from .. import raeting
from .. import nacling
from .. import lotting

from ioflo.base.consoling import getConsole
console = getConsole()

YARD_UXD_DIR = os.path.join('/var', 'cache', 'raet')
ALT_YARD_UXD_DIR = os.path.join('~', '.raet', 'uxd')


class Yard(lotting.Lot):
    '''
    RAET protocol Yard
    '''
    Yid = 2 # class attribute

    def  __init__(self,
                  stack=None,
                  yid=None,
                  name='',
                  ha='',
                  dirpath='',
                  lanename='',
                  bid=0,
                  **kwa):
        '''
        Initialize instance
        '''
        if yid is None:
            if stack:
                yid = stack.nextYid()
                while yid in stack.remotes:
                    yid = stack.nextYid()
            else:
                yid = Yard.Yid
                Yard.Yid += 1
        self.yid = yid # yard ID

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

        name = name or "yard{0}".format(self.yid)

        super(Yard, self).__init__(stack=stack, name=name, ha=ha, **kwa)

        self.lanename = lanename or 'lane'
        self.bid = bid #current book id

        if not dirpath:
            dirpath = YARD_UXD_DIR
        self.dirpath = os.path.abspath(os.path.expanduser(dirpath))
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath)
            except OSError as ex:
                dirpath = os.path.abspath(os.path.expanduser(ALT_YARD_UXD_DIR))
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
        else:
            if not os.access(dirpath, os.R_OK | os.W_OK):
                dirpath = os.path.abspath(os.path.expanduser(ALT_YARD_UXD_DIR))
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)

        self.ha = ha or os.path.join(dirpath, "{0}.{1}.uxd".format(self.lanename, self.name))

    @property
    def uid(self):
        '''
        property that returns unique identifier
        '''
        return self.yid

    @uid.setter
    def uid(self, value):
        '''
        setter for uid property
        '''
        self.yid = value

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
            emsg = "Invalid format for ha '{0}'. Not lane.name".format(ha)
            raise  raeting.YardError(emsg)

        return (lanename, yardname)

    def nextBid(self):
        '''
        Generates next book id number.
        '''
        self.bid += 1
        if self.bid > 0xffffffffL:
            self.bid = 1  # rollover to 1
        return self.bid

class LocalYard(Yard):
    '''
    RAET UXD Protocol endpoint local Yard
    '''
    def __init__(self, stack=None, name='', main=None, **kwa):
        '''
        Setup Yard instance
        '''
        super(LocalYard, self).__init__(stack=stack, name=name, **kwa)
        self.main = True if main else False # main yard on lane


class RemoteYard(Yard):
    '''
    RAET protocol endpoint remote yard
    '''
    def __init__(self, rsid=0, **kwa):
        '''
        Setup Yard instance
        '''
        super(RemoteYard, self).__init__(**kwa)
        self.rsid = rsid # last sid received from remote

    def validRsid(self, rsid):
        '''
        Compare new rsid to old .rsid and return True if new is greater than old
        modulo N where N is 2^32 = 0x100000000
        And greater means the difference is less than N/2
        '''
        return (((rsid - self.rsid) % 0x100000000) < (0x100000000 // 2))
