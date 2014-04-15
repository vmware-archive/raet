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

The archtecture of a RAET based application is shown in the figure below:

![Diagram 1](docs/images/RaetMetaphor.png?raw=true)


## Details

### Production UDP/IP Ports for Raet

Manor Estate 4505
Other Estates 4510

### Packet Data Format

The data used to initialize a packet is an ordered dict with several fields
most of the fields are shared with the header data format below so only the
unique fields are shown here.

### Unique Packet data fields

    sh: source host ip address (ipv4)
    sp: source ip port
    dh: destination host ip address (ipv4)
    dp: destination host ip port

### Header Data Format.
The .data in the packet header is an ordered dict  which is used to either
create a packet to transmit
or holds the field from a received packet.
What fields are included in a header is dependent on the header kind.

### Header encoding

There are three header encoding formats currently supported.

- RAET Native. This is an minimized ascii test format that optimizes the tradeoff between
easy readability and size. This is the default.

- JSON. This is the most verbose format but has the advantage of compatibility.

- Binary. This is not yet implemented. Once the protocol reaches a more mature state
and its not likely that there will be any header changes (or very infrequent) then
a binary format that minimizes size will be provided.

When the head kind is json = 0, then certain optimizations are used to minimize
the header length.
- The header field keys are two bytes long
- If a header field value is the default then the field is not included
- Lengths are encoded as hex strings
- The flags are encoded as a double char hex string in field 'fg'


### Header Data Fields

    ri: raet id Default 'RAET'
    vn: Version (Version) Default 0
    pk: Packet Kind (PcktKind)
    pl: Packet Length (PcktLen)
    hk: Header kind   (HeadKind) Default 0
    hl: Header length (HeadLen) Default 0

    se: Source Estate ID (SEID)
    de: Destination Estate ID (DEID)
    cf: Correspondent Flag (CrdtFlag) Default 0
    bf: BroadCast Flag (BcstFlag)  Default 0

    si: Session ID (SID) Default 0
    ti: Transaction ID (TID) Default 0
    tk: Transaction Kind (TrnsKind)

    dt: Datetime Stamp  (Datetime) Default 0
    oi: Order index (OrdrIndx)   Default 0

    wf: Waiting Ack Flag    (WaitFlag) Default 0
        Next segment or ordered packet is waiting for ack to this packet
    ml: Message Length (MsgLen)  Default 0
        Length of message only (unsegmented)
    sn: Segment Number (SgmtNum) Default 0
    sc: Segment Count  (SgmtCnt) Default 1
    sf: Segment Flag  (SgmtFlag) Default 0
        This packet is part of a segmented message
    af: All Flag (AllFlag) Default 0
        Resend all segments not just one

    bk: Body kind   (BodyKind) Default 0
    ck: Coat kind   (CoatKind) Default 0
    fk: Footer kind   (FootKind) Default 0
    fl: Footer length (FootLen) Default 0

    fg: flags  packed (Flags) Default '00' hs
         2 char Hex string with bits (0, 0, af, sf, 0, wf, bf, cf)
         Zeros are TBD flags


### Body Data Format

The Body .data is a Mapping that is serialized using either JSON or MSGPACK

### Packet Parts

Each packet has 4 parts some of which may be empty. These are:
- Head
- Body
- Coat
- Tail

The Head is manditory and provides the header fields that are needed to process the
packet.

The Tail provides the authentication signature that is used to verify the source of
the packet and that its contents have not been tampered with.

The Body is the contents of the packet. Some packets such as Acks and Nacks don't
need a body. The Body is a serialized Python dictionary typically and ordered dictionary
so that parsing and debugging has a consistent view of the ordering of the fields
in the body.

The Coat is the encrypted version of the body. The encryption type is CurveCP based.
If the Coat is provided then the Body is encapsulated within the Coat Part.



### Header Details

#### JSON Encoding

Header is the ASCII Safe JSON encoding of a Python ordered dictionary.
Header termination is an empty line given by double pair of carriage-return linefeed
characters.

/r/n/r/n
10 13 10 13
ADAD
1010 1101 1010 1101

Carriage-return and newline characters cannot appear in a JSON encoded
string unless they are escaped with backslash, so the 4 byte combination is illegal
in valid JSON that does not have multi-byte unicode characters so it makes it a
uniquely identifiable header termination.

These means the header must be ascii safe  so no multibyte utf-8 strings are
allowed in the header.

#### Native Encoding

The header consists of newline delimited lines. Each header line consists
of a two character field identifier followed by a space followed by the value
of the field as ascii hex encoded binary followed by newline.
The Header end is indicated by a blank line, that is, a double newline character.
Example

#### Binary Encoding

The header consists of defined set of fixed length fields


### Session

Session is important for security. Want one session opened and then multiple
transactions within session.

Session ID
SID
sid
si


### Session Bootstrap



### Layering:

OSI Layers

7: Application: Format: Data (Stack to Application interface buffering etc)
6: Presentation: Format: Data (Encrypt-Decrypt convert to machine independent format)
5: Session: Format: Data (Interhost communications. Authentication. Groups)
4: Transport: Format: Segments (Reliable delivery of Message, Transactions, Segmentation, Error checking)
3: Network: Format: Packets/Datagrams (Addressing Routing)
2: Link: Format: Frames ( Reliable per frame communications connection, Media access controller )
1: Physical: Bits (Transciever communication connection not reliable)

- Link is hidden from Raet

- Network is IP host address and UDP Port

- Transport is Raet transaction and packet authentication vis tail signature that
   provide reliable transport.

- Session is session id key exchange for signing. Grouping is Road

- Presentation is Encrypt-Decrypt Body and Serialize-Deserialize Body

- Application is Body data dictionary

Packet signing could technically be in either the Transport or Session layers.
