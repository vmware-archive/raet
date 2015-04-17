# -*- coding: utf-8 -*-
'''
Helpers for multiprocessing module

'''

from multiprocessing import Value, Lock


class Counter():
    def __init__(self, init=0):
        self.value = Value('i', 0)
        self.lock = Lock()

    def inc(self):
        with self.lock:
            self.value.value += 1

    def get(self):
        with self.lock:
            return self.value.value
