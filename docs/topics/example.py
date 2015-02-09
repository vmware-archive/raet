'''
RAET Tutorial Example
'''
import time

import raet
from raet import raeting

def example():
    alpha = raet.road.stacking.RoadStack(name='alpha',
                                         ha=('0.0.0.0', 7531),
                                         auto=raeting.autoModes.always)

    beta = raet.road.stacking.RoadStack(name='beta',
                                         ha=('0.0.0.0', 7532),
                                         main=True,
                                         auto=raeting.autoModes.always)

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

if __name__ == "__main__":
    example()
