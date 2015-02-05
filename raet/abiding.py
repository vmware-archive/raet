# -*- coding: utf-8 -*-
'''
Globals to be used with from abiding import *

Python 2 to 3 Support
'''

# pylint: skip-file
# pylint: disable=C0103

# Import python libs
import sys

# Python2to3 support
if sys.version > '3':  # Python3
    long = int
    basestring = (str, bytes)
    unicode = str
    xrange = range

    def ns2b(x):
        """
        Converts from native str type to native bytes type
        """
        return x.encode('ISO-8859-1')

    def ns2u(x):
        """
        Converts from native str type to native unicode type
        """
        return x

else:  # Python2
    # long = long
    # basestring = basestring
    # unicode = unicode

    def ns2b(x):
        """
        Converts from native str type to native bytes type
        """
        return x

    def ns2u(x):
        """
        Converts from native str type to native unicode type
        """
        return unicode(x)
