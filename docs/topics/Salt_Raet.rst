============
Salt with RAET
============

The current version of Salt using Raet is a hybrid architecture due to the amount
of work it would have taken to convert all of Salt to a RAET-Ioflo style architecture.
Mostly the changes were made to replace Zero-MQ with RAET but not change everything
else to a micro-threaded architecture. The following figure shows notionally how
Salt works on top of RAET. At some point in the future more of Salt will be migrated
to a micro-threaded architecture as feasible. The constraint being that Salt must
still support ZeroMQ.

.. figure:: /images/RaetSaltAlphaArchitecture.png
    :alt: RAET Salt archtecture diagram

    The archtecture of Salt when using RAET.



