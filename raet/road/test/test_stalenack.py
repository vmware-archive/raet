# -*- coding: utf-8 -*-
'''
Tests to try out stacking. Potentially ephemeral

'''
# pylint: skip-file
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing
from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import packeting, estating, keeping, stacking, transacting


def test():
    '''
    initially
    master on port 7530 with eid of 1
    minion on port 7531 with eid of 0
    eventually
    master eid of 1
    minion eid of 2
    '''
    console.reinit(verbosity=console.Wordage.concise)

    store = storing.Store(stamp=0.0)

    #master stack
    masterName = "master"
    signer = nacling.Signer()
    masterSignKeyHex = signer.keyhex
    privateer = nacling.Privateer()
    masterPriKeyHex = privateer.keyhex
    dirpathMaster = os.path.join('/tmp/raet', 'keep', masterName)

    #minion0 stack
    minionName0 = "minion0"
    signer = nacling.Signer()
    minionSignKeyHex = signer.keyhex
    privateer = nacling.Privateer()
    minionPriKeyHex = privateer.keyhex
    dirpathMinion0 = os.path.join('/tmp/raet', 'keep', minionName0)

    keeping.clearAllKeepSafe(dirpathMaster)
    keeping.clearAllKeepSafe(dirpathMinion0)

    local = estating.LocalEstate(   eid=1,
                                     name=masterName,
                                     sigkey=masterSignKeyHex,
                                     prikey=masterPriKeyHex,)
    stack0 = stacking.RoadStack(local=local,
                               store=store,
                               auto=True,
                               main=True,
                               dirpath=dirpathMaster)


    local = estating.LocalEstate(   eid=0,
                                     name=minionName0,
                                     ha=("", raeting.RAET_TEST_PORT),
                                     sigkey=minionSignKeyHex,
                                     prikey=minionPriKeyHex,)
    stack1 = stacking.RoadStack(local=local,
                               store=store,
                               dirpath=dirpathMinion0)


    print "\n********* Join Transaction **********"
    stack1.join()
    timer = Timer(duration=2)
    timer.restart(duration=2)
    while not timer.expired:
        stack1.serviceAll()
        stack0.serviceAll()
    for remote in stack0.remotes.values():
        print "Remote Estate {0} joined= {1}".format(remote.eid, remote.joined)
    for remote in stack1.remotes.values():
        print "Remote Estate {0} joined= {1}".format(remote.eid, remote.joined)

    print "\n********* Allow Transaction **********"
    stack1.allow()
    timer.restart(duration=2)
    while not timer.expired:
        stack1.serviceAll()
        stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "Remote Estate {0} allowed= {1}".format(remote.eid, remote.allowed)
    for remote in stack1.remotes.values():
        print "Remote Estate {0} allowed= {1}".format(remote.eid, remote.allowed)

    print "\n********* Message Transactions Both Ways **********"
    #stack1.transmit(odict(house="Oh Boy1", queue="Nice"))
    stack0.transmit(odict(house="Yeah Baby1", queue="Good"))

    timer.restart(duration=1)
    while not timer.expired:
        stack0.serviceAllTx() # transmit but leave receives in socket buffer

    timer.restart(duration=1)
    while not timer.expired:
        stack1.serviceAllRx() # receive but leave transmits in queue

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
            print msg
    print

    stack0.transactions = odict() #clear transactions so RX is stale correspondent

    timer.restart(duration=2)
    while not timer.expired:
        stack1.serviceAllTx() #send queued transmits
        stack0.serviceAllRx() # receive stale packets from buffer

    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Stats".format(stack0.name)
    for key, val in stack0.stats.items():
        print "   {0}={1}".format(key, val)
    print
    print "{0} Stats".format(stack1.name)
    for key, val in stack1.stats.items():
        print "   {0}={1}".format(key, val)
    print

    """
    stale_correspondent_attempt=1
    stale_correspondent_nack=1
    """


    stack0.server.close()
    stack1.server.close()

    stack0.clearLocal()
    stack0.clearRemoteKeeps()
    stack1.clearLocal()
    stack1.clearRemoteKeeps()


if __name__ == "__main__":
    test()

