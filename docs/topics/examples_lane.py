'''
RAET Tutorial Examples for LaneStack
'''

import os
import shutil
import time
import tempfile

import ioflo
from ioflo.base.consoling import getConsole

import raet

console = getConsole()
console.reinit(verbosity=console.Wordage.concise)

def serviceStacks(stacks, duration=0.5, period=0.1):
    '''
    Utility method to service queues. Call from test method.
    '''
    store = ioflo.base.storing.Store(stamp=0.0)
    timer = ioflo.aid.timing.StoreTimer(store=store, duration=duration)
    while not timer.expired:
        for stack in stacks:
            stack.serviceAll()
            stack.store.advanceStamp(period)

        store.advanceStamp(period)
        time.sleep(period)

def example1():
    tempDirpath = tempfile.mkdtemp(prefix="raet", suffix="base", dir='/tmp')
    baseDirpath = os.path.join(tempDirpath, 'lane')

    alpha = raet.lane.stacking.LaneStack(name='alpha',
                                         uid=1,
                                         lanename='zeus',
                                         sockdirpath=baseDirpath)

    beta = raet.lane.stacking.LaneStack(name='beta',
                                        uid=1,
                                        lanename='zeus',
                                        sockdirpath=baseDirpath)

    stacks = [alpha, beta]

    for stack in stacks:
        console.terse("LaneStack '{0}': UXD socket ha = '{1}'\n".format(stack.name, stack.ha))

    remote = raet.lane.yarding.RemoteYard(stack=alpha, ha=beta.ha)
    alpha.addRemote(remote)

    msg = dict(content="Hello this is a message from alpha to beta")
    alpha.transmit(msg, remote.uid)
    serviceStacks(stacks)

    while beta.rxMsgs:
        rxMsg, source = beta.rxMsgs.popleft()
        console.terse("Beta received from {0} message = '{1}'\n".format(source, rxMsg))

    remote = beta.remotes.values()[0]
    console.terse("Beta remotes has '{0}' at '{1}'\n".format(remote.name, remote.ha))

    remote = alpha.remotes.values()[0]
    console.terse("Alpha remotes has '{0}' at '{1}'\n".format(remote.name, remote.ha))

    beta.transmit(dict(content = "Hi from beta"))
    beta.transmit(dict(content = "Hi again from beta"))
    beta.transmit(dict(content = "Hi yet again from beta"))

    alpha.transmit(dict(content = "Hello from alpha"))
    alpha.transmit(dict(content = "Hello again from alpha"))
    alpha.transmit(dict(content = "Hello yet again from alpha"))

    serviceStacks(stacks)

    for stack in stacks:
        while stack.rxMsgs:
            rxMsg, source = stack.rxMsgs.popleft()
            console.terse("LaneStack {0} received from {1} message = '{2}'\n".format(stack.name, source, rxMsg))



    for stack in stacks:
        stack.server.close()

    shutil.rmtree(tempDirpath)

    print("Finished\n")



if __name__ == "__main__":
    example1()

