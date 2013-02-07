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
from StubAdminServer import make_server
                
from yabibe.server.resources.TaskManager.Task import MainTask
from yabibe.server.resources.BaseResource import base
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

def createfile(filename, blocks=1, bs=1024):
    with open(filename, 'wb') as fh:
        for i in range(blocks):
            fh.write(createdata(bs))

def createdata(count):
    return "".join( [ random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-=_+[]{}\\|;:'\",<.>/?`~")
                                  for X in range(count) ] )

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

##
## Global Mocks
##
StatusMock = MagicMock()
LogMock = MagicMock()

class MainTaskTestSuite(unittest.TestCase):
    """Test Task"""
    testdir="/tmp/yabi-ssh-filesystem-unit-test" 
    
    def setUp(self):
        if os.path.exists(self.testdir):
            os.system("sudo rm -rf '%s'"%self.testdir)
        os.makedirs(self.testdir)
        os.chmod(self.testdir,0777)
        self.task = MainTask()
    
    def tearDown(self):
        pass
            
    def test_construct(self):
        task = MainTask()
        self.assertTrue(task)

    def run_reactor(self):
        self._run = True
        try:
            reactor.startRunning()
        except Exception:
            pass
        reactor.greenlet = gevent.getcurrent()
        while self._run:
            reactor.doInner()
        self._run = False

    def reactor_stop(self):
        self._run = False

    def reactor_run(self, gthread=None):
        self.run_reactor()

        #if gthread is passed in, check for exception and raise it if there is one
        if gthread is not None and gthread.exception:
            raise gthread.exception        

    def test_load_json_into_task(self):
        data = """
{
    "taskid": "task-101",
    "statusurl":"http://localhost/",
    "errorurl":"http://localhost/",
    "stagein":"/tmp",
    "stageout":"/tmp",
    "yabiusername":"%s",
    "exec":
    {
      "submission":"blah",
      "backend":"localex://localhost/",
      "command":"command",
      "fsbackend":"fsbackend",
      "workingdir":"working"
    }
}
"""

        task = MainTask()
        task.load_json(data)

        self.assertTrue(hasattr(task,'json'))

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8080/',
                                                         'hmackey':'dummyhmac',
                                                         'admin_cert_check':False,
                                                         'start_https':False,
                                                         'certificates':"/tmp/certs",
                                                         'temp':'/tmp'
                                                         }} )
    @patch('yabibe.server.resources.TaskManager.TaskTools.Status',StatusMock)       # our test status call
    @patch('yabibe.server.resources.TaskManager.TaskTools.Log',LogMock)             # our test log call
    @patch('yabibe.server.resources.TaskManager.TaskTools.Sleep',MagicMock())       # retry delays have no effect
    def test_main_task_run(self):
        # load connectors
        base.LoadConnectors()

        # path to a testing area
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # dest and source
        dpath = os.path.join( path, "dest.dat" ) 
        spath = os.path.join( path, "source.dat" )
        createfile(spath,blocks=128)

        # our config
        tc = TestConfig()

        # make server
        debug('starting server')

        # our users creds for json encoding
        creds = {
            'name':'localfs backend',
            'scheme':'localfs',
            'homedir':'/tmp',
            'credential':'Users Credential',
            'username':'dummyusername',
            'password':'dummypassword',
            'cert':'dummycert',
            'key':'dummykey'
        }
        
        services = {
            ('/ws/credential/exec/testuser/','uri=localex%3A//localhost/'):('text/json',json.dumps(creds))
        }
        server = make_server(services)
        debug('started',server)

        job_data = {
            "taskid": "task-101",
            "statusurl":"http://localhost:80/",
            "errorurl":"http://localhost:80/",
            "stagein": [
            {
                "src": "localfs://localhost%s"%spath,
                "dst": "localfs://localhost%s"%dpath,
                "order": 0
            } ],
            "stageout":"localfs://localhost/tmp/test-yabi-job-output/",
            "stageout_method":"copy",
            "yabiusername":tc['username'],
            "exec":
            {
                "submission":"cd ${working}\n${command} 1>${stdout} 2>${stderr}",
                "backend":"localex://localhost/",
                "command":"hostname",
                "fsbackend":"localfs://localhost/tmp/test-yabi-working-directory",
                # TODO: the trailing output directory here shouldnt be passed in by yabiadmin
                # we created the 'output' so we should know about it and append it to the URI
                "workingdir":"/tmp/test-yabi-working-directory/output"
            }
        }

        jobjson = json.dumps(job_data)
        
        task = MainTask()
        task.load_json(jobjson)
        debug(1)

        def threadlet():
            try:
                debug("running",task,task.main)
                result = task.main()
                debug("ran",result)
                
            finally:
                self.reactor_stop()

        thread = gevent.spawn(threadlet)
        self.reactor_run(thread)


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

    
