# -*- coding: utf-8 -*-
'''
Linux tc netem adapter

'''

from subprocess import call, check_output

SU_CMD = ['sudo']
NETEM_DEL_LO_ROOT_CMD = ['tc', 'qdisc', 'del', 'dev', 'lo', 'root']
NETEM_ADD_LO_ROOT_CMD = ['tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'netem']
NETEM_SHOW_LO = ['tc', 'qdisc', 'show', 'dev', 'lo']


def delay(time=100, jitter=10, correlation=25):
    '''
    Add loopback interface netem rule to delay packets

    :param time: delay value in ms
    :param jitter: deviation from the specified duration in ms
    :param correlation:
    :return: True if no error
    '''
    time = '{0}ms'.format(time)
    jitter = '{0}ms'.format(jitter)
    correlation = '{0}%'.format(correlation)
    cmd = SU_CMD + NETEM_ADD_LO_ROOT_CMD + ['delay', time, jitter, correlation]
    print("calling cmd: {0}".format(cmd))
    return call(cmd) == 0


def loss(percent=5, correlation=25):
    '''
    Add loopback interface netem rule to loss packets

    :param percent: loss percentage
    :param correlation:
    :return: True if no error
    '''
    percent = '{0}%'.format(percent)
    correlation = '{0}%'.format(correlation)
    cmd = SU_CMD + NETEM_ADD_LO_ROOT_CMD + ['loss', percent, correlation]
    return call(cmd) == 0


def duplicate(percent=5, correlation=25):
    '''
    Add loopback interface netem rule to loss packets

    :param percent: loss percentage
    :param correlation:
    :return: True if no error
    '''
    percent = '{0}%'.format(percent)
    correlation = '{0}%'.format(correlation)
    cmd = SU_CMD + NETEM_ADD_LO_ROOT_CMD + ['duplicate', percent, correlation]
    return call(cmd) == 0


def reorder(time=100, percent=10, correlation=25):
    '''
    Add loopback interface netem rule to delay packets

    :param time: delay value, ms
    :param percent: deviation from the specified duration, ms
    :param correlation: how much packets
    :return: True if no error
    '''
    time = '{0}ms'.format(time)
    percent = '{0}%'.format(percent)
    correlation = '{0}%'.format(correlation)
    cmd = SU_CMD + NETEM_ADD_LO_ROOT_CMD + ['delay', time, 'reorder', percent, correlation]
    return call(cmd) == 0


def corrupt(percent=5, correlation=25):
    '''
    Add loopback interface netem rule to delay packets

    :param duration: corruption percentage
    :param correlation: how much packets
    :return: True if no error
    '''
    percent = '{0}%'.format(percent)
    correlation = '{0}%'.format(correlation)
    cmd = SU_CMD + NETEM_ADD_LO_ROOT_CMD + ['corrupt', percent, correlation]
    return call(cmd) == 0


def clear():
    '''
    Clear all netem rules on loopback interface

    :return: True if no error
    '''
    cmd = SU_CMD + NETEM_DEL_LO_ROOT_CMD
    return call(cmd) == 0


def check():
    '''
    Returns the count of netem rules applied to the loopback

    :return: The count of netem rules
    '''
    cmd = SU_CMD + NETEM_SHOW_LO
    out = check_output(cmd)
    return len(out.splitlines())