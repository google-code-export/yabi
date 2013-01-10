import unittest2 as unittest
from mock import MagicMock, patch
import os
import tempfile
import StringIO
import json

from yabibe.connectors.fs import SSHFilesystem
from yabibe.exceptions import NoSuchCredential

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
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def test_construct(self):
        sshfs = SSHFilesystem.SSHFilesystem()

    def test_URI(self):
        sshfs = SSHFilesystem.SSHFilesystem()
        self.assertEquals( sshfs.URI( "testuser", "testhost" ), "scp://testuser@testhost/" )
        self.assertEquals( sshfs.URI( "testuser", "testhost", 2200 ),  "scp://testuser@testhost:2200/" )
        self.assertEquals( sshfs.URI( "testuser", "testhost", 2200, "/some/path" ),  "scp://testuser@testhost:2200/some/path" )
        self.assertEquals( sshfs.URI( "testuser", "testhost", path="/some/path" ),  "scp://testuser@testhost/some/path" )
        self.assertEquals( sshfs.URI( "testuser", "testhost", path=None ),  "scp://testuser@testhost/" )

    def test_Creds(self):
        # pass in creds and make sure we get them back
        sshfs = SSHFilesystem.SSHFilesystem()
        self.assertEquals( sshfs.Creds( 'yabiusername', {1:1,2:2}, None ), {1:1, 2:2} )

        with self.assertRaises( AssertionError ):
            sshfs.Creds(None,None,None)



    DUMMY_CERT =  {'user':'dummyuser',
                   'cert':'dummycert',
                   'key':'dummykey'}
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/'}} )
    @patch('yabibe.utils.geventtools.GET', MagicMock( return_value= (200,
                                                                     "OK",
                                                                     json.dumps( DUMMY_CERT ))))
    def test_Creds_fetch(self):
        """test that when creds are asked for by username, they are fetched"""
        sshfs = SSHFilesystem.SSHFilesystem()
        self.assertTrue( sshfs.Creds('yabiusername', None, "scp://user@remotehost/path/"), self.DUMMY_CERT )


    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/'}} )
    @patch('yabibe.utils.geventtools.GET', MagicMock( return_value= (404,
                                                                     "Not Found",
                                                                     "No Decrypted Credential Available" )))
    def test_Creds_fetch_non_existant_cred(self):
        """test that a 404 error raises a NoSuchCredential"""
        sshfs = SSHFilesystem.SSHFilesystem()
        with self.assertRaises( NoSuchCredential ):
            sshfs.Creds('yabiusername', None, "scp://user@remotehost/path/"), self.DUMMY_CERT
