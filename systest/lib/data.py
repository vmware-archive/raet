# -*- coding: utf-8 -*-
'''
Data providers for system tests

'''

from ioflo.aid.odicting import odict
from BitVector import BitVector
import data


def getStuff(name='master', size=1024, number=0):
    '''
    Generate padding stuff for message data unique for the given sender name and the message number and size.
    Always returns equal result for equal arguments. Can be used as for data generation as for result check.

    :param name: sender's name
    :param size: data size
    :param number: message number
    :return: string of the given length containing the data
    '''
    alpha = '{0}{1}{2}{3}'.format(name, number,
                                  ''.join([chr(n) for n in xrange(ord('A'), ord('Z') + 1)]),
                                  ''.join([chr(n) for n in xrange(ord('a'), ord('z') + 1)]))
    num = size / len(alpha)
    ret = ''.join([alpha for _ in xrange(num)])
    num = size - len(ret)
    ret = ''.join([ret, alpha[:num]])
    assert len(ret) == size, 'Coding fault: generated data size not equal to requested'
    return ret


def createData(name='master', size=1024, number=0, house='manor', queue='stuff'):
    '''
    Create message dictionary with padding of the given size (so the actual message will be bigger)

    :param name: sender name
    :param size: padding size
    :param number: message number in sequence (just for unicity)
    :param house: house name
    :param queue: queue name
    :return: odict containing the generated message
    '''
    stuff = getStuff(name, size, number)
    ret = odict(house=house, queue=queue, sender=name, number=number, stuff=stuff)
    return ret


def generateMessages(name, size, count, house='manor', queue='stuff'):
    '''
    Messages generator.

    :param name: sender name
    :param size: message padding size
    :param count: messages count
    :param house: house name
    :param queue: queue name
    :return: generator object for count of messages
    '''
    for i in xrange(count):
        yield createData(name, size, i, house, queue)


class MessageVerifier():
    '''
    Provide a way to collect information about received messages and check messages contents.

    Current limitations:
        - all messages are of the same padding size
        - all remotes should send the same message count
        - house and queue are the same for all (probably should be removed at all)

    Usage:
        - for each message use verifyMessage method to verify it and register the fact it's received
        - at the end call checkAllDone and print results
    '''
    def __init__(self, size, msgCount, remoteCount, house, queue):
        '''
        Setup instance

        :param size: message padding size
        :param msgCount: expected per remote message count
        :param remoteCount: expected remote count
        :param house: house name
        :param queue: queue name
        '''
        self.size = size
        self.count = msgCount
        self.remoteCount = remoteCount
        self.house = house
        self.queue = queue
        self.received = {}

    def verifyMessage(self, msg):
        '''
        Verify the given message content and mark it as received. The message have to be one of created by the
        :func:`generateMessage` generator.

        :param msg: message to verify
        '''
        sender = msg[0]['sender']
        number = msg[0]['number']
        expectedMsg = data.createData(sender, self.size, number, self.house, self.queue)
        equal = expectedMsg == msg[0]

        if sender not in self.received:
            self.received[sender] = (BitVector(size=self.count),  # received
                                     BitVector(size=self.count),  # duplicated
                                     BitVector(size=self.count))  # wrong content

        if self.received[sender][0][number]:  # duplicate
            self.received[sender][1][number] = 1
        else:  # first time received
            self.received[sender][0][number] = 1
        if not equal:
            self.received[sender][2][number] = 1

    def checkAllDone(self):
        '''
        Check the status of all messages verified previously. For each remote writes how much messages duplicated,
        lost and broken.

        :return: a list of strings containing error messages. Empty list means no error
        '''
        errors = []
        if self.remoteCount != len(self.received):
            errors.append('remote count not match {0} vs {1}'.format(self.remoteCount, len(self.received)))
        for name, results in self.received.iteritems():
            rcv = results[0].count_bits()
            dup = results[1].count_bits()
            bad = results[2].count_bits()
            if rcv != self.count:
                errors.append('{0}: lost {1} messages'.format(name, self.count - rcv))
            if dup:
                errors.append('{0}: got duplications for {1} messages'.format(name, dup))
            if bad:
                errors.append('{0}: {1} received messages are broken'.format(name, bad))
        return errors

