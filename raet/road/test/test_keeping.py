# -*- coding: utf-8 -*-
'''
Tests to try out keeping. Potentially ephemeral

'''
# pylint: skip-file
# pylint: disable=C0103
import os

from ioflo.base.odicting import odict

from raet import raeting, nacling
from raet.road import estating, keeping, stacking


def test(dirpath='/tmp/raet/test_keeping'):
    '''
    Test keeping.
    '''
    masterDirpath = os.path.join(dirpath, 'keep', 'master')
    signer = nacling.Signer()
    masterSignKeyHex = signer.keyhex
    masterVerKeyHex = signer.verhex
    privateer = nacling.Privateer()
    masterPriKeyHex = privateer.keyhex
    masterPubKeyHex = privateer.pubhex

    m1Dirpath = os.path.join(dirpath, 'keep', 'minion1')
    signer = nacling.Signer()
    m1SignKeyHex = signer.keyhex
    m1VerKeyHex = signer.verhex
    privateer = nacling.Privateer()
    m1PriKeyHex = privateer.keyhex
    m1PubKeyHex = privateer.pubhex

    signer = nacling.Signer()
    m2SignKeyHex = signer.keyhex
    m2VerKeyHex = signer.verhex
    privateer = nacling.Privateer()
    m2PriKeyHex = privateer.keyhex
    m2PubKeyHex = privateer.pubhex

    signer = nacling.Signer()
    m3SignKeyHex = signer.keyhex
    m3VerKeyHex = signer.verhex
    privateer = nacling.Privateer()
    m3PriKeyHex = privateer.keyhex
    m3PubKeyHex = privateer.pubhex

    keeping.clearAllRoadSafe(masterDirpath)
    keeping.clearAllRoadSafe(m1Dirpath)

    #master stack
    dirpath = os.path.join(dirpath, 'keep', 'master')
    local = estating.LocalEstate(  eid=1,
                                    name='master',
                                    sigkey=masterSignKeyHex,
                                    prikey=masterPriKeyHex,)
    stack0 = stacking.RoadStack(local=local, dirpath=masterDirpath)

    print("{0} dirpath = {1}".format(stack0.name, stack0.keep.dirpath))

    stack0.addRemote(estating.RemoteEstate(eid=2,
                                    ha=('127.0.0.1', 7532),
                                    verkey=m1VerKeyHex,
                                    pubkey=m1PubKeyHex,))

    stack0.addRemote(estating.RemoteEstate(eid=3,
                                    ha=('127.0.0.1', 7533),
                                    verkey=m2VerKeyHex,
                                    pubkey=m2PubKeyHex,))

    #minion stack
    dirpath = os.path.join(dirpath, 'keep', 'minion1')
    local = estating.LocalEstate(   eid=2,
                                     name='minion1',
                                     ha=("", raeting.RAET_TEST_PORT),
                                     sigkey=m1SignKeyHex,
                                     prikey=m1PriKeyHex,)
    stack1 = stacking.RoadStack(local=local, dirpath=m1Dirpath)

    print("{0} dirpath = {1}".format(stack1.name, stack1.keep.dirpath))


    stack1.addRemote(estating.RemoteEstate(eid=1,
                                    ha=('127.0.0.1', 7532),
                                    verkey=masterVerKeyHex,
                                    pubkey=masterPubKeyHex,))

    stack1.addRemote(estating.RemoteEstate(eid=4,
                                    ha=('127.0.0.1', 7534),
                                    verkey=m3VerKeyHex,
                                    pubkey=m3PubKeyHex,))

    stack0.clearLocal()
    stack0.clearRemoteKeeps()
    stack1.clearLocal()
    stack1.clearRemoteKeeps()

    stack0.dumpLocal()
    stack0.dumpRemotes()

    stack1.dumpLocal()
    stack1.dumpRemotes()

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

    stack0.server.close()
    stack1.server.close()

    #master stack
    dirpath = os.path.join(dirpath, 'keep', 'master')
    local = estating.LocalEstate(  eid=1,
                                    name='master',
                                    sigkey=masterSignKeyHex,
                                    prikey=masterPriKeyHex,)
    stack0 = stacking.RoadStack(local=local, dirpath=masterDirpath)

    print("{0} dirpath = {1}".format(stack0.name, stack0.keep.dirpath))

    #minion stack
    dirpath = os.path.join(dirpath, 'keep', 'minion1')
    local = estating.LocalEstate(   eid=2,
                                     name='minion1',
                                     ha=("", raeting.RAET_TEST_PORT),
                                     sigkey=m1SignKeyHex,
                                     prikey=m1PriKeyHex,)
    stack1 = stacking.RoadStack(local=local, dirpath=m1Dirpath)

    print("{0} dirpath = {1}".format(stack1.name, stack1.keep.dirpath))


    stack0.loadLocal()
    print stack0.local.name, stack0.local.eid, stack0.local.sid, stack0.local.ha, stack0.local.signer, stack0.local.priver
    stack1.loadLocal()
    print stack1.local.name, stack1.local.eid, stack1.local.sid, stack1.local.ha, stack1.local.signer, stack1.local.priver

    stack0.clearLocal()
    stack0.clearRemoteKeeps()
    stack1.clearLocal()
    stack1.clearRemoteKeeps()

    stack0.server.close()
    stack1.server.close()



if __name__ == "__main__":
    test()
    test(dirpath='/var/cache/raet')
