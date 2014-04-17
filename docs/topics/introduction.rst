============
Introduction
============

Currently RAET supports two types of communication.

- Host to host communication over UDP/IP sockets
- Same host interprocess communication over Unix Domain (UXD) Sockets

.. figure:: /images/RaetMetaphor.png
    :alt: RAET application archtecture diagram

    The archtecture of a RAET based application.

Details
=======

Production UDP/IP Ports for Raet
--------------------------------

Manor Estate 4505
Other Estates 4510

Packet Data Format
------------------

The data used to initialize a packet is an ordered dict with several fields
most of the fields are shared with the header data format below so only the
unique fields are shown here.

Unique Packet data fields
-------------------------

::

    sh: source host ip address (ipv4)
    sp: source ip port
    dh: destination host ip address (ipv4)
    dp: destination host ip port

Header Data Format
------------------

The .data in the packet header is an ordered dict  which is used to either
create a packet to transmit
or holds the field from a received packet.
What fields are included in a header is dependent on the header kind.

Header encoding
---------------

There are three header encoding formats currently supported.

- RAET Native. This is an minimized ascii test format that optimizes the
  tradeoff between easy readability and size. This is the default.

- JSON. This is the most verbose format but has the advantage of compatibility.

- Binary. This is not yet implemented. Once the protocol reaches a more mature
  state and its not likely that there will be any header changes (or very
  infrequent) then a binary format that minimizes size will be provided.

When the head kind is json = 0, then certain optimizations are used to minimize
the header length.

- The header field keys are two bytes long
- If a header field value is the default then the field is not included
- Lengths are encoded as hex strings
- The flags are encoded as a double char hex string in field 'fg'


Header Data Fields
------------------

::

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


Body Data Format
----------------

The Body .data is a Mapping that is serialized using either JSON or MSGPACK

Packet Parts
------------

Each packet has 4 parts some of which may be empty. These are:

- Head
- Body
- Coat
- Tail

The Head is manditory and provides the header fields that are needed to process
the packet.

The Tail provides the authentication signature that is used to verify the
source of the packet and that its contents have not been tampered with.

The Body is the contents of the packet. Some packets such as Acks and Nacks
don't need a body. The Body is a serialized Python dictionary typically and
ordered dictionary so that parsing and debugging has a consistent view of the
ordering of the fields in the body.

The Coat is the encrypted version of the body. The encryption type is CurveCP
based. If the Coat is provided then the Body is encapsulated within the Coat
Part.



Header Details
--------------

JSON Encoding
`````````````

Header is the ASCII Safe JSON encoding of a Python ordered dictionary. Header
termination is an empty line given by double pair of carriage-return linefeed
characters::

    /r/n/r/n
    10 13 10 13
    ADAD
    1010 1101 1010 1101

Carriage-return and newline characters cannot appear in a JSON encoded string
unless they are escaped with backslash, so the 4 byte combination is illegal in
valid JSON that does not have multi-byte unicode characters so it makes it a
uniquely identifiable header termination.

These means the header must be ascii safe  so no multibyte utf-8 strings are
allowed in the header.

Native Encoding
```````````````

The header consists of newline delimited lines. Each header line consists of a
two character field identifier followed by a space followed by the value of the
field as ascii hex encoded binary followed by newline. The Header end is
indicated by a blank line, that is, a double newline character. Example

Binary Encoding
```````````````

The header consists of defined set of fixed length fields


Session
```````

Session is important for security. Want one session opened and then multiple
transactions within session::

    Session ID
    SID
    sid
    si


Session Bootstrap
-----------------



Layering
--------

OSI Layers

==  ==
7:  Application: Format: Data (Stack to Application interface buffering etc)
6:  Presentation: Format: Data (Encrypt-Decrypt convert to machine independent format)
5:  Session: Format: Data (Interhost communications. Authentication. Groups)
4:  Transport: Format: Segments (Reliable delivery of Message, Transactions, Segmentation, Error checking)
3:  Network: Format: Packets/Datagrams (Addressing Routing)
2:  Link: Format: Frames ( Reliable per frame communications connection, Media access controller )
1:  Physical: Bits (Transciever communication connection not reliable)
==  ==

- Link is hidden from Raet

- Network is IP host address and UDP Port

- Transport is Raet transaction and packet authentication vis tail signature
  that provide reliable transport.

- Session is session id key exchange for signing. Grouping is Road

- Presentation is Encrypt-Decrypt Body and Serialize-Deserialize Body

- Application is Body data dictionary

Packet signing could technically be in either the Transport or Session layers.
