==============
Tutorial
==============

RAET is written in python.

RAET communications is centered on a communications Stack object.
There are currently two types of RAET Stacks. A RoadStack provides communication between
IP hosts via UDP sockets and a LaneStack provides communication between processes on the
same host via Unix Domain Sockets (UXD) on unix or mail slots on windows.

Although a RoadStack has a flexible set of configuration parameters,
it tries to use intelligent defaults where ever possible.

The following python snippet shows how to create a RoadStack.


To install on a UNIX based system use pip:

.. code-block:: python

    import raet
    stack = raet.road.stacking.RoadStack()

On OS X:

.. code-block:: bash

    $ sudo pip install raet

