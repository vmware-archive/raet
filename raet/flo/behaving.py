# -*- coding: utf-8 -*-
'''
behaving.py raet ioflo behaviors

See raeting.py for data format and packet field details.

Layout in DataStore


raet.road.stack.stack
    value StackUdp
raet.road.stack.txmsgs
    value deque()
raet.road.stack.rxmsgs
    value deque()
raet.road.stack.local
    name host port sigkey prikey
raet.road.stack.status
    joined allowed idle
raet.road.stack.destination
    value deid


'''
# pylint: skip-file
# pylint: disable=W0611

import os

# Import Python libs
from collections import deque
try:
    import simplejson as json
except ImportError:
    import json

# Import ioflo libs
from ioflo.base.odicting import odict
from ioflo.base.globaling import *

from ioflo.base import aiding
from ioflo.base import storing
from ioflo.base import deeding

from ioflo.base.consoling import getConsole
console = getConsole()

from .. import raeting
from ..road.stacking import  RoadStack
from ..lane.stacking import  LaneStack
from ..road import packeting, estating
from ..lane import paging, yarding


class RaetRoadStack(deeding.Deed):
    '''
    Initialize and run raet road stack
    FloScript:

    do raet road stack

    '''
    Ioinits = odict(
        inode="raet.road.stack.",
        stack='stack',
        txmsgs=odict(ipath='txmsgs', ival=deque()),
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),
        local=odict(ipath='local', ival=odict(   name='master',
                                                 basedirpath='/tmp/raet/keep',
                                                 main=False,
                                                 auto=True,
                                                 eid=None,
                                                 localname='master',
                                                 host='0.0.0.0',
                                                 port=raeting.RAET_PORT,
                                                 sigkey=None,
                                                 prikey=None)),)

    def postinitio(self):
        '''
        Setup stack instance
        '''
        sigkey = self.local.data.sigkey
        prikey = self.local.data.prikey
        name = self.local.data.name
        localname = self.local.data.localname
        basedirpath = os.path.abspath(os.path.expanduser(self.local.data.basedirpath))
        auto = self.local.data.auto
        main = self.local.data.main
        ha = (self.local.data.host, self.local.data.port)

        eid = self.local.data.eid
        local = estating.LocalEstate(  eid=eid,
                                        name=localname,
                                        ha=ha,
                                        sigkey=sigkey,
                                        prikey=prikey,)
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = RoadStack(  local=local,
                                       store=self.store,
                                       name=name,
                                       localname=localname,
                                       auto=auto,
                                       main=main,
                                       basedirpath=basedirpath,
                                       txMsgs=txMsgs,
                                       rxMsgs=rxMsgs, )

    def action(self, **kwa):
        '''
        Service all the deques for the stack
        '''
        self.stack.value.serviceAll()


class RaetRoadStackSetup(deeding.Deed):
    '''
    Initialize  raet road stack
    FloScript:

    do raet road stack setup

    '''
    Ioinits = odict(
        inode="raet.road.stack.",
        stack='stack',
        txmsgs=odict(ipath='txmsgs', ival=deque()),
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),
        local=odict(ipath='local', ival=odict(   name='master',
                                                 basedirpath='/tmp/raet/keep',
                                                 main=False,
                                                 auto=True,
                                                 eid=None,
                                                 localname='master',
                                                 host='0.0.0.0',
                                                 port=raeting.RAET_PORT,
                                                 sigkey=None,
                                                 prikey=None)),)

    def postinitio(self):
        '''
        Setup stack instance
        '''
        sigkey = self.local.data.sigkey
        prikey = self.local.data.prikey
        name = self.local.data.name
        localname = self.local.data.localname
        basedirpath = os.path.abspath(os.path.expanduser(self.local.data.basedirpath))
        auto = self.local.data.auto
        main = self.local.data.main
        ha = (self.local.data.host, self.local.data.port)

        eid = self.local.data.eid
        local = estating.LocalEstate(  eid=eid,
                                        name=localname,
                                        ha=ha,
                                        sigkey=sigkey,
                                        prikey=prikey,)
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = RoadStack(  local=local,
                                       store=self.store,
                                       name=name,
                                       localname=localname,
                                       auto=auto,
                                       main=main,
                                       basedirpath=basedirpath,
                                       txMsgs=txMsgs,
                                       rxMsgs=rxMsgs, )


class RaetRoadStackCloser(deeding.Deed):
    '''
    Closes road stack server socket connection
    FloScript:

    do raet road stack closer at exit

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self, **kwa):
        '''
        Close udp socket
        '''
        if self.stack.value and isinstance(self.stack.value, RoadStack):
            self.stack.value.server.close()

class RaetRoadStackRxServicer(deeding.Deed):
    '''
    Serive inbound packets and process

    FloScript:
        do raet road stack rx servicer

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self):
        '''
        Process inboud queues
        '''
        self.stack.value.serviceAllRx()

class RaetRoadStackTxServicer(deeding.Deed):
    '''
    Service outbound packets

    FloScript:
        do raet road stack tx servicer

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self):
        '''
        Process inbound queues
        '''
        self.stack.value.serviceAllTx()

class RaetRoadStackJoiner(deeding.Deed):
    '''
    Initiates join transaction with zeroth remote estate (main)
    FloScript:

    do raet road stack joiner at enter

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack',)

    def action(self, **kwa):
        '''

        '''
        stack = self.stack.value
        if stack and isinstance(stack, RoadStack):
            stack.join()

class RaetRoadStackJoined(deeding.Deed):
    '''
    Updates status field in share with .joined of zeroth remote estate (main)
    FloScript:

    do raet road stack joined
    go next if joined in .raet.road.stack.status
    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack',
        status=odict(ipath='status', ival=odict(joined=False,
                                                allowed=False,
                                                idle=False, )))

    def action(self, **kwa):
        '''
        Update .status share
        '''
        stack = self.stack.value
        joined = False
        if stack and isinstance(stack, RoadStack):
            if stack.remotes:
                joined = stack.remotes.values()[0].joined
        self.status.update(joined=joined)

class RaetRoadStackAllower(deeding.Deed):
    '''
    Initiates allow (CurveCP handshake) transaction with zeroth remote estate (main)
    FloScript:

    do raet road stack allower at enter

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self, **kwa):
        '''
        Receive any udp packets on server socket and put in rxes
        Send any packets in txes
        '''
        stack = self.stack.value
        if stack and isinstance(stack, RoadStack):
            stack.allow(cascade=True)

class RaetRoadStackAllowed(deeding.Deed):
    '''
    Updates status field in share with .allowed of zeroth remote estate (main)
    FloScript:

    do raet road stack allowed
    go next if allowed in .raet.road.stack.status

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack',
        status=odict(ipath='status', ival=odict(joined=False,
                                                allowed=False,
                                                idle=False, )))

    def action(self, **kwa):
        '''
        Update .status share
        '''
        stack = self.stack.value
        allowed = False
        if stack and isinstance(stack, RoadStack):
            if stack.remotes:
                allowed = stack.remotes.values()[0].allowed
        self.status.update(allowed=allowed)

class RaetRoadStackIdled(deeding.Deed):
    '''
    Updates idle status field in shate to true if there are no outstanding
    transactions in the associated stack

    FloScript:

    do raet road stack idled
    go next if idled in .raet.road.stack.status

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack',
        status=odict(ipath='status', ival=odict(joined=False,
                                                allowed=False,
                                                idle=False, )))

    def action(self, **kwa):
        '''
        Update .status share
        '''
        stack = self.stack.value
        idled = False
        if stack and isinstance(stack, RoadStack):
            if not stack.transactions:
                idled = True
        self.status.update(idled=idled)

class RaetRoadStackManager(deeding.Deed):
    '''
    Runs the presence manage method of RoadStack
    
    FloScript:
        do raet road stack manager

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self, **kwa):
        '''
        Manage the presence of any remotes
        '''
        stack = self.stack.value
        if stack and isinstance(stack, RoadStack):
            stack.manage(cascade=True)

class RaetRoadStackManagerImmediate(deeding.Deed):
    '''
    Initiates allow (CurveCP handshake) transaction with zeroth remote estate (main)
    FloScript:

    do raet road stack allower at enter

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack='stack', )

    def action(self, **kwa):
        '''
        Manage the presence of any remotes
        '''
        stack = self.stack.value
        if stack and isinstance(stack, RoadStack):
            stack.manage(cascade=True, immediate=True)

class RaetRoadStackMessenger(deeding.Deed):
    '''
    Message is composed of fields that are parameters to action method
    and is sent to remote estate deid by putting message on txMsgs deque

    FloScript:
    do raet road stack messenger to contents "Hello World" at enter

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        stack="stack",
        destination="destination",)

    def action(self, **kwa):
        '''
        Queue up message
        '''
        if kwa:
            msg = odict(kwa)
            stack = self.stack.value
            if stack and isinstance(stack, RoadStack):
                deid = self.destination.value
                stack.transmit(msg=msg, duid=deid)


class RaetRoadStackPrinter(deeding.Deed):
    '''
    Prints out messages on rxMsgs queue for associated stack
    FloScript:

    do raet road stack printer

    '''
    Ioinits = odict(
        inode=".raet.road.stack.",
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),)

    def action(self, **kwa):
        '''
        Queue up message
        '''
        rxMsgs = self.rxmsgs.value
        while rxMsgs:
            msg = rxMsgs.popleft()
            console.terse("\nReceived....\n{0}\n".format(msg))

class RaetLaneStack(deeding.Deed):
    '''
    Initialize and run raet lane stack
    FloScript:

    do raet lane stack

    '''
    Ioinits = odict(
        inode="raet.lane.stack.",
        stack='stack',
        txmsgs=odict(ipath='txmsgs', ival=deque()),
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),
        local=odict(ipath='local', ival=odict(name='minion',
                                              localname='minion',
                                              lane="maple",
                                              basedirpath="/tmp/raet/test/lane/keep/")),)

    def postinitio(self):
        '''
        Setup stack instance
        '''
        name = self.local.data.name
        lane = self.local.data.lane
        localname = self.local.data.localname
        basedirpath = self.local.data.basedirpath
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = LaneStack(
                                       store=self.store,
                                       name=name,
                                       localname=localname,
                                       basedirpath=basedirpath,
                                       lanename=lane,
                                       txMsgs=txMsgs,
                                       rxMsgs=rxMsgs, )

    def action(self, **kwa):
        '''
        Service all the deques for the stack
        '''
        self.stack.value.serviceAll()

class RaetLaneStackCloser(deeding.Deed):
    '''
    Closes lane stack server socket connection
    FloScript:

    do raet lane stack closer at exit

    '''
    Ioinits = odict(
        inode=".raet.lane.stack.",
        stack='stack',)

    def action(self, **kwa):
        '''
        Close uxd socket
        '''
        if self.stack.value and isinstance(self.stack.value, LaneStack):
            self.stack.value.server.close()

class RaetLaneStackYardAdd(deeding.Deed):
    '''
    Adds yard to lane stack.
    Where lane is the lane name and name is the yard name in the parameters
    FloScript:

    do raet lane stack yard add to lane "ash" name "lord" at enter

    '''
    Ioinits = odict(
        inode=".raet.lane.stack.",
        stack='stack',
        local='yard',
        yard=odict(ipath='local', ival=odict(name=None, lane="maple")),)

    def action(self, lane="lane", name=None, **kwa):
        '''
        Adds new yard to stack on lane with yid
        '''
        stack = self.stack.value
        if stack and isinstance(stack, LaneStack):
            yard = yarding.RemoteYard(stack=stack, lanename=lane, name=name)
            stack.addRemote(yard)
            self.local.value = yard

class RaetLaneStackTransmit(deeding.Deed):
    '''
    Message is composed of fields that are parameters to action method
    and is sent to remote estate deid by putting on txMsgs deque
    FloScript:

    do raet lane stack transmit to content "Hello World" at enter

    '''
    Ioinits = odict(
        inode=".raet.lane.stack.",
        stack="stack",
        dest="dest",)

    def action(self, **kwa):
        '''
        Queue up message
        '''
        if kwa:
            msg = odict(kwa)
            stack = self.stack.value
            if stack and isinstance(stack, LaneStack):
                name = self.dest.value #destination yard name
                stack.transmit(msg=msg, duid=stack.uids.get(name))


class RaetLaneStackPrinter(deeding.Deed):
    '''
    Prints out messages on rxMsgs queue
    FloScript:

    do raet lane stack printer

    '''
    Ioinits = odict(
        inode=".raet.lane.stack.",
        stack="stack",
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),)

    def action(self, **kwa):
        '''
        Queue up message
        '''
        rxMsgs = self.rxmsgs.value
        stack = self.stack.value
        while rxMsgs:
            msg = rxMsgs.popleft()
            console.terse("\n{0} Received....\n{1}\n".format(stack.name, msg))
