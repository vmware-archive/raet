# -*- coding: utf-8 -*-
'''
Helpers for multiprocessing module

'''

from multiprocessing import Value, Lock


class Counter():
    '''
    Multiprocessing integer Value() wrapper that can safely be increased and read.
    '''

    def __init__(self, init=0):
        self.value = Value('i', 0)
        self.lock = Lock()

    def inc(self):
        '''
        Increases the value by 1
        '''
        with self.lock:
            self.value.value += 1

    def get(self):
        '''
        Value getter

        :return: the counter value
        '''
        with self.lock:
            return self.value.value
