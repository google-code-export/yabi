from yabibe.reactor import GeventReactor
GeventReactor.install()

import unittest2 as unittest
from mock import MagicMock, patch
import os
import tempfile
import StringIO
import json
import sys
import random
import gevent
import time

from config import TestConfig
                
from yabibe.connectors.fs import SSHFilesystem
from yabibe.exceptions import CredentialNotFound

from twisted.internet import reactor

def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

def make_conf(conf):
    output = []
    for key in conf:
        output.append('[%s]'%key)
        for subkey in conf[key]:
            output.append('%s: %s'%(subkey,conf[key][subkey]))
    return '\n'.join(output)+'\n'

class write_config(object):
    def __init__(self, conf):
        self.conf = conf
        
    def __enter__(self):
        self.tempfile = tempfile.NamedTemporaryFile().name
        with open(self.tempfile,'w') as fh:
            fh.write(make_conf(self.conf))
        
        return self.tempfile

    def __exit__(self, exc_type, exc_value, traceback):
        os.unlink(self.tempfile)
        

class SSHFilesystemTestSuite(unittest.TestCase):
    """Test SSHFilesystem"""
    testdir="/tmp/yabi-ssh-filesystem-unit-test"
    
    def setUp(self):
        if os.path.exists(self.testdir):
            os.system("sudo rm -rf '%s'"%self.testdir)
        os.makedirs(self.testdir)
        os.chmod(self.testdir,0777)
        self.sshfs = SSHFilesystem.SSHFilesystem()
    
    def tearDown(self):
        # for some reason our gevent reactor has some problems restarting. Thinks it's already started. So we just tell it its stopped here.
        # its up to each test to stop and start the reactor. This ensures clean deferred status on entry and exit
        reactor._started = False
            
    def test_construct(self):
        sshfs = SSHFilesystem.SSHFilesystem()

    def test_URI(self):
        self.assertEquals( self.sshfs.URI( "testuser", "testhost" ), "scp://testuser@testhost/" )
        self.assertEquals( self.sshfs.URI( "testuser", "testhost", 2200 ),  "scp://testuser@testhost:2200/" )
        self.assertEquals( self.sshfs.URI( "testuser", "testhost", 2200, "/some/path" ),  "scp://testuser@testhost:2200/some/path" )
        self.assertEquals( self.sshfs.URI( "testuser", "testhost", path="/some/path" ),  "scp://testuser@testhost/some/path" )
        self.assertEquals( self.sshfs.URI( "testuser", "testhost", path=None ),  "scp://testuser@testhost/" )

    def test_Creds(self):
        # pass in creds and make sure we get them back
        self.assertEquals( self.sshfs.Creds( 'yabiusername', {1:1,2:2}, None ), {1:1, 2:2} )

        with self.assertRaises( AssertionError ):
            self.sshfs.Creds(None,None,None)



    DUMMY_CERT =  {'user':'dummyuser',
                   'cert':'dummycert',
                   'key':'dummykey',
                   'username':'dummyusername',
                   'password':'dummypasssword'}
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/'}} )
    @patch('yabibe.utils.geventtools.GET', MagicMock( return_value= (200,
                                                                     "OK",
                                                                     json.dumps( DUMMY_CERT ))))
    def test_Creds_fetch(self):
        """test that when creds are asked for by username, they are fetched"""
        self.assertTrue( self.sshfs.Creds('yabiusername', None, "scp://user@remotehost/path/"), self.DUMMY_CERT )


    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/'}} )
    @patch('yabibe.utils.geventtools.GET', MagicMock( return_value= (404,
                                                                     "Not Found",
                                                                     "No Decrypted Credential Available" )))
    def test_Creds_fetch_non_existant_cred(self):
        """test that a 404 error raises a CredentialNotFound"""
        with self.assertRaises( CredentialNotFound ):
            self.sshfs.Creds('yabiusername', None, "scp://user@remotehost/path/"), self.DUMMY_CERT

    def run_reactor(self):
        self._run = True
        reactor.startRunning()
        while self._run:
            sys.stderr.write(".")
            reactor.runUntilCurrent()
            reactor.doIteration(1)
            gevent.sleep()



    USER_CERT =  {'user':os.environ.get("TESTUSER","dummyuser"),
                   'username':os.environ.get('USER','dummyusername'),
                   'password':os.environ.get('PASSWORD','dummypasssword')}

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_mkdir(self):
        """test mkdir on ssh filesystem"""
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()
                path = os.path.join(self.testdir,"directory")

                res = self.sshfs.mkdir("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                         'username':tc['username'],
                                                                         'password':tc['password'] } )
                
                # when mkdir succeeds its output is nothing
                self.assertFalse( res.strip() )

                # make sure the directory is there
                self.assertTrue( os.path.exists(path) )
                self.assertTrue( os.path.isdir(path) )

            finally:
                reactor.stop()
                
        thread = gevent.spawn(threadlet)
        reactor.run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_mkdir_permission_denied(self):
        """test mkdir on ssh filesystem that we don't have write permissions on"""
        # turn off world writable
        os.chmod( self.testdir, 0755)

        from yabibe.exceptions import PermissionDenied
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()
                path = os.path.join(self.testdir,"directory")

                with self.assertRaises( PermissionDenied ):
                    res = self.sshfs.mkdir("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                   'username':tc['username'],
                                                                                   'password':tc['password'] } )
                
            finally:
                reactor.stop()
                
        thread = gevent.spawn(threadlet)
        reactor.run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_mkdir_creates_all_parents(self):
        """test mkdir on ssh filesystem where the path to create in does not exist"""
        # turn off world writable
        path = os.path.join(self.testdir,"doesnotexist","full","path","to","directory")

        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                #with self.assertRaises( InvalidPath ):
                res = self.sshfs.mkdir("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                   'username':tc['username'],
                                                                                   'password':tc['password'] } )
                # when mkdir succeeds its output is nothing
                self.assertFalse( res.strip() )

                # make sure the directory is there
                self.assertTrue( os.path.exists(path) )
                self.assertTrue( os.path.isdir(path) )
                
            finally:
                reactor.stop()
                
        thread = gevent.spawn(threadlet)
        reactor.run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_file_with_no_recurse(self):
        """test a plain deletion of a file"""
        # turn off world writable
        path = os.path.join(self.testdir,"testfile.dat")
        with open(path, 'wb') as fh:
            for i in range(256):
                data = "".join( [ random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-=_+[]{}\\|;:'\",<.>/?`~")
                                  for X in range(256) ] )
                fh.write(data)
                
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is there
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.isfile(path))

                #with self.assertRaises( InvalidPath ):
                res = self.sshfs.rm("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                   'username':tc['username'],
                                                                                   'password':tc['password'] } )

                # when rm succeeds its output is nothing
                self.assertFalse( res.strip() )

                # make sure the file is gone
                self.assertFalse( os.path.exists(path) )
                
            finally:
                reactor.stop()
                
        thread = gevent.spawn(threadlet)
        reactor.run()

