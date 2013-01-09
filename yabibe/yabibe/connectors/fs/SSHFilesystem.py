import json
import os

import gevent
from yabibe.utils.LockQueue import LockQueue
from yabibe.utils.RetryController import SSHRetryController, HARD

import FSConnector
from yabibe.exceptions import PermissionDenied, InvalidPath
from yabibe.conf import config
from yabibe.utils.decorators import retry
from yabibe.utils.protocol import ssh
from yabibe.server.resources.TaskManager.TaskTools import UserCreds, uriify

sshauth = ssh.SSHAuth.SSHAuth()

# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "scp"

DEBUG = False

MAX_SSH_CONNECTIONS = 15                                     # zero is unlimited
    

sshretry = SSHRetryController()

class SSHHardError(Exception): pass
class SSHSoftError(Exception): pass

class SSHFilesystem(FSConnector.FSConnector, ssh.KeyStore.KeyStore, object):
    """This is the resource that connects to the ssh backends"""
    VERSION=0.1
    NAME="SSH Filesystem"
    copymode = "ssh"
    
    def __init__(self):
        FSConnector.FSConnector.__init__(self)
        
        # make a path to store keys in
        configdir = config.config['backend']['certificates']
        ssh.KeyStore.KeyStore.__init__(self, dir=configdir)
        
        # instantiate a lock queue for this backend. Key refers to the particular back end. None is the global queue
        self.lockqueue = LockQueue( MAX_SSH_CONNECTIONS )
        
    def lock(self,*args,**kwargs):
        return self.lockqueue.lock(*args, **kwargs)
        
    def unlock(self, tag):
        return self.lockqueue.unlock(tag)
        
    @retry(5,(InvalidPath,PermissionDenied, SSHHardError))
    #@call_count
    def mkdir(self, host, username, path, port=22, yabiusername=None, creds={},priority=0):
        # acquire our queue lock
        if priority:
            lock = self.lockqueue.lock()
        
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])                         #, tag=(yabiusername,username,host,path)
        
        # we need to munge the path for transport over ssh (cause it sucks)
        #mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.mkdir(usercert,host,path, port=port, username=creds['username'], password=creds['password'])
        
        while not pp.isDone():
            gevent.sleep()
            
        if priority:
            self.lockqueue.unlock(lock)
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            elif "No such file or directory" in err:
                raise InvalidPath("No such file or directory\n")
            else:
                # hard or soft error?
                error_type = sshretry.test(pp.exitcode, pp.err)
                if error_type == HARD:
                    print "SSH failed with exit code %d and output: %s"%(pp.exitcode,out)
                    raise SSHHardError(err)
                else:
                    raise SSHSoftError(err)
        
        if DEBUG:
            print "mkdir_data=",out
            print "err", err

        if usercert:
            os.unlink(usercert)

        return out
        
    #@lock
    @retry(5,(InvalidPath,PermissionDenied, SSHHardError))
    #@call_count
    def rm(self, host, username, path, port=22, yabiusername=None, recurse=False, creds={}, priority=0):
        # acquire our queue lock
        if priority:
            lock = self.lockqueue.lock()
        
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        
        # we need to munge the path for transport over gsissh (cause it sucks)
        #mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.rm(usercert,host,path, port=port,args="-rf" if recurse else "-f", username=creds['username'], password=creds['password'])
        
        while not pp.isDone():
            gevent.sleep()
        
        if priority:
            self.lockqueue.unlock(lock)
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            elif "No such file or directory" in err:
                raise InvalidPath("No such file or directory\n")
            else:
                # hard or soft error?
                error_type = sshretry.test(pp.exitcode, pp.err)
                if error_type == HARD:
                    print "SSH failed with exit code %d and output: %s"%(pp.exitcode,out)
                    raise SSHHardError(err)
                else:
                    raise SSHSoftError(err)
        
        if DEBUG:
            print "rm_data=",out
            print "err", err

        if usercert:
            os.unlink(usercert)

        return out
    
    #@lock
    @retry(5,(InvalidPath,PermissionDenied, SSHHardError))                            
    #@call_count
    def ls(self, host, username, path, port=22, yabiusername=None, recurse=False, culldots=True, creds={}, priority=0):
        if DEBUG:
            print "SSHFilesystem::ls(",host,username,path,port,yabiusername,recurse,culldots,creds,priority,")"
        
        # acquire our queue lock
        if priority:
            lock = self.lockqueue.lock()
                
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        
        # we need to munge the path for transport over gsissh (cause it sucks)
        #mungedpath = '"' + path.replace('"',r'\"') + '"'
        #print "===>LS",usercert,host,path, port, "-lFR" if recurse else "-lF", creds['username'], creds['password']
        pp = ssh.Shell.ls(usercert,host,path, port=port, recurse=recurse, username=creds['username'], password=creds['password'] )
        
        while not pp.isDone():
            gevent.sleep()
            
        # release our queue lock
        if priority:
            self.lockqueue.unlock(lock)
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            elif "No such file" in err:
                raise InvalidPath("No such file or directory\n")
            else:
                # hard or soft error?
                error_type = sshretry.test(pp.exitcode, pp.err)
                if error_type == HARD:
                    print "SSH failed with exit code %d and output: %s"%(pp.exitcode,out)
                    raise SSHHardError(pp.err)
                else:
                    raise SSHSoftError(pp.err)
        
        try:
            ls_data = json.loads(out)
        except ValueError, ve:
            raise SSHHardError("Could not list directory: Paramiko script returned malformed JSON data.")
        
        if usercert:
            os.unlink(usercert)
                        
        return ls_data
        
    @retry(5,(InvalidPath,PermissionDenied, SSHHardError))
    #@call_count
    def ln(self, host, username, target, link, port=22, yabiusername=None, creds={},priority=0):
        # acquire our queue lock
        if priority:
            lock = self.lockqueue.lock()
        
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])                         #, tag=(yabiusername,username,host,path)
        
        # we need to munge the path for transport over ssh (cause it sucks)
        #mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.ln(usercert,host,target, link, port=port, username=creds['username'], password=creds['password'])
        
        while not pp.isDone():
            gevent.sleep()
            
        if priority:
            self.lockqueue.unlock(lock)
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            elif "No such file or directory" in err:
                raise InvalidPath("No such file or directory\n")
            else:
                # hard or soft error?
                error_type = sshretry.test(pp.exitcode, pp.err)
                if error_type == HARD:
                    print "SSH failed with exit code %d and output: %s"%(pp.exitcode,out)
                    raise SSHHardError(err)
                else:
                    raise SSHSoftError(err)
        
        if DEBUG:
            print "ln_data=",out
            print "ln_err", err
        
        if usercert:
            os.unlink(usercert)
        
        return out
        
    @retry(5,(InvalidPath,PermissionDenied, SSHHardError))
    #@call_count
    def cp(self, host, username, src, dst, port=22, yabiusername=None, recurse=False, creds={},priority=0):
        # acquire our queue lock
        if priority:
            lock = self.lockqueue.lock()
        
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])                         #, tag=(yabiusername,username,host,path)
        
        # we need to munge the path for transport over ssh (cause it sucks)
        #mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.cp(usercert,host,src, dst, args="-r" if recurse else None, port=port, username=creds['username'], password=creds['password'])
        
        while not pp.isDone():
            gevent.sleep()
            
        if priority:
            self.lockqueue.unlock(lock)
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            elif "No such file or directory" in err:
                if not ("cp: cannot stat" in str(err) and "*': No such file or directory" in str(err) and recurse==True):
                    raise InvalidPath("No such file or directory\n")
            else:
                # hard or soft error?
                error_type = sshretry.test(pp.exitcode, pp.err)
                if error_type == HARD:
                    print "SSH failed with exit code %d and output: %s"%(pp.exitcode,out)
                    raise SSHHardError(err)
                else:
                    raise SSHSoftError(err)
        
        if DEBUG:
            print "cp_data=",out
            print "cp_err", err

        if usercert:
            os.unlink(usercert)

        return out
        
    
        
    #@lock
    def GetWriteFifo(self, host=None, username=None, path=None, port=22, filename=None, fifo=None, yabiusername=None, creds={}, priority=0):
        """sets up the chain needed to setup a write fifo from a remote path as a certain user.
        
        pass in here the username, path
    
        if a fifo pathis apssed in, use that one instead of making one
    
        when everything is setup and ready, deferred will be called with (proc, fifo), with proc being the python subprocess Popen object
        and fifo being the filesystem location of the fifo.
        """
        if DEBUG:
            print "SSHFilesystem::GetWriteFifo( host:"+host,",username:",username,",path:",path,",filename:",filename,",fifo:",fifo,",yabiusername:",yabiusername,",creds:",creds,")"
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        return ssh.Copy.WriteToRemote(usercert,dst,port=port,password=str(creds['password']),fifo=fifo)
        
    #@lock
    def GetReadFifo(self, host=None, username=None, path=None, port=22, filename=None, fifo=None, yabiusername=None, creds={}, priority=0):
        """sets up the chain needed to setup a read fifo from a remote path as a certain user.
        
        pass in here the username, path, and a deferred
    
        if a fifo pathis apssed in, use that one instead of making one
    
        when everything is setup and ready, deferred will be called with (proc, fifo), with proc being the python subprocess Popen object
        and fifo being the filesystem location of the fifo.
        """
        if DEBUG:
            print "SSH::GetReadFifo(",host,username,path,filename,fifo,yabiusername,creds,")"
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        return ssh.Copy.ReadFromRemote(usercert,dst,port=port,password=creds['password'],fifo=fifo)
        
    def GetCompressedReadFifo(self, host=None, username=None, path=None, port=22, filename=None, fifo=None, yabiusername=None, creds={}, priority=0):
        """sets up the chain needed to setup a read fifo from a remote path as a certain user that streams in a compressed file archive"""
        if DEBUG:
            print "SSH::GetCompressedReadFifo(",host,username,path,filename,fifo,yabiusername,creds,")"
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        return ssh.Copy.ReadCompressedFromRemote(usercert,dst,port=port,password=creds['password'],fifo=fifo)
        
    def GetCompressedWriteFifo(self, host=None, username=None, path=None, port=22, filename=None, fifo=None, yabiusername=None, creds={}, priority=0):
        """sets up the chain needed to setup a read fifo from a remote path as a certain user that streams in a compressed file archive"""
        if DEBUG:
            print "SSH::GetCompressedWriteFifo(",host,username,path,filename,fifo,yabiusername,creds,")"
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        creds = self.Creds(yabiusername, creds)
        usercert = self.save_identity(creds['key'])
        return ssh.Copy.WriteCompressedToRemote(usercert,dst,port=port,password=creds['password'],fifo=fifo)
        
    def Creds(self, yabiusername, creds):
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        return creds or UserCreds( yabiusername, uriify( SCHEMA, username, host, path=path), credtype="fs")
