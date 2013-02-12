from yabibe.reactor import GeventReactor
from twisted.internet.error import ReactorAlreadyInstalledError
try:
    GeventReactor.install()
except ReactorAlreadyInstalledError:
    pass

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
import pwd

from config import TestConfig
from FileSet import FileSet, TempFile
                
from yabibe.server.resources.TaskManager.TaskManager import TaskManager
from yabibe.exceptions import CredentialNotFound, IsADirectory, PermissionDenied, InvalidPath

from twisted.internet import reactor

def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

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
        

class TaskManagerTestSuite(unittest.TestCase):
    """Test TaskManager"""
    testdir="/tmp/yabi-ssh-filesystem-unit-test" 
    
    def setUp(self):
        if os.path.exists(self.testdir):
            os.system("sudo rm -rf '%s'"%self.testdir)
        os.makedirs(self.testdir)
        os.chmod(self.testdir,0777)
        self.tm = TaskManager()
    
    def tearDown(self):
        pass
            
    def test_construct(self):
        tm = TaskManager()
        self.assertTrue(tm)

    def run_reactor(self):
        self._run = True
        try:
            reactor.startRunning()
        except Exception:
            pass
        while self._run:
            if reactor.doInner():
                break
        self._run = False

    def reactor_stop(self):
        self._run = False

    def reactor_run(self, gthread=None):
        self.run_reactor()

        #if gthread is passed in, check for exception and raise it if there is one
        if gthread is not None and gthread.exception:
            raise gthread.exception


    USER_CERT =  {'user':os.environ.get("TESTUSER","dummyuser"),
                   'username':os.environ.get('USER','dummyusername'),
                   'password':os.environ.get('PASSWORD','dummypasssword')}

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def ntest_run(self):
        """test mkdir on ssh filesystem"""
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshex.set_check_knownhosts(True)
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
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run(thread)

