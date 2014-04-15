# RAET (Reliable Asynchronous Event Transport) Protocol

## Motivation

Modern large scale distributed application architectures where components are
distributed across the internet on multiple hosts and multiple CPU cores are often
based on a messaging or event bus that allows the various distributed components
to communicate asynchronously with each other. Typically the messaging bus is
some form of messaging queue service such as AMQP or ZeroMQ. The message bus supports
what is commonly referred to as a publish/subscribe methodology for information
exchange.

While there are many advantages to a full featured message queuing service,
one of the disadvantagesis the inability to manage performance at scale.

A message queuing service performs two distinct but complementary functions.

- The first is asynchronous transport of messages over the internet.
- The second is message queue management, that is, the identification, tracking,
storage, and distribution of messages between publishers and subscribers via queues.

One of the advantages of a message queuing service for many applications is that
the service hides the complexities of queue management from the clients
behind an API. The disadvantage is that at scale where the volume of messages, the
timing of messages, and the associated demands on  memory, network, and cpu capacity
become critical, the client has little ability to tune the service for performance.
Often MQ services become bottlenecks for the distributed application.
The more complicated MQ services like AMQP tend to be unreliable under load.

Separating the asynchrounous event over network transport function from the message
queue management allows independant tuning at scale of each function.

Moreover, most if not all of the MQ services that we are familiar with are based on TCP/IP
which due to the way it handles connection setup and teardown as well as failed
connections in order to support streams tends to add high latency to the
network communications and is not therefore not well suited for the asynchronous nature
of distibuted event driven application communications.

Because UDP/IP has lower latency and is connectionless, it scales better, but it
has the serious drawback that it is not reliable. What it needed is a tuned transport
protocol adds reliability to UDP/IP without sacrificing latency and scalability.
A transactioned protocol, is much more appropriate for providing reliablity to
asynchronous event transport than a streaming protocol.

In addition, because most MQ services are based on TCP/IP they tend to also use
HTTP and therefore TLS/SSL for secure communications. While using HTTP provides
easy integration with web based systems, it is problematic for high performant systems
and TLS is also problematic as a security system both from performance and vulnerabilty
aspects. Elliptic Curve Cryptography provides increases in security
with lower performance requires over other approaches. LibSodium provides an open
source Elliptic Curve Cryptographic library with support for both authentication
and encryption. The CurveCP protocol is based on LibSodium and provides a handshake
protocol for bootstrapping secure network exchanges of information.

Finally, one of the best ways to manage and fine tune processor resources
(cpu, memory, network) in distrubted concurrent event driven applications is to use
something called micro-threads. A microthread is typically and in-language feature
that allows logical concurrency with no more overhead than a function call.
Micro threading uses cooperative multi-tasking instead of threads and/or processes
and avoids many of the complexities of resource contention, context switching,
and interprocess communications while providing much higher total performance.

The main limitation of a micro-threaded application is that it is constrained to
one CPU core because it runs in one process. To enable full utilization of all CPU
cores, the application needs to be able to run at least one process per CPU core.
This requires on host inter-process communications. But instead of one process per
logical concurrent function which is the conventional approach to multi-processing,
A micro-threaded multi-process application has one micro-thread per logical concurrent
function and the total number of micro-threads is distributed amoungst the minimum
number of processes, no more than the number of cpu cores. This optimizes the use
of the cpu power while minimizes the overhead of process context switching.

An example of a framework that uses this type of micro-threaded but multi-process
architecture is Erlang. Indeed, Erlang provided confirmation that the approach to
RAET could be viable. Unfortunately, the Erlang ecosystem is somewhat limited
and the language itself uses what one might describe as a very unfortunate syntax.
Since we have extensive background in Python we wanted to leverage the richness of
the Python ecosystem but still be able to develop distributed applications on a
micro-threaded multi-process capable framework.


RAET is designed to provide secure reliable scalable asynchronous message/event
transport over the internet in a micro-threaded multi-process application framework
that uses UDP for interhost communication and LibSodium for authentication, encryption
and the CurveCP handshake for secure bootstrap.

The queue management and micro-threaded application support is provided by Ioflo.
RAET is a complementary project to Ioflo in that RAET enables multiple Ioflo
applications to work together over a network as part of a distributed application.

The primary use case and motivating problem that resulted in the development of RAET
was the need to enable SaltStack to scale better. SaltStack is a remote execution
and configuration management platform written in Python. SaltStack uses ZeroMQ (0MQ)
as is message bug or message queuing service. ZeroMQ is based on


## Installation

Current raet is provided as a PyPi package. To install on a unix based system
use pip.

``` bash

$ pip install raet


```

on OS X

``` bash
$ sudo pip install raet

```



## Introduction

Currently RAET supports to types of communication.

- Host to host communication over UDP/IP sockets
- Same host interprocess communication over Unix Domain (UXD) Sockets

The archtectures of a RAET based application is shown in the figure below:

![Diagram 1](docs/images/RaetMetaphor.png?raw=true)






























Layering:

OSI Layers

7: Application: Format: Data (Stack to Application interface buffering etc)
6: Presentation: Format: Data (Encrypt-Decrypt convert to machine independent format)
5: Session: Format: Data (Interhost communications. Authentication. Groups)
4: Transport: Format: Segments (Reliable delivery of Message, Transactions, Segmentation, Error checking)
3: Network: Format: Packets/Datagrams (Addressing Routing)
2: Link: Format: Frames ( Reliable per frame communications connection, Media access controller )
1: Physical: Bits (Transciever communication connection not reliable)

Link is hidden from Raet
Network is IP host address and Udp Port
Transport is Raet transactions, service kind, tail error checking,
    Could include header signing as part of transport reliable delivery
    serialization of header
Session is session id key exchange for signing. Grouping is Road (like 852 channel)
Presentation is Encrpt Decript body Serialize Deserialize Body
Application is body data dictionary

Header signing spans both the Transport and Session layers.

Header
----------

JSON Header (Tradeoff some processing speed for extensibility, ease of use, readability)

Body initially JSON but support for "packed" binary body


Packet
------

Header ASCII Safe JSON
Header termination:
Empty line given by double pair of carriage return linefeed
/r/n/r/n
10 13 10 13
ADAD
1010 1101 1010 1101

In json carriage return and newline characters cannot appear in a json encoded
string unless they are escaped with backslash, so the 4 byte combination is illegal in valid
json that does not have multi-byte unicode characters.

These means the header must be ascii safe  so no multibyte utf-8 strings
allowed in header.

Following Header Terminator is variable length signature block. This is binary
and the length is provided in the header.

Following the signature block is the packet body or data.
This may either be JSON or packed binary.
The format is given in the json header

Finally is an optional tail block for error checking or encryption details


Header Fields
-------------

In UDP header

sh = source host
sp = source port
dh = destination host
dp = destination port


In RAET Header

hk = header kind
hl = header length

vn = version number

sd = Source Device ID
dd = Destination Device ID
cf = Corresponder Flag
mf = Multicast Flag

si = Session ID
ti = Transaction ID

sk = Service Kind
pk = Packet Kind
bf = Burst Flag  (Send all Segments or Ordered packets without interleaved acks)

oi = Order Index
dt = DateTime Stamp

sn = Segment Number
sc = Segment Count

pf = Pending Segment Flag
af = All Flag   (Resent all Segments not just one)

nk = Auth header kind
nl = Auth header length

bk = body kind
bl = body length

tk = tail kind
tl = tail length

fg = flags  packed (Flags) Default '00' hex string
                 2 byte Hex string with bits (0, 0, af, pf, 0, bf, mf, cf)
                 Zeros are TBD flags


Session Bootstrap
-----------------

Minion sends packet with SID of Zero with public key of minions Public Private Key pair
Master acks packet with SID of Zero to let minion know it received the request

Some time later Master sends packet with SID of zero that accepts the Minion

Minion


Session
-----------
Session is important for security. Want one session opened and then multiple
transactions within session.

Session ID
SID
sid

GUID hash to guarantee uniqueness since no guarantee of nonvolitile storage
or require file storage to keep last session ID used.

Service Types or Modular Services
---------------------------------
Four Service Types

A) One or more maybe (unacknowledged repeat) maybe means no guarantee

B) Exactly one at most  (ack with retries) (duplicate detection idempotent)
        at most means fixed number of retries has finite probability of failing
        B1) finite retries
        B2) infinite retries with exponential back-off up to a maximum delay

C) Exactly one of sequence at most (sequence numbered)
        Receiver requests retry of missing packet with same B1 or B2 retry type

D) End to End (Application layer Request Response)
      This is two B sub transactions

Initially unicast messaging
Eventually support for Multicast

The use case for C) is to fragment large packets as once a UDP packet
exceeds the frame size its reliability goes way down
So its more reliable to fragment large packets.


Better approach might be to have more modularity.
Services Levels

1) Maybe one or more
    A) Fire and forget
        no transaction either side
    B) Repeat, no ack, no dupdet
        repeat counter send side,
        no transaction on receive side
    C) Repeat, no Ack, dupdet
        repeat counter send side,
        dup detection transaction receive side
2) More or Less Once
   A) retry finite, ack no dupdet
      retry timer send side, finite number of retires
      ack receive side no dupdet

3) At most Once
   A) retry finite, ack, dupdet
      retry timer send side, finite number of retires
      ack receive side dupdet

4) Exactly once
   A) ack retry
      retry timer send side,
      ack and duplicate detection receive side
      Infinite retries with exponential backoff

4) Sequential sequence number
   A) reorder escrow
   B) Segmented packets

5) request response to application layer


Service Features

1) repeats
2) ack retry transaction id
3) sequence number duplicate detection  out of order detection sequencing
5) rep-req

Always include transaction id since multiple transactions on same port
So get duplicate detection for free if keep transaction alive but if use


A) Maybe one or more
B1) At Least One
B2) Exactly One
C) One of sequence
D) End to End

A) Sender creates transaction id for number of repeats but reciever does not
keep transaction alive

B1) Sender creates transaction id  keeps it for retries.
Receiver keeps it to send ack then kills so retry could be duplicate not detected

B2) Sender creates transaction id keeps for retries
Receiver keeps tid for acks on any retires so no duplicates.

C) Sender creates TID and Sequence Number.
Receiver checks for out of order sequence and can request retry.

D) Application layer sends response. So question is do we keep transaction open
or have response be new transaction. No because then we need a rep-req ID so
might as well use the same transaction id. Just keep alive until get response.

Little advantage to B1 vs B2 not having duplicates.

So 4 service types

A) Maybe one or more (unacknowledged repeat)

B) Exactly One (At most one)  (ack with retry) (duplicate detection idempotent)

C) One of Sequence (sequence numbered)

D) End to End


Also multicast or unicast


Modular Transaction Table

Sender Side:
   Transaction ID plus transaction source sender or receiver generated transaction id
   Repeat Counter
   Retry Timer Retry Counter (finite retries)
   Redo Timer (infinite redos with exponential backoff)
   Sequence number without acks (look for resend requests)
   Sequence with ack (wait for ack before sending next in sequence)
   Segmentation

Receiver Side:
   Nothing just accept packet
   Acknowledge (can delete transaction after acknowledge)
   No duplicate detection
   Transaction timeout (keep transaction until timeout)
   Duplicate detection save transaction id duplicate detection timeout
   Request resend of missing packet in sequence
   Sequence reordering with escrow timeout wait escrow before requesting resend
   Unsegmentation (request resends of missing segment)




