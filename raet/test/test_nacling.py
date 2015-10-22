# -*- coding: utf-8 -*-
'''
Tests to try out nacling. Potentially ephemeral

'''
# pylint: skip-file
import sys
import inspect
import struct

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from ioflo.base.consoling import getConsole
console = getConsole()

from ioflo.aid.odicting import odict

# Import raet libs
from raet.abiding import *  # import globals
from raet import nacling

def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass


class BasicTestCase(unittest.TestCase):
    '''
    Test basic sign verify encrypt decrypt functions
    '''

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testSign(self):
        '''
        Test signature verification
        '''
        console.terse("{0}\n".format(self.testSign.__doc__))
        signerBob = nacling.Signer()
        console.terse("Bob Signer keyhex = {0}\n".format(signerBob.keyhex))
        self.assertEqual(len(signerBob.keyhex), 64)
        self.assertEqual(len(signerBob.keyraw), 32)
        console.terse("Bob Signer verhex = {0}\n".format(signerBob.verhex))
        self.assertEqual(len(signerBob.verhex), 64)
        self.assertEqual(len(signerBob.verraw), 32)

        # creating verifier from verhex
        verferPam = nacling.Verifier(signerBob.verhex)
        console.terse("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
        self.assertEqual(len(verferPam.keyhex), 64)
        self.assertEqual(len(verferPam.keyraw), 32)
        self.assertEqual(verferPam.keyhex, signerBob.verhex)

        msg = b"Hello This is Bob, how are you Pam?"
        signature = signerBob.signature(msg)
        console.terse("Signed by Bob: Msg len={0} '{1}' Sig Len={2}\n".format(
                 len(msg), msg, len(signature)))
        self.assertEqual(len(msg), 35)
        self.assertEqual(len(signature), 64)

        verified = verferPam.verify(signature, msg)
        self.assertTrue(verified)
        console.terse("Verified by Pam = {0}\n".format(verified))

        # creating verifier from verraw
        verferPam = nacling.Verifier(signerBob.verraw)
        console.terse("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
        self.assertEqual(len(verferPam.keyhex), 64)
        self.assertEqual(len(verferPam.keyraw), 32)
        self.assertEqual(verferPam.keyhex, signerBob.verhex)
        verified = verferPam.verify(signature, msg)
        self.assertTrue(verified)
        console.terse("Verified by Pam = {0}\n".format(verified))

        # creating verifier from key object
        verferPam = nacling.Verifier(verferPam.key)
        console.terse("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
        self.assertEqual(len(verferPam.keyhex), 64)
        self.assertEqual(len(verferPam.keyraw), 32)
        self.assertEqual(verferPam.keyhex, signerBob.verhex)
        verified = verferPam.verify(signature, msg)
        self.assertTrue(verified)
        console.terse("Verified by Pam = {0}\n".format(verified))

    def testEncrypt(self):
        '''
        Test encryption decryption with public private remote local key pairs
        '''
        console.terse("{0}\n".format(self.testEncrypt.__doc__))
        priverBob = nacling.Privateer()
        console.terse("Bob Local Key Pair\n")
        console.terse("Bob Privateer keyhex = {0}\n".format(priverBob.keyhex))
        console.terse("Bob Privateer pubhex = {0}\n".format(priverBob.pubhex))
        self.assertEqual(len(priverBob.keyhex), 64)
        self.assertEqual(len(priverBob.keyraw), 32)
        self.assertEqual(len(priverBob.pubhex), 64)
        self.assertEqual(len(priverBob.pubraw), 32)

        # create from pubhex
        pubberBob = nacling.Publican(priverBob.pubhex)
        console.terse("Bob remote public key\n")
        console.terse("Bob Publican keyhex = {0}\n".format(pubberBob.keyhex))
        self.assertEqual(len(pubberBob.keyhex), 64)
        self.assertEqual(len(pubberBob.keyraw), 32)
        self.assertEqual(pubberBob.keyhex, priverBob.pubhex)

        # create from pubraw
        pubberBob = nacling.Publican(priverBob.pubraw)
        #console.terse("Bob remote public key\n")
        #console.terse("Bob Publican keyhex = {0}\n".format(pubberBob.keyhex))
        self.assertEqual(len(pubberBob.keyhex), 64)
        self.assertEqual(len(pubberBob.keyraw), 32)
        self.assertEqual(pubberBob.keyhex, priverBob.pubhex)

        # create from key
        pubberBob = nacling.Publican(pubberBob.key)
        #console.terse("Bob remote public key\n")
        #console.terse("Bob Publican keyhex = {0}\n".format(pubberBob.keyhex))
        self.assertEqual(len(pubberBob.keyhex), 64)
        self.assertEqual(len(pubberBob.keyraw), 32)
        self.assertEqual(pubberBob.keyhex, priverBob.pubhex)

        priverPam = nacling.Privateer()
        console.terse("Pam Local Key Pair\n")
        console.terse("Pam Privateer keyhex = {0}\n".format(priverPam.keyhex))
        console.terse("Pam Privateer pubhex = {0}\n".format(priverPam.pubhex))
        self.assertEqual(len(priverPam.keyhex), 64)
        self.assertEqual(len(priverPam.keyraw), 32)
        self.assertEqual(len(priverPam.pubhex), 64)
        self.assertEqual(len(priverPam.pubraw), 32)

        #create from pubhex
        pubberPam = nacling.Publican(priverPam.pubhex)
        console.terse("Pam remote public key\n")
        console.terse("Pam Publican keyhex = {0}\n".format(pubberPam.keyhex))
        self.assertEqual(len(pubberPam.keyhex), 64)
        self.assertEqual(len(pubberPam.keyraw), 32)
        self.assertEqual(pubberPam.keyhex, priverPam.pubhex)

        # create from pubraw
        pubberPam = nacling.Publican(priverPam.pubraw)
        #console.terse("Pam remote public key\n")
        #console.terse("Pam Publican keyhex = {0}\n".format(pubberPam.keyhex))
        self.assertEqual(len(pubberPam.keyhex), 64)
        self.assertEqual(len(pubberPam.keyraw), 32)
        self.assertEqual(pubberPam.keyhex, priverPam.pubhex)

        # create from key
        pubberPam = nacling.Publican(pubberPam.key)
        #console.terse("Pam remote public key\n")
        #console.terse("Pam Publican keyhex = {0}\n".format(pubberPam.keyhex))
        self.assertEqual(len(pubberPam.keyhex), 64)
        self.assertEqual(len(pubberPam.keyraw), 32)
        self.assertEqual(pubberPam.keyhex, priverPam.pubhex)

        console.terse("Encrypted by Bob local private and Pam remote public key pair\n")
        enmsg = b"Hello its me Bob, Did you get my last message Pam?"
        console.terse("Msg len={0} '{1}'\n".format(len(enmsg), enmsg))
        self.assertEqual(len(enmsg), 50)

        # Pam remote public key, raw cipher nonce
        cipher, nonce = priverBob.encrypt(enmsg, pubberPam.key)
        console.terse("Cipher len={0} Nonce len={1}\n".format(len(cipher), len(nonce)))
        self.assertEqual(len(cipher), 66)
        self.assertEqual(len(nonce), 24)

        # Bob public key object
        console.terse("Decrypted by Pam local private and Bob remote public key pair\n")
        demsg = priverPam.decrypt(cipher, nonce, pubberBob.key)
        console.terse("Msg len={0} '{1}'\n".format(len(demsg), demsg))
        self.assertEqual(len(demsg), 50)
        self.assertEqual(demsg, enmsg)

        # Pam remote public key, hex cipher nonce
        cipher, nonce = priverBob.encrypt(enmsg, pubberPam.key, enhex=True)
        console.terse("Cipher len={0} '{1}'\nNonce len={2} '{3}'\n".format(
                len(cipher), cipher, len(nonce), nonce))
        self.assertEqual(len(cipher), 132)
        self.assertEqual(len(nonce), 48)

        # Bob public key object
        #console.terse("Decrypted by Pam local private and Bob remote public key pair\n")
        demsg = priverPam.decrypt(cipher, nonce, pubberBob.key, dehex=True)
        #console.terse("Msg len={0} '{1}'\n".format(len(demsg), demsg))
        self.assertEqual(len(demsg), 50)
        self.assertEqual(demsg, enmsg)

        # Pam remote public keyhex,
        cipher, nonce = priverBob.encrypt(enmsg, pubberPam.keyhex)
        #console.terse("Cipher len={0} '{1}'\nNonce len={2} '{3}'\n".format(
                 #len(cipher), cipher, len(nonce), nonce))
        self.assertEqual(len(cipher), 66)
        self.assertEqual(len(nonce), 24)

        # Bob public keyhex
        #console.terse("Decrypted by Pam local private and Bob remote public key pair\n")
        demsg = priverPam.decrypt(cipher, nonce, pubberBob.keyhex)
        #console.terse("Msg len={0} '{1}'\n".format(len(demsg), demsg))
        self.assertEqual(len(demsg), 50)
        self.assertEqual(demsg, enmsg)

        # Pam remote public keyraw,
        cipher, nonce = priverBob.encrypt(enmsg, pubberPam.keyraw)
        #console.terse("Cipher len={0} '{1}'\nNonce len={2} '{3}'\n".format(
                 #len(cipher), cipher, len(nonce), nonce))
        self.assertEqual(len(cipher), 66)
        self.assertEqual(len(nonce), 24)

        # Bob public keyraw
        #console.terse("Decrypted by Pam local private and Bob remote public key pair\n")
        demsg = priverPam.decrypt(cipher, nonce, pubberBob.keyraw)
        #console.terse("Msg len={0} '{1}'\n".format(len(demsg), demsg))
        self.assertEqual(len(demsg), 50)
        self.assertEqual(demsg, enmsg)

    def testUuid(self):
        '''
        Test uuid generation
        '''
        console.terse("{0}\n".format(self.testUuid.__doc__))
        uuid = nacling.uuid(16)
        self.assertEqual(len(uuid), 16)
        uuid = nacling.uuid(12)
        self.assertEqual(len(uuid), 16)
        uuid = nacling.uuid(20)
        self.assertEqual(len(uuid), 20)

        uuids = [nacling.uuid(16) for i in range(1024)]
        self.assertEqual(len(uuids), 1024)
        self.assertEqual(len(set(uuids)), len(uuids))

class PartTestCase(unittest.TestCase):
    """
    Test encrytion of handshake parts
    """

    def setUp(self):
        self.priverBob = nacling.Privateer()
        self.pubberBob = nacling.Publican(self.priverBob.pubhex)
        self.priverPam = nacling.Privateer()
        self.pubberPam = nacling.Publican(self.priverPam.pubhex)

    def tearDown(self):
        pass

    def testBlank(self):
        '''
        Blank message
        '''
        console.terse("{0}\n".format(self.testBlank.__doc__))
        enmsg = b"".rjust(64, b'\x00')
        console.terse("Msg len={0} '{1}'\n".format(len(enmsg), enmsg))
        cipher, nonce = self.priverBob.encrypt(enmsg, self.pubberPam.keyhex)
        console.terse("Cipher len={0} Nonce len={1}\n".format(len(cipher), len(nonce)))
        self.assertEqual(len(cipher), 80)
        self.assertEqual(len(nonce), 24)

    def testCookie(self):
        '''
        Cookie message parts
        '''
        console.terse("{0}\n".format(self.testCookie.__doc__))

        #part 1
        fmt = '!32sLL32s'
        msg = struct.pack(fmt, self.pubberPam.keyraw, 1, 2, self.pubberBob.keyraw)
        console.terse("Packed len={0}\n".format(len(msg)))
        self.assertEqual(len(msg), 72)
        cipher, nonce = self.priverBob.encrypt(msg, self.pubberPam.keyhex)
        console.terse("Cipher len={0} Nonce len={1}\n".format(len(cipher), len(nonce)))
        self.assertEqual(len(cipher), 88)
        self.assertEqual(len(nonce), 24)

        #part 2
        fmt = '!32sLL24s'
        cookie = self.priverBob.nonce()
        msg = struct.pack(fmt, self.pubberPam.keyraw, 1, 2, cookie)
        console.terse("Packed len={0}\n".format(len(msg)))
        self.assertEqual(len(msg), 64)
        cipher, nonce = self.priverBob.encrypt(msg, self.pubberPam.keyhex)
        console.terse("Cipher len={0} Nonce len={1}\n".format(len(cipher), len(nonce)))
        self.assertEqual(len(cipher), 80)
        self.assertEqual(len(nonce), 24)

    def testInitiate(self):
        '''
        Initiate message parts
        '''
        console.terse("{0}\n".format(self.testInitiate.__doc__))

        msg = self.priverBob.keyraw
        vcipher, vnonce = self.priverBob.encrypt(msg, self.pubberPam.key)
        console.terse("VCipher len={0} VNonce len={1}\n".format(len(vcipher), len(vnonce)))
        self.assertEqual(len(vcipher), 48)
        self.assertEqual(len(vnonce), 24)

        fqdn = b"10.0.2.30".ljust(128, b' ')
        fmt = '!32s48s24s128s'
        stuff = struct.pack(fmt, self.priverBob.keyraw, vcipher, vnonce, fqdn)
        console.terse("Stuff len={0} FQDN len={1} '{2}'\n\n".format(
                len(stuff), len(fqdn), fqdn))
        self.assertEqual(len(stuff), 232)
        cipher, nonce = self.priverBob.encrypt(stuff, self.pubberPam.keyhex)
        console.terse("Cipher len={0} Nonce len={1}\n".format(len(cipher), len(nonce)))
        self.assertEqual(len(cipher), 248)
        self.assertEqual(len(nonce), 24)

def runSome():
    """ Unittest runner """
    tests = []
    names = ['testSign',
             'testEncrypt'
             'testUuid', ]
    tests.extend(map(BasicTestCase, names))

    names = ['testBlank',
             'testInitiate', ]
    tests.extend(map(PartTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


def runAll():
    """ Unittest runner """
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(PartTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    runAll() #run all unittests

    #runSome()#only run some
