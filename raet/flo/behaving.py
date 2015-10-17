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

import shutil

# Import ioflo libs
from ioflo.aid.odicting import odict
from ioflo.base import deeding

from ioflo.base.consoling import getConsole
console = getConsole()

# Import raet libs
from ..abiding import *  # import globals
from .. import raeting
from ..raeting import AutoMode
from ..road.stacking import  RoadStack
from ..lane.stacking import  LaneStack
from ..road import packeting, estating
from ..lane import paging, yarding

class SaltRaetRoadCleanup(deeding.Deed):
    '''
    Cleanup stray road keep directories

    FloScript:

    do salt raet road cleanup at enter

    '''
    Ioinits = odict(
                     inode="raet.road.stack.",
                     local=odict(
                                 ipath='local',
                                 ival=odict(basedirpath='/tmp/raet/keep')
                                )
                    )

    def action(self):
        '''
        Should only run once to cleanup stale lane uxd files.
        '''
        basedirpath = os.path.abspath(os.path.expanduser(self.local.data.basedirpath))
        console.concise("Cleaning up road files in {0}\n".format(basedirpath))
        if os.path.exists(basedirpath):
            shutil.rmtree(basedirpath)

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
                                                 mutable=True,
                                                 auto=AutoMode.once.value,
                                                 uid=None,
                                                 host='0.0.0.0',
                                                 port=raeting.RAET_PORT,
                                                 sigkey=None,
                                                 prikey=None)),)

    def _prepare(self):
        '''
        Setup stack instance
        '''
        sigkey = self.local.data.sigkey
        prikey = self.local.data.prikey
        name = self.local.data.name
        basedirpath = os.path.abspath(os.path.expanduser(self.local.data.basedirpath))
        auto = self.local.data.auto
        main = self.local.data.main
        mutable = self.local.data.mutable
        ha = (self.local.data.host, self.local.data.port)

        uid = self.local.data.uid
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = RoadStack(store=self.store,
                                     main=main,
                                     mutable=mutable,
                                     name=name,
                                     uid=uid,
                                     ha=ha,
                                     sigkey=sigkey,
                                     prikey=prikey,
                                     auto=auto,
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

    do salt raet road stack setup at enter

    '''
    Ioinits = odict(
        inode="raet.road.stack.",
        stack='stack',
        txmsgs=odict(ipath='txmsgs', ival=deque()),
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),
        local=odict(ipath='local', ival=odict(   name='master',
                                                 basedirpath='/tmp/raet/keep',
                                                 main=False,
                                                 mutable=True,
                                                 auto=AutoMode.once.value,
                                                 uid=None,
                                                 host='0.0.0.0',
                                                 port=raeting.RAET_PORT,
                                                 sigkey=None,
                                                 prikey=None)),)

    def _prepare(self):
        '''
        Assign class defaults
        '''
        #RoadStack.Bk = raeting.bodyKinds.msgpack
        RoadStack.JoinentTimeout = 0.0

    def action(self):
        '''
        enter action
        should only run once to setup road stack.
        moved from _prepare so can do clean up before stack is initialized

        do salt raet road stack setup at enter
        '''

        sigkey = self.local.data.sigkey
        prikey = self.local.data.prikey
        name = self.local.data.name
        basedirpath = os.path.abspath(os.path.expanduser(self.local.data.basedirpath))
        auto = self.local.data.auto
        main = self.local.data.main
        mutable = self.local.data.mutable
        ha = (self.local.data.host, self.local.data.port)

        uid = self.local.data.uid
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = RoadStack(store=self.store,
                                     name=name,
                                     uid=uid,
                                     ha=ha,
                                     sigkey=sigkey,
                                     prikey=prikey,
                                     auto=auto,
                                     main=main,
                                     mutable=mutable,
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

    Ioinits = odict(
                     inode="raet.road.stack.",
                     stack='stack',
                     local=odict(
                                 ipath='local',
                                 ival=odict(masterhost='127.0.0.1',
                                            masterport=raeting.RAET_PORT,
                                            )
                                )
                    )

    def action(self, **kwa):
        '''
        do raet road stack joiner at enter
        '''
        stack = self.stack.value
        host = self.local.data.masterhost
        if host == "" or  host == "0.0.0.0":
            host = "127.0.0.1"
        port = self.local.data.masterport
        ha = (host, port)
        if stack and isinstance(stack, RoadStack):
            if not stack.remotes:
                stack.addRemote(estating.RemoteEstate(stack=stack,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=ha))
            stack.join(uid=stack.remotes.values()[0].uid)

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
                stack.transmit(msg=msg, uid=deid)


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
        Receive message
        '''
        rxMsgs = self.rxmsgs.value
        while rxMsgs:
            msg, name = rxMsgs.popleft()
            console.terse("\nReceived....\n{0}\n".format(msg))

class SaltRaetLaneCleanup(deeding.Deed):
    '''
    Cleanup stray lane keep directories not reaped

    FloScript:

    do salt raet lane cleanup at enter

    '''
    Ioinits = {
                'opts': '.salt.opts',
            }

    def action(self):
        '''
        Should only run once to cleanup stale lane uxd files.
        '''
        if self.opts.value.get('sock_dir'):
            sockdirpath = os.path.abspath(self.opts.value['sock_dir'])
            console.concise("Cleaning up uxd files in {0}\n".format(sockdirpath))
            for name in os.listdir(sockdirpath):
                path = os.path.join(sockdirpath, name)
                if os.path.isdir(path):
                    continue
                root, ext = os.path.splitext(name)
                if ext != '.uxd':
                    continue
                if not all(root.partition('.')):
                    continue
                try:
                    os.unlink(path)
                    console.concise("Removed {0}\n".format(path))
                except OSError:
                    console.concise("Failed removing {0}\n".format(path))
                    raise

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
                                              lane="maple",
                                              sockdirpath="/tmp/raet/test/lane/")),)

    def _prepare(self):
        '''
        Setup stack instance
        '''
        name = self.local.data.name
        lane = self.local.data.lane
        sockdirpath = self.local.data.sockdirpath
        txMsgs = self.txmsgs.value
        rxMsgs = self.rxmsgs.value

        self.stack.value = LaneStack(
                                       store=self.store,
                                       name=name,
                                       sockdirpath=sockdirpath,
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
        local=odict(ipath='local',
                    ival=odict(sockdirpath="/tmp/raet/test/lane/")))

    def action(self, lane="lane", name=None, **kwa):
        '''
        Adds new yard to stack on lane with name
        '''
        stack = self.stack.value
        sockdirpath = self.local.data.sockdirpath
        if stack and isinstance(stack, LaneStack):
            yard = yarding.RemoteYard(stack=stack,
                                      lanename=lane,
                                      name=name,
                                      dirpath=sockdirpath)
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
                stack.transmit(msg=msg, uid=stack.fetchUidByName(name))


class RaetLaneStackPrinter(deeding.Deed):
    '''
    Prints out messages on rxMsgs queue
    FloScript:

    do raet lane stack printer

    '''
    Ioinits = odict(
        inode=".raet.lane.stack.",
        total=odict(ipath="totalRxMsg", ival=odict(value=0)),
        stack="stack",
        rxmsgs=odict(ipath='rxmsgs', ival=deque()),)

    def action(self, **kwa):
        '''
        Receive message
        '''
        rxMsgs = self.rxmsgs.value
        stack = self.stack.value
        while rxMsgs:
            msg, name = rxMsgs.popleft()
            console.terse("\n{0} Received....\n{1}\n".format(stack.name, msg))
            self.total.value += 1
