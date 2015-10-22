'''
RAET Tutorial Examples for RoadStack
'''
import time

import ioflo
from ioflo.base.consoling import getConsole


import raet
from raet import raeting
from raet.raeting import AutoMode

console = getConsole()
console.reinit(verbosity=console.Wordage.concise)

def serviceStacks(stacks, duration=1.0, period=0.1):
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
        if all([not stack.transactions for stack in stacks]):
            break
        time.sleep(period)
    console.concise("Perceived service duration = {0} seconds\n".format(timer.elapsed))

def example1():
    alpha = raet.road.stacking.RoadStack(name='alpha',
                                         ha=('0.0.0.0', 7531),
                                         auto=AutoMode.always.value)

    beta = raet.road.stacking.RoadStack(name='beta',
                                         ha=('0.0.0.0', 7532),
                                         main=True,
                                         auto=AutoMode.always.value)

    remote = raet.road.estating.RemoteEstate(stack=alpha,
                                             ha=beta.ha)

    alpha.addRemote(remote)

    alpha.join(uid=remote.uid, cascade=True)

    stacks = [alpha, beta]
    while True:
        for stack in stacks:
            stack.serviceAll()
            stack.store.advanceStamp(0.1)
        if all([not stack.transactions for stack in stacks]):
            break
        time.sleep(0.1)

    for stack in stacks:
        stack.server.close()  # close the UDP socket
        stack.keep.clearAllDir()  # clear persisted data

    print("Finished\n")


def example2():
    alpha = raet.road.stacking.RoadStack(name='alpha',
                                         ha=('0.0.0.0', 7531),
                                         auto=AutoMode.always.value)

    beta = raet.road.stacking.RoadStack(name='beta',
                                        ha=('0.0.0.0', 7532),
                                        main=True,
                                        auto=AutoMode.always.value)

    remote = raet.road.estating.RemoteEstate(stack=alpha,
                                             ha=beta.ha)

    alpha.addRemote(remote)

    alpha.join(uid=remote.uid, cascade=True)

    stacks = [alpha, beta]
    while True:
        for stack in stacks:
            stack.serviceAll()
            stack.store.advanceStamp(0.1)
        if all([not stack.transactions for stack in stacks]):
            break
        time.sleep(0.1)

    print("Finished Handshake\n")

    msg =  {'subject': 'Example message alpha to beta',
            'content': 'The dict keys in this dict are not special any dict will do.',}

    alpha.transmit(msg, remote.uid)
    while True:
        for stack in stacks:
            stack.serviceAll()
            stack.store.advanceStamp(0.1)
        if all([not stack.transactions for stack in stacks]):
            break
        time.sleep(0.1)

    rx = beta.rxMsgs.popleft()
    print("{0}\n".format(rx))
    print("Finished Message alpha to beta\n")

    msg =  {'subject': 'Example message beta to alpha',
            'content': 'Messages are the core of raet.',}

    beta.transmit(msg, remote.uid)
    while True:
        for stack in stacks:
            stack.serviceAll()
            stack.store.advanceStamp(0.1)
        if all([not stack.transactions for stack in stacks]):
            break
        time.sleep(0.1)

    rx = alpha.rxMsgs.popleft()
    print("{0}\n".format(rx))
    print("Finished Message beta to alpha\n")

    for stack in stacks:
        stack.server.close()  # close the UDP socket
        stack.keep.clearAllDir()  # clear persisted data

    print("Finished\n")

def example3():
    alpha = raet.road.stacking.RoadStack(name='alpha',
                                         ha=('0.0.0.0', 7531),
                                         main=True,
                                         auto=AutoMode.always.value)

    beta = raet.road.stacking.RoadStack(name='beta',
                                        ha=('0.0.0.0', 7532),
                                        main=True,
                                        auto=AutoMode.always.value)

    gamma = raet.road.stacking.RoadStack(name='gamma',
                                        ha=('0.0.0.0', 7533),
                                        main=True,
                                        auto=AutoMode.always.value)

    remote = raet.road.estating.RemoteEstate(stack=alpha,
                                             name=beta.name,
                                             ha=beta.ha)
    alpha.addRemote(remote)
    alpha.join(uid=remote.uid, cascade=True)

    remote = raet.road.estating.RemoteEstate(stack=alpha,
                                             name=gamma.name,
                                             ha=gamma.ha)
    alpha.addRemote(remote)
    alpha.join(uid=remote.uid, cascade=True)

    remote = raet.road.estating.RemoteEstate(stack=beta,
                                             name=gamma.name,
                                             ha=gamma.ha)
    beta.addRemote(remote)
    beta.join(uid=remote.uid, cascade=True)

    stacks = [alpha, beta, gamma]
    serviceStacks(stacks)
    print("Finished Handshakes\n")

    msg =  {'subject': 'Example message alpha to whoever',
            'content': 'Hi',}
    for remote in alpha.remotes.values():
        alpha.transmit(msg, remote.uid)

    msg =  {'subject': 'Example message beta to whoever',
            'content': 'Hello.',}
    for remote in beta.remotes.values():
        beta.transmit(msg, remote.uid)

    msg =  {'subject': 'Example message gamma to whoever',
            'content': 'Good Day',}
    for remote in gamma.remotes.values():
        gamma.transmit(msg, remote.uid)

    serviceStacks(stacks)
    print("Finished Messages\n")

    for stack in stacks:
        print("Stack {0} received:\n".format(stack.name))
        while stack.rxMsgs:
            msg, source = stack.rxMsgs.popleft()
            print("source = '{0}'.\nmsg= {1}\n".format(source, msg))


    for stack in stacks:
        stack.server.close()  # close the UDP socket
        stack.keep.clearAllDir()  # clear persisted data

    print("Finished\n")


if __name__ == "__main__":
    example1()
    example2()
    example3()
