# -*- coding: utf-8 -*-
'''
raeting module provides constants and values for the RAET protocol

Production Ports for Raet
Master 4505
Minion(s) 4510

Packet Data Format.
The data used to initialize a packet is an ordered dict with several fields
most of the fields are shared with the header data format below so only the
unique fields are shown here.

Unique Packet data fields

    sh: source host ip address (ipv4) Default: ''
    sp: source ip port                Default: 7532
    dh: destination host ip address (ipv4) Default: '127.0.0.1'
    dp: destination host ip port           Default 7532

Header Data Format.
The .data in the packet header is an ordered dict  which is used to either
create a packet to transmit
or holds the field from a received packet.
What fields are included in a header is dependent on the header kind.

Header encoding.
    When the head kind is json = 0, then certain optimizations are
    used to minimize the header length.
        The header field keys are two bytes long
        If a header field value is the default then the field is not included
        Lengths are encoded as hex strings
        The flags are encoded as a double char hex string in field 'fg'

header data =
{
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
    nf: NAT Flag (NatFlag) Default 0
    df: Dynamic IP Flag (DynFlag) Default 0
    vf: IPv6 Flag (IP) (Ipv6Flag) Default 0

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
    af: Again Flag (AgnFlag) Default 0
        This segment is being sent again

    bk: Body kind   (BodyKind) Default 0
    ck: Coat kind   (CoatKind) Default 0
    fk: Footer kind   (FootKind) Default 0
    fl: Footer length (FootLen) Default 0

    fg: flags  packed (Flags) Default '00' hs
         2 char Hex string with bits (vf, df, nf, af, sf, wf, bf, cf)
         Zeros are TBD flags
}

Body Data Format
The Body .data is a Mapping

Body Encoding
    When the body kind is json = 0, then the .data is json encoded

Body Decoding


'''

# pylint: disable=C0103

# Import python libs
import struct
import enum

# Import ioflo libs
from ioflo.aid.odicting import odict

# Import raet libs
# pylint: disable=wildcard-import,unused-wildcard-import,redefined-builtin
from .abiding import *  # import globals
# pylint: enable=wildcard-import,unused-wildcard-import,redefined-builtin

# Used to comput session id wrap around where valid sid is >= modulo N given by
# (((new - old) % 0x100000000) < (0x100000000 // 2))
# N//2 = 0x80000000
SID_WRAP_MODULO = 0x100000000  # session id wraps modulo N = 2^32 = 0x100000000
SID_WRAP_DELTA = 0x80000000    # session id >= delta at N//2 = 0x80000000
SID_ROLLOVER = 0xffffffff      # session id rolls over at modulo (N-1) -= 2^32 -1 = 0xffffffff

RAET_PORT = 7530
RAET_TEST_PORT = 7531
DEFAULT_SRC_HOST = ''
DEFAULT_DST_HOST = '127.0.0.1'

UDP_MAX_DATAGRAM_SIZE = (2 ** 16) - 1  # 65535
UDP_MAX_SAFE_PAYLOAD = 548  # IPV4 MTU 576 - udp headers 28
# IPV6 MTU is 1280 but headers are bigger
UDP_MAX_PACKET_SIZE = min(1024, UDP_MAX_DATAGRAM_SIZE)  # assumes IPV6 capable equipment
UXD_MAX_PACKET_SIZE = (2 ** 16) - 1  # 65535
MAX_SEGMENT_COUNT = (2 ** 16) - 1  # 65535
MAX_MESSAGE_SIZE = min(67107840, UDP_MAX_PACKET_SIZE * MAX_SEGMENT_COUNT)
MAX_HEAD_SIZE = 255

JSON_END = b'\r\n\r\n'
HEAD_END = b'\n\n'

VERSIONS = odict([('0.1', 0)])
VERSION_NAMES = odict((v, k) for k, v in VERSIONS.iteritems())
VERSION = VERSIONS.values()[0]

HELLO_PACKER = struct.Struct('!64s32s80s24s')  # curvecp allow trans bodies
COOKIESTUFF_PACKER = struct.Struct('!32sLL24s')
COOKIE_PACKER = struct.Struct('!80s24s')
INITIATESTUFF_PACKER = struct.Struct('!32s48s24s128s')
INITIATE_PACKER = struct.Struct('!32s24s248s24s')


def get_exception_error(ex):
    '''
    Return the error code from an exception
    '''
    if hasattr(ex, 'errno'):
        return ex.errno
    elif hasattr(ex, 'winerror'):
        return ex.winerror
    else:
        emsg = "Cannot find error code in exception: {0}".format(ex)
        raise TypeError(emsg)


@enum.unique
class HeadKind(enum.IntEnum):
    '''
    Integer Enums of Head Kinds
    '''
    raet = 0
    json = 1
    binary = 2
    unknown = 255


@enum.unique
class BodyKind(enum.IntEnum):
    '''
    Integer Enums of Body Kinds
    '''
    nada = 0
    json = 1
    raw = 2
    msgpack = 3
    unknown = 255


@enum.unique
class FootKind(enum.IntEnum):
    '''
    Integer Enums of Foot Kinds
    '''
    nada = 0
    nacl = 1
    sha2 = 2
    crc64 = 3
    unknown = 255


class FootSize(enum.IntEnum):
    '''
    Integer Enums of Foot Sizes in bytes
    '''
    nada = 0
    nacl = 64
    sha2 = 256
    crc64 = 8
    unknown = 0


@enum.unique
class CoatKind(enum.IntEnum):
    '''
    Integer Enums of Coat Kinds
    '''
    nada = 0
    nacl = 1
    crc16 = 2
    crc64 = 3
    unknown = 255


class TailSize(enum.IntEnum):
    '''
    Integer Enums of Tail Sizes in bytes
    '''
    nada = 0
    nacl = 24
    crc16 = 2
    crc64 = 8
    unknown = 0


@enum.unique
class TrnsKind(enum.IntEnum):
    '''
    Integer Enums of Transaction Kinds
    '''
    message = 0
    join = 1
    bind = 2
    allow = 3
    alive = 4
    unknown = 255


@enum.unique
class PcktKind(enum.IntEnum):
    '''
    Integer Enums of Packet Kinds
    '''
    message = 0
    ack = 1
    nack = 2
    resend = 3
    request = 4
    response = 5
    hello = 6
    cookie = 7
    initiate = 8
    unjoined = 9
    unallowed = 10
    renew = 11
    refuse = 12
    reject = 13
    pend = 14
    done = 15
    unknown = 255


@enum.unique
class Acceptance(enum.IntEnum):
    '''
    Integer Enums of Acceptances
    '''
    pending = 0
    accepted = 1
    rejected = 2


@enum.unique
class AutoMode(enum.IntEnum):
    '''
    Integer Enums of Auto Modes
    '''
    never = 0
    once = 1
    always = 2


@enum.unique
class PackKind(enum.IntEnum):
    '''
    Integer Enums of Pack Kinds for Lane Pages
    '''
    json = 0
    pack = 1


# head fields that may be included in packet header if not default value
PACKET_DEFAULTS = odict([
                            ('sh', DEFAULT_SRC_HOST),
                            ('sp', RAET_PORT),
                            ('dh', DEFAULT_DST_HOST),
                            ('dp', RAET_PORT),
                            ('ri', 'RAET'),
                            ('vn', 0),
                            ('pk', 0),
                            ('pl', 0),
                            ('hk', 0),
                            ('hl', 0),
                            ('se', 0),
                            ('de', 0),
                            ('cf', False),
                            ('bf', False),
                            ('nf', False),
                            ('df', False),
                            ('vf', False),
                            ('si', 0),
                            ('ti', 0),
                            ('tk', 0),
                            ('dt', 0),
                            ('oi', 0),
                            ('wf', False),
                            ('sn', 0),
                            ('sc', 1),
                            ('ml', 0),
                            ('sf', False),
                            ('af', False),
                            ('bk', 0),
                            ('ck', 0),
                            ('fk', 0),
                            ('fl', 0),
                            ('fg', '00'),
                      ])

PACKET_FIELDS = ['sh', 'sp', 'dh', 'dp',
                 'ri', 'vn', 'pk', 'pl', 'hk', 'hl',
                 'se', 'de', 'cf', 'bf', 'nf', 'df', 'vf', 'si', 'ti', 'tk',
                 'dt', 'oi', 'wf', 'sn', 'sc', 'ml', 'sf', 'af',
                 'bk', 'ck', 'fk', 'fl', 'fg']

PACKET_HEAD_FIELDS = ['ri', 'vn', 'pk', 'pl', 'hk', 'hl',
               'se', 'de', 'cf', 'bf', 'nf', 'df', 'vf', 'si', 'ti', 'tk',
               'dt', 'oi', 'wf', 'sn', 'sc', 'ml', 'sf', 'af',
               'bk', 'bl', 'ck', 'cl', 'fk', 'fl', 'fg']

PACKET_FLAGS = ['vf', 'df', 'nf', 'af', 'sf', 'wf', 'bf', 'cf']
PACKET_FLAG_FIELDS = ['vf', 'df', 'nf', 'af', 'sf', 'wf', 'bf', 'cf']

PACKET_FIELD_FORMATS = odict([
                    ('ri', '.4s'),
                    ('vn', 'x'),
                    ('pk', 'x'),
                    ('pl', '04x'),
                    ('hk', 'x'),
                    ('hl', '02x'),
                    ('se', 'x'),
                    ('de', 'x'),
                    ('cf', ''),
                    ('bf', ''),
                    ('nf', ''),
                    ('df', ''),
                    ('vf', ''),
                    ('si', 'x'),
                    ('ti', 'x'),
                    ('tk', 'x'),
                    ('dt', 'f'),
                    ('oi', 'x'),
                    ('wf', ''),
                    ('sn', 'x'),
                    ('sc', 'x'),
                    ('ml', 'x'),
                    ('sf', ''),
                    ('af', ''),
                    ('bk', 'x'),
                    ('ck', 'x'),
                    ('fk', 'x'),
                    ('fl', 'x'),
                    ('fg', '.2s'),
              ])

# head fields that may be included in page header if not default value
PAGE_DEFAULTS = odict([
                        ('ri', 'RAET'),
                        ('vn', 0),
                        ('pk', 0),
                        ('sn', ''),
                        ('dn', ''),
                        ('si', '000000000000000000'),
                        ('bi', 0),
                        ('pn', 0),
                        ('pc', 1),
                      ])

PAGE_FIELD_FORMATS = odict([
                            ('ri', '.4s'),
                            ('vn', 'x'),
                            ('pk', 'x'),
                            ('sn', 's'),
                            ('dn', 's'),
                            ('si', '.18s'),
                            ('bi', 'x'),
                            ('pn', '04x'),
                            ('pc', '04x'),
                           ])

PAGE_FIELDS = ['ri', 'vn', 'pk', 'sn', 'dn', 'si', 'bi', 'pn', 'pc']


class RaetError(Exception):
    '''
    Exceptions in RAET Protocol processing

       usage:
           emsg = "Invalid unique id '{0}'".format(uid)
           raise raeting.RaetError(emsg)
    '''
    def __init__(self, message=None):
        self.message = message  # description of error
        super(RaetError, self).__init__(message)

    def __str__(self):
        return "{0}: {1}.\n".format(self.__class__.__name__, self.message)


class StackError(RaetError):
    '''
       Exceptions in RAET stack processing

       Usage:
            emsg = "Invalid unique id '{0}'".format(uid)
            raise raeting.StackError(emsg)
    '''
    pass


class EstateError(RaetError):
    '''
       Exceptions in RAET estate processing

       Usage:
            emsg = "Invalid unique id '{0}'".format(uid)
            raise raeting.EstateError(emsg)
    '''
    pass


class TransactionError(RaetError):
    '''
       Exceptions in RAET transaction processing

       Usage:
            emsg = "Invalid uniqu id '{0}'".format(uid)
            raise raeting.TransactionError(emsg)
    '''
    pass


class PacketError(RaetError):
    '''
       Exceptions in RAET packet processing

       Usage:
            emsg = "Invalid unique id '{0}'".format(uid)
            raise raeting.PacketError(emsg)
    '''
    pass


class PacketSizeError(PacketError):
    '''
       Packet too large error needs to be segmented

       Usage:
            emsg = "Packet size {0} too large needs to be segmented".format(size)
            raise raeting.PacketSizeError(emsg)
    '''
    pass


class KeepError(RaetError):
    '''
       Exceptions in RAET keep processing

       Usage:
            emsg = "Invalid unique id '{0}'".format(uid)
            raise raeting.KeepError(emsg)
    '''
    pass


class YardError(RaetError):
    '''
       Exceptions in RAET yard processing

       Usage:
            emsg = "Invalid unique id '{0}'".format(uid)
            raise raeting.YardError(emsg)
    '''
    pass


class PageError(RaetError):
    '''
       Exceptions in RAET page processing

       Usage:
            emsg = "Invalid page kind '{0}'".format(kind)
            raise raeting.PageError(emsg)
    '''
    pass
