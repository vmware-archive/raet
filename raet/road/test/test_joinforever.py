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


    print "\n********* Join Forever Transaction **********"
    #transacting.Joiner.Timeout = 0 # make join go on forever
    stack1.join(timeout=0.0) # make join go on forever
    timer = StoreTimer(store=store, duration=30.0)
    while (stack1.transactions or stack0.transactions) and not timer.expired:
        stack1.serviceAll()
        if timer.elapsed > 20.0:
            stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack0.name,
                                                         remote.eid,
                                                         remote.joined)
    for remote in stack1.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack1.name,
                                                         remote.eid,
                                                         remote.joined)

    print "{0} Stats".format(stack0.name)
    for key, val in stack0.stats.items():
        print "   {0}={1}".format(key, val)
    print
    print "{0} Stats".format(stack1.name)
    for key, val in stack1.stats.items():
        print "   {0}={1}".format(key, val)
    print

    print "\n********* Join Default Timeout Transaction **********"
    stack1.join(timeout=None)
    timer.restart()
    while (stack1.transactions or stack0.transactions) and not timer.expired:
        stack1.serviceAll()
        if timer.elapsed > 20.0:
            stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack0.name,
                                                         remote.eid,
                                                         remote.joined)
    for remote in stack1.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack1.name,
                                                         remote.eid,
                                                         remote.joined)
    print "{0} Stats".format(stack0.name)
    for key, val in stack0.stats.items():
        print "   {0}={1}".format(key, val)
    print
    print "{0} Stats".format(stack1.name)
    for key, val in stack1.stats.items():
        print "   {0}={1}".format(key, val)
    print

    for uid in stack0.remotes:
        stack0.removeRemote(uid)
    for uid in stack1.remotes:
        stack1.removeRemote(uid)

    if postClearMaster:
        keeping.clearAllRoadSafe(masterDirpath)
    if postClearMinion:
        keeping.clearAllRoadSafe(m0Dirpath)

    print "Road {0}".format(stack0.name)
    print stack0.keep.loadLocalData()
    print stack0.keep.loadAllRemoteData()
    print "Safe {0}".format(stack0.name)
    print stack0.safe.loadLocalData()
    print stack0.safe.loadAllRemoteData()
    print

    print "Road {0}".format(stack1.name)
    print stack1.keep.loadLocalData()
    print stack1.keep.loadAllRemoteData()
    print "Safe {0}".format(stack1.name)
    print stack1.safe.loadLocalData()
    print stack1.safe.loadAllRemoteData()
    print

    print "\n********* Join Default Timeout Transaction After Clear Keeps **********"
    stack1.join(timeout=None)
    timer.restart()
    while (stack1.transactions or stack0.transactions) and not timer.expired:
        stack1.serviceAll()
        if timer.elapsed > 20.0:
            stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack0.name,
                                                         remote.eid,
                                                         remote.joined)
    for remote in stack1.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack1.name,
                                                         remote.eid,
                                                         remote.joined)

    print "{0} Stats".format(stack0.name)
    for key, val in stack0.stats.items():
        print "   {0}={1}".format(key, val)
    print
    print "{0} Stats".format(stack1.name)
    for key, val in stack1.stats.items():
        print "   {0}={1}".format(key, val)
    print

    print "\n********* Join Forever Timeout Transaction After Clear Keeps**********"
    stack1.join(timeout=0.0)
    timer.restart()
    while (stack1.transactions or stack0.transactions) and not timer.expired:
        stack1.serviceAll()
        if timer.elapsed > 20.0:
            stack0.serviceAll()
        store.advanceStamp(0.1)

    for remote in stack0.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack0.name,
                                                         remote.eid,
                                                         remote.joined)
    for remote in stack1.remotes.values():
        print "{0} Remote Estate {1} joined= {2}".format(stack1.name,
                                                         remote.eid,
                                                         remote.joined)

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

