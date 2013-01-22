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
        pass
            
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
        #reactor.installWaker()
        #reactor._handleSignals()
        try:
            reactor.startRunning()
        except Exception:
            pass
        while self._run:
            #sys.stderr.write("+")
            if reactor.doInner():
                #sys.stderr.write("break!")
                break
        self._run = False

    def reactor_stop(self):
        self._run = False

    def reactor_run(self):
        self.run_reactor()


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
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_mkdir_permission_denied(self):
        """test mkdir on ssh filesystem that we don't have write permissions on"""
        # turn off world writable
        os.chmod( self.testdir, 0755)

        
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
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_mkdir_creates_all_parents(self):
        """test mkdir on ssh filesystem where the path to create in does not exist"""
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
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_file_with_no_recurse(self):
        """test a plain deletion of a file"""
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
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_path_with_no_recurse(self):
        """test trying to delete a directory without recurse"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)
        os.chmod(path, 0755)
                        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is there
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.isdir(path))
                
                with self.assertRaises( IsADirectory ):
                    res = self.sshfs.rm("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                'username':tc['username'],
                                                                                'password':tc['password'] } )
                # directory should still be there
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.isdir(path))

            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_path_with_recurse(self):
        """test trying to delete a directory with recurse"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)
        os.chmod(path, 0755)
                        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is there
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.isdir(path))
                
                res = self.sshfs.rm("localhost",tc['username'],path, recurse=True, creds={'user':tc['username'],
                                                                                          'username':tc['username'],
                                                                                          'password':tc['password'] } )
                # success returns nothing
                self.assertFalse(res.strip())
                
                # directory should still be there
                self.assertFalse(os.path.exists(path))
                self.assertFalse(os.path.isdir(path))

            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_file_without_permissions(self):
        """test a deletion of a file we don't have permission to delete"""
        path = os.path.join(self.testdir,"testfile.dat")
        with open(path, 'wb') as fh:
            for i in range(256):
                data = "".join( [ random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-=_+[]{}\\|;:'\",<.>/?`~")
                                  for X in range(256) ] )
                fh.write(data)
                
        # unwritable as shell user (but writable as test runner)
        os.chmod(path,0755)
        os.chmod(self.testdir, 0755)

        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is there
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.isfile(path))

                with self.assertRaises( PermissionDenied ):
                    res = self.sshfs.rm("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                'username':tc['username'],
                                                                                'password':tc['password'] } )

                # make sure the file is still there
                self.assertTrue( os.path.exists(path) )
                self.assertTrue( os.path.isfile(path) )

                # try again with recurse. Should have no effect
                with self.assertRaises( PermissionDenied ):
                    res = self.sshfs.rm("localhost",tc['username'],path, recurse=True, creds={'user':tc['username'],
                                                                                              'username':tc['username'],
                                                                                              'password':tc['password'] } )

                # make sure the file is still there
                self.assertTrue( os.path.exists(path) )
                self.assertTrue( os.path.isfile(path) )

                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()
    
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_rm_nonexisting_path(self):
        """test trying to delete a path that does not exist"""
        path = "/file/path/that/does/not/exist/123456756"
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is not there
                self.assertFalse(os.path.exists(path))

                # because our rm is "-f" (force), this call should succeed
                res = self.sshfs.rm("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                            'username':tc['username'],
                                                                            'password':tc['password'] } )
                # success returns nothing
                self.assertFalse(res.strip())
                
                # directory should still not be there
                self.assertFalse(os.path.exists(path))

            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ls_non_existing_path(self):
        """test trying to list a path that does not exist"""
        path = "/file/path/that/does/not/exist/123456756"

        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is not there
                self.assertFalse(os.path.exists(path))

                with self.assertRaises(InvalidPath):
                    res = self.sshfs.ls("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                                'username':tc['username'],
                                                                                'password':tc['password'] } )
               
                # directory should still not be there
                self.assertFalse(os.path.exists(path))

            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ls_existing_path(self):
        """test trying to list a path that we've created"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)
        os.chmod(path, 0755)

        subdirs = ( '1', '2', 'test' )

        for subpath in subdirs:
            os.makedirs( os.path.join( path, subpath ) )
            os.chmod( os.path.join( path, subpath ), 0755 )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is present
                self.assertTrue(os.path.exists(path))

                res = self.sshfs.ls("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                            'username':tc['username'],
                                                                            'password':tc['password'] } )

                # TODO: the rest return strings. This returns dict. Some unification should be done between ls/mkdir/rm etc
                self.assertTrue( path in res )
                r = res[path]                  #move inside dicrionary for this path
                
                self.assertTrue( 'files' in r )
                self.assertTrue( 'directories' in r )
                self.assertEquals( len(r['directories']), 3 )
                for entry in r['directories']:
                    # should not be a symlink
                    self.assertFalse( entry[3] )

                    # first should be directory name
                    self.assertTrue( entry[0] in subdirs )
              
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ls_recursive_path(self):
        """test trying to recursively list a multi level path that we've created"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)
        os.chmod(path, 0755)

        subdirs = ( '1', '2', 'test', "1/blah", "2/temp", "1/blah/bing" )

        for subpath in subdirs:
            os.makedirs( os.path.join( path, subpath ) )
            os.chmod( os.path.join( path, subpath ), 0755 )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is present
                self.assertTrue(os.path.exists(path))

                res = self.sshfs.ls("localhost",tc['username'],path, recurse=True, creds={'user':tc['username'],
                                                                            'username':tc['username'],
                                                                            'password':tc['password'] } )

                # TODO: the rest return strings. This returns dict. Some unification should be done between ls/mkdir/rm etc
                self.assertTrue( path in res )
                r = res[path]                  #move inside dicrionary for this path
                
                self.assertTrue( 'files' in r )
                self.assertTrue( 'directories' in r )
                self.assertEquals( len(r['directories']), 3 )
                for entry in r['directories']:
                    # should not be a symlink
                    self.assertFalse( entry[3] )

                    # first should be directory name
                    self.assertTrue( entry[0] in ('1','2','test') )

                # now look for the other directories. They all must be here
                keys = res.keys()
                for d in subdirs:
                    keys.remove(os.path.join(path, d))
                keys.remove(path)

                # there should be no other directories listed but these
                self.assertEquals( len(keys), 0 )
              
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    
    
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ls_existing_path_with_files(self):
        """test trying to list a path that we've created that also has some files in it"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)
        os.chmod(path, 0755)

        files = ( '1.dat', '2.doc', 'test.txt' )

        for filename in files:
            fpath = os.path.join(path,filename)
            with open(fpath, 'wb') as fh:
                for i in range(256):
                    data = "".join( [ random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-=_+[]{}\\|;:'\",<.>/?`~")
                                      for X in range(256) ] )
                    fh.write(data)
            
            os.chmod( fpath, 0755 )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is present
                self.assertTrue(os.path.exists(path))

                res = self.sshfs.ls("localhost",tc['username'],path, creds={'user':tc['username'],
                                                                            'username':tc['username'],
                                                                            'password':tc['password'] } )

                # TODO: the rest return strings. This returns dict. Some unification should be done between ls/mkdir/rm etc
                self.assertTrue( path in res )
                r = res[path]                  #move inside dicrionary for this path
                
                self.assertTrue( 'files' in r )
                self.assertTrue( 'directories' in r )
                self.assertEquals( len(r['files']), 3 )
                for entry in r['files']:
                    # should not be a symlink
                    self.assertFalse( entry[3] )

                    # first should be directory name
                    self.assertTrue( entry[0] in files )
              
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    def createfile(self,filename, blocks=1, bs=1024):
        with open(filename, 'wb') as fh:
            for i in range(blocks):
                fh.write("".join( [ random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()-=_+[]{}\\|;:'\",<.>/?`~")
                                      for X in range(bs) ] ))

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ln_creation_in_restricted_directory(self):
        """test trying to sym-link to a file but we can't write in our symlink dir"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # we have no rights to write a symlink into this directory
        os.chmod(path, 0755)

        # target
        tpath = os.path.join( path, "target.dat" ) 
        self.createfile(tpath)

        # link
        lpath = os.path.join( path, "source.dat" )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is present
                self.assertTrue(os.path.exists(tpath))

                with self.assertRaises(PermissionDenied):
                    self.sshfs.ln("localhost",tc['username'],tpath, lpath, creds={'user':tc['username'],
                                                                                  'username':tc['username'],
                                                                                  'password':tc['password'] } )
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ln_creation(self):
        """test trying to sym-link to a file"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # target
        tpath = os.path.join( path, "target.dat" ) 
        self.createfile(tpath)

        # link
        lpath = os.path.join( path, "source.dat" )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is present
                self.assertTrue(os.path.exists(tpath))

                res = self.sshfs.ln("localhost",tc['username'],tpath, lpath, creds={'user':tc['username'],
                                                                                    'username':tc['username'],
                                                                                    'password':tc['password'] } )

                self.assertFalse( res.strip() )

                # test for symlink
                self.assertTrue( os.path.exists(lpath) )
                self.assertTrue( os.path.islink(lpath) )

                # link should point where we asked it to
                self.assertEquals( os.readlink(lpath), tpath )
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_ln_creation_to_non_existing_path(self):
        """test trying to sym-link to a missing file"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # target
        tpath = os.path.join( path, "target.dat" ) 
        
        # link
        lpath = os.path.join( path, "source.dat" )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is absent
                self.assertFalse(os.path.exists(tpath))

                # our ln is symbolic so it doesn't return any error on a non existing path
                res = self.sshfs.ln("localhost",tc['username'],tpath, lpath, creds={'user':tc['username'],
                                                                                    'username':tc['username'],
                                                                                    'password':tc['password'] } )

                self.assertFalse( res.strip() )

                # test for symlink
                self.assertFalse( os.path.exists(lpath) )
                self.assertTrue( os.path.islink(lpath) )

                # link should point where we asked it to (which doesn't exist)
                self.assertEquals( os.readlink(lpath), tpath )

                # opening it should error
                with self.assertRaises(IOError):
                    open(lpath, 'r')
                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_non_existing_path(self):
        """test trying to copy a missing file"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # dest and source
        dpath = os.path.join( path, "dest.dat" ) 
        spath = os.path.join( path, "source.dat" )
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure directory is absent
                self.assertFalse(os.path.exists(spath))

                # should raise InvalidPath exception
                with self.assertRaises(InvalidPath):
                    self.sshfs.cp("localhost",tc['username'],spath, dpath, creds={'user':tc['username'],
                                                                                  'username':tc['username'],
                                                                                  'password':tc['password'] } )
                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()


    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_existing_file(self):
        """copy a file"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # dest and source
        dpath = os.path.join( path, "dest.dat" ) 
        spath = os.path.join( path, "source.dat" )
        self.createfile(spath,kb=128)

        # we need to read this file to copy it
        os.chmod(spath,0755)
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                res = self.sshfs.cp("localhost",tc['username'],spath, dpath, creds={'user':tc['username'],
                                                                                    'username':tc['username'],
                                                                                    'password':tc['password'] } )

                self.assertFalse(res.strip())

                # make sure files are identical
                with open(spath) as sh:
                    with open(dpath) as dh:
                        self.assertEquals(sh.read(), dh.read())
                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    
    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_dir_non_recursive(self):
        """try to copy a directory without specifying recurse"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # destdir and sourcedir
        dpath = os.path.join( path, "destdir" ) 
        spath = os.path.join( path, "sourcedir" )
        os.makedirs(spath)
        os.makedirs(dpath)
        
        # we need to read this directory to copy it
        os.chmod(spath,0755)

        # stick a file in in
        self.createfile(os.path.join(spath,"dummy.dat"))
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                with self.assertRaises(IsADirectory):
                    res = self.sshfs.cp("localhost",tc['username'],spath, dpath, creds={'user':tc['username'],
                                                                                        'username':tc['username'],
                                                                                        'password':tc['password'] } )
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_dir_recursive_with_no_read_permissions(self):
        """try to copy a directory without read permissione"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # destdir and sourcedir
        dpath = os.path.join( path, "destdir" ) 
        spath = os.path.join( path, "sourcedir" )
        os.makedirs(spath)
        os.makedirs(dpath)
        
        # we need to read this directory to copy it
        os.chmod(spath,0755)

        # stick a file in in
        self.createfile(os.path.join(spath,"dummy.dat"))
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                with self.assertRaises(PermissionDenied):
                    res = self.sshfs.cp("localhost",tc['username'],spath, dpath, recurse=True, creds={'user':tc['username'],
                                                                                                      'username':tc['username'],
                                                                                                      'password':tc['password'] } )
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_dir_recursively(self):
        """try to copy a directory recursively"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # destdir and sourcedir
        dpath = os.path.join( path, "destdir" ) 
        spath = os.path.join( path, "sourcedir" )
        os.makedirs(spath)
        os.makedirs(dpath)

        # source readable, dest writable
        os.chmod(spath, 0755)
        os.chmod(dpath, 0777)
        
        # stick a file in it and make it readable
        fpath = os.path.join(spath,"dummy.dat")
        self.createfile(fpath)
        os.chmod(fpath, 0755)
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                #debug("src:%s"%spath)
                #debug("dst:%s"%dpath)

                res = self.sshfs.cp("localhost",tc['username'],spath, dpath, recurse=True, creds={'user':tc['username'],
                                                                                                  'username':tc['username'],
                                                                                                  'password':tc['password'] } )

                # sourcedir should appear inside destdir
                self.assertTrue(os.path.isdir(os.path.join(dpath,'sourcedir')))

                # the file should be inside that
                self.assertTrue(os.path.isfile(os.path.join(dpath,'sourcedir','dummy.dat')))

                # the file should be identical to the source
                with open(fpath) as src:
                    with open(os.path.join(dpath,'sourcedir','dummy.dat')) as dst:
                        self.assertEquals( src.read(), dst.read() )
                              
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_dir_recursively_to_different_folder_name(self):
        """try to copy a directory recursively but make the destination another name, not the containing folder"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # destdir and sourcedir
        dpath = os.path.join( path, "destdir" ) 
        spath = os.path.join( path, "sourcedir" )
        os.makedirs(spath)
        os.makedirs(dpath)

        # source readable, dest writable
        os.chmod(spath, 0755)
        os.chmod(dpath, 0777)
        
        # stick a file in it and make it readable
        fpath = os.path.join(spath,"dummy.dat")
        self.createfile(fpath)
        os.chmod(fpath, 0755)
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                #debug("src:%s"%spath)
                #debug("dst:%s"%dpath)

                res = self.sshfs.cp("localhost",tc['username'],spath, dpath+"/newname", recurse=True, creds={'user':tc['username'],
                                                                                                  'username':tc['username'],
                                                                                                  'password':tc['password'] } )

                # newname should appear inside destdir
                self.assertTrue(os.path.isdir(os.path.join(dpath,'newname')))

                # the file should be inside that
                self.assertTrue(os.path.isfile(os.path.join(dpath,'newname','dummy.dat')))

                # the file should be identical to the source
                with open(fpath) as src:
                    with open(os.path.join(dpath,'newname','dummy.dat')) as dst:
                        self.assertEquals( src.read(), dst.read() )
                              
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_non_existant_dir_recursively(self):
        """try to copy a directory recursively"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # destdir and sourcedir
        dpath = os.path.join( path, "destdir" ) 
        spath = os.path.join( path, "sourcedir" )
        os.makedirs(dpath)

        # dest writable
        os.chmod(dpath, 0777)
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertFalse(os.path.exists(spath))

                with self.assertRaises(InvalidPath):
                    self.sshfs.cp("localhost",tc['username'],spath, dpath, recurse=True, creds={'user':tc['username'],
                                                                                                'username':tc['username'],
                                                                                                'password':tc['password'] } )

            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_cp_existing_file_recursively(self):
        """copy a file but but do it recursively"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # give ourselves write access to the dir
        os.chmod(path, 0777)

        # dest and source
        dpath = os.path.join( path, "dest.dat" ) 
        spath = os.path.join( path, "source.dat" )
        self.createfile(spath,kb=128)

        # we need to read this file to copy it
        os.chmod(spath,0755)
        
        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                res = self.sshfs.cp("localhost",tc['username'],spath, dpath, recurse=True, creds={'user':tc['username'],
                                                                                                  'username':tc['username'],
                                                                                                  'password':tc['password'] } )

                self.assertFalse(res.strip())

                # make sure files are identical
                with open(spath) as sh:
                    with open(dpath) as dh:
                        self.assertEquals(sh.read(), dh.read())
                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()

    @patch.dict('yabibe.conf.config.config', {'backend':{'admin':'http://localhost:8000/','hmackey':'dummyhmac','admin_cert_check':False}} )
    def test_get_read_fifo(self):
        """read a files contents via a fifo"""
        path = os.path.join(self.testdir,"testdir")
        os.makedirs(path)

        # we have no rights to write a symlink into this directory
        os.chmod(path, 0755)

        # source we want to read
        spath = os.path.join( path, "source.dat" ) 
        self.createfile(spath, bs=9652)
        os.chmod(spath, 0755)

        def threadlet():
            try:
                # making the sshfs connector do this means we dont need an admin with a hostkeys table set etc.
                self.sshfs.set_check_knownhosts(True)
                tc = TestConfig()

                # make sure file is present
                self.assertTrue(os.path.exists(spath))

                pp, fifo = self.sshfs.GetReadFifo("localhost",tc['username'],path, filename="source.dat", creds={'user':tc['username'],
                                                                                                                 'username':tc['username'],
                                                                                                                 'password':tc['password'] } )
                debug("started",pp,fifo)
                self.assertTrue(pp)
                self.assertTrue(fifo)

                # lets read from the fifo and check with our file
                with open(spath) as fileh:
                    #debug(fileh)
                    with open(fifo) as fifoh:
                    #with os.fdopen(os.open(fifo, os.O_RDONLY|os.O_NONBLOCK)) as fifoh:
                        #import fcntl, errno
                        #fcntl.fcntl(fifoh.fileno(), fcntl.F_SETFL, os.O_NONBLOCK) 

                        indat = fileh.read()
                        outdat = fifoh.read()
                        debug("comparing %d bytes"%len(indat))
                        self.assertEquals(indat,outdat)

                # wait for task to finish
                while not pp.isDone():
                    from twisted.internet import process
                    process.reapAllProcesses()
                    time.sleep(1)
                    import signal
                    debug(signal.getsignal(signal.SIGCHLD))
                    debug(pp.isDone())

                # lets make sure after these are closed that our exit code is 0
                self.assertEquals( pp.exitcode, 0 )
                debug(res)
                
            finally:
                self.reactor_stop()
                
        thread = gevent.spawn(threadlet)
        self.reactor_run()
