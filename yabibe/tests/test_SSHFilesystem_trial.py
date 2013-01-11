from yabibe.reactor import GeventReactor
GeventReactor.install()

from twisted.trial import unittest
from mock import MagicMock, patch
import os
import tempfile
import StringIO
import json
import sys
import gevent

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
    DUMMY_CERT =  {'user':'dummyuser',
                   'cert':'dummycert',
                   'key':'dummykey',
                   'username':'dummyusername',
                   'password':'dummypasssword'}
 
    def setUp(self):
        self.sshfs = SSHFilesystem.SSHFilesystem()
    
    def tearDown(self):
        pass
        
    def test_construct(self):
        sshfs = SSHFilesystem.SSHFilesystem()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    #@patch('twisted.internet.reactor.spawnProcess', MagicMock())
    def test_mkdir(self):
        """test mkdir on ssh filesystem"""
        def threadlet():
            debug("START")
            res = self.sshfs.mkdir("localhost","localuser","/tmp/testmkdir", creds=self.DUMMY_CERT)
            print "result"
            print res

            self._run = False

        self._run = True

        thread = gevent.spawn(threadlet)
        while True:
            debug("PING")
            gevent.sleep(1.0)
        
        self.assertTrue(False)
