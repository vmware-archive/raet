------------------
CHANGE LOG
-------------------

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



