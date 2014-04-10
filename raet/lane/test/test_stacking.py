# -*- coding: utf-8 -*-
'''
Tests to try out stacking. Potentially ephemeral

'''
# pylint: skip-file
from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer

from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting
from raet.lane import yarding, stacking

def testStackUxd(kind=raeting.packKinds.json):
    '''
    initially


    '''
    console.reinit(verbosity=console.Wordage.concise)

    stacking.LaneStack.Pk = kind

    #lord stack
    #yard0 = yarding.Yard(name='lord')
    stack0 = stacking.LaneStack(dirpath='/tmp/raet/test_stacking',
                                sockdirpath='/tmp/raet/test_stacking')

    #serf stack
    #yard1 = yarding.Yard(name='serf', yid=1)
    stack1 = stacking.LaneStack(dirpath='/tmp/raet/test_stacking',
                                sockdirpath='/tmp/raet/test_stacking')

    stack0.addRemote(yarding.RemoteYard(ha=stack1.local.ha))
    stack1.addRemote(yarding.RemoteYard(ha=stack0.local.ha))
    #stack0.addRemoteYard(stack1.local)
    #stack1.addRemoteYard(stack0.local)

    print "{0} yard name={1} ha={2}".format(stack0.name, stack0.local.name, stack0.local.ha)
    print "{0} yards=\n{1}".format(stack0.name, stack0.remotes)
    print "{0} names=\n{1}".format(stack0.name, stack0.uids)

    print "{0} yard name={1} ha={2}".format(stack1.name, stack1.local.name, stack1.local.ha)
    print "{0} yards=\n{1}".format(stack1.name, stack1.remotes)
    print "{0} names=\n{1}".format(stack1.name, stack1.uids)

    print "\n********* UXD Message lord to serf serf to lord **********"
    msg = odict(what="This is a message to the serf. Get to Work", extra="Fix the fence.")
    stack0.transmit(msg=msg)

    msg = odict(what="This is a message to the lord. Let me be", extra="Go away.")
    stack1.transmit(msg=msg)

    timer = Timer(duration=0.5)
    timer.restart()
    while not timer.expired:
        stack0.serviceAll()
        stack1.serviceAll()


    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print

    print "\n********* Multiple Messages Both Ways **********"

    stack1.transmit(odict(house="Mama mia1", queue="fix me"), None)
    stack1.transmit(odict(house="Mama mia2", queue="help me"), None)
    stack1.transmit(odict(house="Mama mia3", queue="stop me"), None)
    stack1.transmit(odict(house="Mama mia4", queue="run me"), None)

    stack0.transmit(odict(house="Papa pia1", queue="fix me"), None)
    stack0.transmit(odict(house="Papa pia2", queue="help me"), None)
    stack0.transmit(odict(house="Papa pia3", queue="stop me"), None)
    stack0.transmit(odict(house="Papa pia4", queue="run me"), None)

    #big packets
    stuff = []
    for i in range(10000):
        stuff.append(str(i).rjust(10, " "))
    stuff = "".join(stuff)

    stack1.transmit(odict(house="Mama mia1", queue="big stuff", stuff=stuff), None)
    stack0.transmit(odict(house="Papa pia4", queue="gig stuff", stuff=stuff), None)

    timer.restart(duration=2)
    while not timer.expired:
        stack1.serviceAll()
        stack0.serviceAll()

    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print

    src = ('minion', 'serf', None)
    dst = ('master', None, None)
    route = odict(src=src, dst=dst)
    msg = odict(route=route, stuff="Hey buddy what is up?")
    stack0.transmit(msg)

    timer.restart(duration=2)
    while not timer.expired:
        stack1.serviceAll()
        stack0.serviceAll()

    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print

    estate = 'minion1'
    #lord stack yard0
    stack0 = stacking.LaneStack(name='lord',
                                lanename='cherry',
                                dirpath='/tmp/raet/test_stacking',
                                sockdirpath='/tmp/raet/test_stacking')

    #serf stack yard1
    stack1 = stacking.LaneStack(name='serf',
                                lanename='cherry',
                                dirpath='/tmp/raet/test_stacking',
                                sockdirpath='/tmp/raet/test_stacking')

    print "Yid", yarding.Yard.Yid

    print "\n********* Attempt Auto Accept ************"
    #stack0.addRemoteYard(stack1.local)
    yard = yarding.RemoteYard(name=stack0.local.name,
                            prefix='cherry',
                            dirpath='/tmp/raet/test_stacking')
    stack1.addRemote(yard)

    print "{0} yard name={1} ha={2}".format(stack0.name, stack0.local.name, stack0.local.ha)
    print "{0} yards=\n{1}".format(stack0.name, stack0.remotes)
    print "{0} names=\n{1}".format(stack0.name, stack0.uids)

    print "{0} yard name={1} ha={2}".format(stack1.name, stack1.local.name, stack1.local.ha)
    print "{0} yards=\n{1}".format(stack1.name, stack1.remotes)
    print "{0} names=\n{1}".format(stack1.name, stack1.uids)

    print "\n********* UXD Message serf to lord **********"
    src = (estate, stack1.local.name, None)
    dst = (estate, stack0.local.name, None)
    route = odict(src=src, dst=dst)
    msg = odict(route=route, stuff="Serf to my lord. Feed me!")
    stack1.transmit(msg=msg)

    timer = Timer(duration=0.5)
    timer.restart()
    while not timer.expired:
        stack0.serviceAll()
        stack1.serviceAll()


    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print

    print "\n********* UXD Message lord to serf **********"
    src = (estate, stack0.local.name, None)
    dst = (estate, stack1.local.name, None)
    route = odict(src=src, dst=dst)
    msg = odict(route=route, stuff="Lord to serf. Feed yourself!")
    stack0.transmit(msg=msg)


    timer = Timer(duration=0.5)
    timer.restart()
    while not timer.expired:
        stack0.serviceAll()
        stack1.serviceAll()

    print "{0} Received Messages".format(stack0.name)
    for msg in stack0.rxMsgs:
        print msg
    print

    print "{0} Received Messages".format(stack1.name)
    for msg in stack1.rxMsgs:
        print msg
    print

    print "{0} yard name={1} ha={2}".format(stack0.name, stack0.local.name, stack0.local.ha)
    print "{0} yards=\n{1}".format(stack0.name, stack0.remotes)
    print "{0} names=\n{1}".format(stack0.name, stack0.uids)

    print "{0} yard name={1} ha={2}".format(stack1.name, stack1.local.name, stack1.local.ha)
    print "{0} yards=\n{1}".format(stack1.name, stack1.remotes)
    print "{0} names=\n{1}".format(stack1.name, stack1.uids)

    stack0.server.close()
    stack1.server.close()

if __name__ == "__main__":
    testStackUxd(raeting.packKinds.json)
    testStackUxd(raeting.packKinds.pack)
