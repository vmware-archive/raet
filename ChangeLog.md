------------------
CHANGE LOG
-------------------

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



