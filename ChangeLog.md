------------------
CHANGE LOG
-------------------
-----------
20151017
----------
v0.6.4

Fixed issue with windows errno
Minor corrections
Fixed imports of ioflo to be compat with ioflo 1.2.3
Removed unused imports and normalized some imports


-----------
20150310
----------
v0.6.3

Changed imports ioflo.base.nonblocking to be compat with ioflo 1.2.1

-----------
20150212
----------
v0.6.1

Updated tutorial
fixed log message


-----------
20150212
----------
v0.6.0

Added enum support using python 3.4 enums via backport enum34
raeting.py NamedTuples replaced with enums

-----------
20150211
----------
v0.5.3

Added tutorial documents
Fixed merge error
Fixed bugs


-----------
20150204
----------
v0.5.2

Updated setup.py dependencies

-----------
20150204
----------
v0.5.1

Windows impossible file check
More coverage tests

-----------
20150204
----------
v0.5.0

Python3 support



-----------
20150201
----------
v0.4.7

Added support for burst size limits in the Message transaction to deal with
limits on UDP receive buffers on some hosts. Significant changes to how the
Messenger and Messagent transactions work.

Added more units tests for messaging.


-----------
20150128
----------
v0.4.6

Silently handles errno.ECONNRESET on transmit in Stack._handleOneTx for windows



-----------
20150128
----------
v0.4.5

Support for simultaneous vacuous joins between same two estates
Correctly terminates one of the joins and allows other to complete
Bugfixes
More tests

-----------
20150120
----------
v0.4.4

Compatibility with ioflo 1.1.5

-----------
20150120
----------
v0.4.3

Minor bug fixes
More units tests

Changed semantics for initial alived state. As soon as estate completes
initial bootstrap to allowed state it is also alived instead of waiting for
manage alive transactions to complete. This enables messaging to commence
immediately upon allowed.


-----------
20141201
----------
v0.4.2

fixed windows compat for autoaccept yard



---------
20141125
----------
v0.4.0

Changed the allow transaction to bigendian structs not little endian
This will break interoperability with older versions of raet.
Msgpack is already bigendian and future binary packet header for raet
should be big endian.


more coverage unit tests
fixed some bugs
updated log messages
updated comments
updated indenting
added more presence unit tests

---------
20141029
----------
v0.3.8

Added more unit tests
Updated and fixed some tests
Joiner and Joinent transactions now persist local data (puid) upon successful completion


---------
20141024
----------
v0.3.7

Added lots of unit tests for join (Joiner and Joinent) transaction
Fixed some bugs
Added better support (but not complete ) for windows



---------
20141009
----------
v0.3.6

Made default timeout for Messenger and Messengent transaction to be 0.0, that is,
never

Added timout parameter to RoadStack.transmit() so timeout can be set on a
message transaction by transaction basis
Added timeout to txMsgs deque triple for RoadStack that is, (msg, uid, timeout)



---------
20141008
----------
v0.3.5

Fixed bug in RoadKeep.loadRemoteRoleData()


---------
20141006
----------
v0.3.4

Added socket error handling for additional failure modes in Stack._handleOneTx
for sending

---------
20141006
----------
v0.3.3

Fixed Python3 incompatabilities



---------
20141002
----------
v0.3.02

Fixed bug in allow transaction that prevented allow on restart
Fixed issue with unicode fqdn on debian


---------
20140924
----------
v0.3.01

New support for peer RAET channel. Changed semantics of how Join transactions
works. This will allows peer to peer joining

---------
20140729
---------

v0.2.11

Lookup remote in stack handleOneRx by using packet.index since it already
substitutes ha if se is zero. Then also lookup remote in haRemotes if not found
in .uidRemotes

Update joinent transaction

Change the way persistence reaping is handled. Instead of removing remote from
memory, mark it with .reaped attribute. This avoide problematic use case of
having to restoreRemote from disk when doing lookup in Joinent.
Update .manage

Also unreap anytime a packet is received from a remote

---------
20140724
---------

v0.2.10

Transactions now referenced and processed per remote not at stack.transactions
sets stage for later doing broadcast transactions

---------
20140724
---------

v0.2.09

Finished support for role keep files in Road

---------
20140723
---------

v0.2.08

Support for msgpack in Keep files
more support for role in Road estates
fixes in join transaction

---------
20140722
---------

v0.2.07

bugfix

---------
20140722
---------

v0.2.06

If verify keep fails then clear the keep file. This autoclears cache
when upgrading format of keep file.
Also more support for role.

---------
20140721
---------

v0.2.05

Refactored odicts indexing access attributes for remotes so can now access
by uid, by name, or by ha. Updated associated accessors
Provides more consistent view onto Stack Road or Lane
Prepatory to adding remote.role for key management

---------
20140715
---------

v0.2.04

Fixed race condition in Yarding makedirs

Road Keep files are now stored by name not uid

---------
20140714
---------

v0.2.03

Added parameter to verify keep to allow passing in verify fields

---------
20140711
---------

v0.2.02

refactor nack handling
refactor moveRemote, removeRemote, renameRemote


---------
20140709
---------

v0.2.01

rxMsgs queue on LaneStack now a duple (msg, sender)
where
msg is message body dict
sender is unique name of remote yard that sent the message


---------
20140708
---------

v0.2.00

Ephemeral Lane Yards
Yards now use a uuid for the session id so that there is no need to persist
any Lane data in order to resolve ambiguous multi-page messages should one
side restart in the middle of a multi-page message.
No more keep for LaneStack.


---------
20140708
---------

v0.1.03

fixed python 2.6 bug

---------
20140708
---------

v0.1.02

Fixed bug in nacling catching wrong exception on verify

Changed rxMsgs queue to be duple of (msg, name)
so that application layer has access to remote name that sent the msg.

---------
20140701
---------

v0.1.01

Added nacling.uuid function to allow unique yard names

---------
20140701
---------

v0.1.00

Minor fixup prepping for release with SaltStack Release Candidate

---------
20140625
---------

v0.0.31

Fixed roadstack .manage method to used aliveds


---------
20140625
---------

v0.0.30

Reverted semantics of join wrt removing remotes. No longer removes rejected remotes
out of band or future presence expire mechanism is needed to remove rejected remotes

---------
20140625
---------

v0.0.29

Fixed a bug on renew in Joiner transaction

---------
20140625
---------

v0.0.28

Fixed some race conditions


---------
20140625
---------

v0.0.27

Support for reaping and restoring dead remotes on main estate road stack
Support for saving and resending stale messages when session changes on rejoin
or reallow
Some other fixes



---------
20140623
---------

v0.0.26

RoadStack.manage now provide underlying support needed for presence events
and filtering of remote targets based on availabilty (allowed) status

---------
20140617
---------

v0.0.25

Fixed race condisitons with two way join transactions now detects if join in
progress added nack refuse so do not delete remote and transactions

now works better with key managment when rejecting remotes.

---------
20140617
---------

v0.0.24

fixed error in lane yard transmit

---------
20140617
---------

v0.0.23

Better support for two way presence checking


---------
20140617
---------

v0.0.22

joined status persistence
session restarts on allow

---------
20140617
---------

v0.0.21

fix requirements.txt issue


---------
20140617
---------

v0.0.20

Fixed reaping of stale event yards
Refactor RoadStack initiation method interfaces in preparation for later changes


---------
20140617
---------

v0.0.19

Fixed issues with Raet in Salt that made minion joining problematic


---------
20140616
---------

v0.0.18

Lots of cleanup refactoring of how session ids are managed. Now more correctly
handles stale sessions id checking and packet rejection.

---------
20140603
---------

v0.0.16

Added basedirpath to Stack creation to provide default way to guarantee that the
stackname is part of the Keep dirpath so that Keep files especially for LaneStack yards
are uniquely named

Some other refactoring.

---------
20140603
---------

v0.0.15

Added persistence to Lanes of Yard info. Add some unit tests
Had to make quite a few changes to accomodate this with naming of Yard persistence
files and directories since multiple LaneStacks on same host using same yard
So made stackname differentiator

Updated Salt to use this

Add support for libnacl to replace PyNaCl. Ported PyNaCl high level interface. At some
point will refactor to use simpler libnacl high level interface




---------
20140523
---------

v0.0.14

Raet now has basic support for persistence. This is through the Aliver and Alivent
transactions and inddicated by the state of RemoteEstate.alived attribute
RoadStack objects now have a .manage method that is responsible for kicking off
the RemoteEstate.manage method which starts alive transactions.

The result is to mark the .alived property as True if communication is successful
with the target of the transaction.


Updated unit tests


---------
20140516
---------

v0.0.13

Added "alive" transaction for keep alive preparatory to supporting presence
Aliver and Alivent objects
Refactored more rigorous normalized persistence of road data
joined and allowed status more conistent
Added some persistence fields
Refactoring in support of persistence

Updated unit tests


---------
20140505
---------

v0.0.12

Updated unit tests
Some bug fixes


---------
20140502
---------

v0.0.11

Basic unittest suite added
Some bug fixes



---------
20140428
---------

v0.0.10

Fixed some corner conditions on the acceptance handling in join transactions
Started added automated unit tests to replace the development tests



