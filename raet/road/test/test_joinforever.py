# -*- coding: utf-8 -*-
'''
Tests to try out stacking. Potentially ephemeral

'''
# pylint: skip-file

import  os

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import keeping, estating, stacking, transacting

def test(preClearMaster=True, preClearMinion=True, postClearMaster=True, postClearMinion=True):
    '''
    initially
    master on port 7530 with eid of 1
    minion on port 7531 with eid of 0
    eventually
    master eid of 1
    minion eid of 2
    '''
    console.reinit(verbosity=console.Wordage.concise)

    transacting.Joiner.Timeout = 0 # make join go on forever

    store = storing.Store(stamp=0.0)

    #master stack
    masterName = "master"
    signer = nacling.Signer()
    masterSignKeyHex = signer.keyhex
    privateer = nacling.Privateer()
    masterPriKeyHex = privateer.keyhex
    masterDirpath = os.path.join('/tmp/raet/road', 'keep', masterName)

    #minion0 stack
    minionName0 = "minion0"
    signer = nacling.Signer()
    minionSignKeyHex = signer.keyhex
    privateer = nacling.Privateer()
    minionPriKeyHex = privateer.keyhex
    m0Dirpath = os.path.join('/tmp/raet/road', 'keep', minionName0)

    if preClearMaster:
        keeping.clearAllRoadSafe(masterDirpath)
    if preClearMinion:
        keeping.clearAllRoadSafe(m0Dirpath)


    local = estating.LocalEstate(  eid=1,
                                    name=masterName,
                                    sigkey=masterSignKeyHex,
                                    prikey=masterPriKeyHex,)
    stack0 = stacking.RoadStack(name=masterName,
                               local=local,
                               auto=True,
                               store=store,
                               main=True,
                               dirpath=masterDirpath)


    local = estating.LocalEstate(  eid=0,
                                    name=minionName0,
                                    ha=("", raeting.RAET_TEST_PORT),
                                    sigkey=minionSignKeyHex,
                                    prikey=minionPriKeyHex,)
    stack1 = stacking.RoadStack(name=minionName0,
                               local=local,
                               store=store,
                               dirpath=m0Dirpath)


    print "\n********* Join Transaction **********"
    stack1.join()
    timer = StoreTimer(store=store, duration=30.0)
    while (stack1.transactions or stack0.transactions) and not timer.expired:
        stack1.serviceAll()
        if timer.elapsed > 20.0:
            stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "Remote Estate {0} joined= {1}".format(remote.eid, remote.joined)
    for remote in stack1.remotes.values():
        print "Remote Estate {0} joined= {1}".format(remote.eid, remote.joined)


    print "{0} eid={1}".format(stack0.name, stack0.local.uid)
    print "{0} remotes=\n{1}".format(stack0.name, stack0.remotes)
    print "{0} transactions=\n{1}".format(stack0.name, stack0.transactions)
    print "{0} eid={1}".format(stack1.name, stack1.local.uid)
    print "{0} remotes=\n{1}".format(stack1.name, stack1.remotes)
    print "{0} transactions=\n{1}".format(stack1.name, stack1.transactions)


    print "Keep {0}".format(stack0.name)
    print stack0.keep.loadLocalData()
    print stack0.keep.loadAllRemoteData()
    print "Safe {0}".format(stack0.name)
    print stack0.safe.loadLocalData()
    print stack0.safe.loadAllRemoteData()
    print

    print "Keep {0}".format(stack1.name)
    print stack1.keep.loadLocalData()
    print stack1.keep.loadAllRemoteData()
    print "Safe {0}".format(stack1.name)
    print stack1.safe.loadLocalData()
    print stack1.safe.loadAllRemoteData()
    print

    print "{0} Stats".format(stack0.name)
    for key, val in stack0.stats.items():
        print "   {0}={1}".format(key, val)
    print
    print "{0} Stats".format(stack1.name)
    for key, val in stack1.stats.items():
        print "   {0}={1}".format(key, val)
    print

    stack0.server.close()
    stack1.server.close()

    if postClearMaster:
        keeping.clearAllRoadSafe(masterDirpath)
    if postClearMinion:
        keeping.clearAllRoadSafe(m0Dirpath)



if __name__ == "__main__":
    test(True, True, True, True)

