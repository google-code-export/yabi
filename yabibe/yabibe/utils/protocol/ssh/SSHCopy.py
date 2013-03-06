"""Implement scp connections"""
import os
import sys

from BaseShell import BaseShell
from SSHRun import SSHExecProcessProtocolParamiko
from yabibe.conf import config
from yabibe.utils.FifoPool import Fifos


DEBUG = True

if DEBUG:
    def debug(*args, **kwargs):
        import sys
        sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))
else:
    def debug(*args, **kwargs):
        pass
        
class SCPError(Exception):
    pass

class SSHCopy(BaseShell):
    scp = os.path.join( os.path.dirname(os.path.realpath(__file__)), "paramiko-ssh.py" )
    python = sys.executable
    
    def WriteToRemote(self, certfile, remoteurl, port=None, password="",fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])
        
        port = port or 22
        
        if not fifo:
            fifo = Fifos.get()
            
        remoteuserhost,remotepath = remoteurl.split(':',1)
        remoteuser, remotehost = remoteuserhost.split('@',1)
            
        command  = [   self.python, self.scp ]
        command += [ "-i", certfile ] if certfile else []
        command += [ "-p", password ] if password else []
        command += [ "-u", remoteuser ] if remoteuser else []
        command += [ "-H", remotehost ] if remotehost else []
        command += [ "-l", fifo, "-r", remotepath ]
        
        if DEBUG:
            print "CERTFILE",certfile
            print "REMOTEUSER",remoteuser
            print "REMOTEHOST",remotehost
            print "REMOTEPATH",remotepath
            print "PORT",port
            print "PASSWORD","*"*len(password)
            print "FIFO",fifo
            
            print "COMMAND",command
            
        return BaseShell.execute(self,SSHExecProcessProtocolParamiko(),
            command, subenv
        ), fifo
        
    def ReadFromRemote(self,certfile,remoteurl,port=None,password="",fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])
        
        port = port or 22
        
        if not fifo:
            fifo = Fifos.get()
            
            
        remoteuserhost,remotepath = remoteurl.split(':',1)
        remoteuser, remotehost = remoteuserhost.split('@',1)
            
        command  = [   self.python, self.scp ]
        command += [ "-i", certfile ] if certfile else []
        command += [ "-p", password ] if password else []
        command += [ "-u", remoteuser ] if remoteuser else []
        command += [ "-H", remotehost ] if remotehost else []
        command += [ "-L", fifo, "-R", remotepath ]
        
        if DEBUG:
            print "CERTFILE",certfile
            print "REMOTEUSER",remoteuser
            print "REMOTEHOST",remotehost
            print "REMOTEPATH",remotepath
            print "PORT",port
            print "PASSWORD","*"*len(password)
            print "FIFO",fifo
            
            print "COMMAND",command
        
        return BaseShell.execute(self,SSHExecProcessProtocolParamiko(),
            command, subenv
        ), fifo
        
    def WriteCompressedToRemote(self, certfile, remoteurl, port=None, password="",fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])
        
        port = port or 22
        
        if not fifo:
            fifo = Fifos.get()
            
        remoteuserhost,remotepath = remoteurl.split(':',1)
        remoteuser, remotehost = remoteuserhost.split('@',1)
         
        path,filename = os.path.split(remotepath)
        print "REMOTEPATH",path,"===",filename
        
        command  = [   self.python, self.scp ]
        command += [ "-i", certfile ] if certfile else []
        command += [ "-p", password ] if password else []
        command += [ "-u", remoteuser ] if remoteuser else []
        command += [ "-H", remotehost ] if remotehost else []
        command += [ "-x", 'tar --gzip --extract --directory "%s"'%(path) ]
        command += [ "-I", fifo ]
                
        if DEBUG:
            print "CERTFILE",certfile
            print "REMOTEUSER",remoteuser
            print "REMOTEHOST",remotehost
            print "REMOTEPATH",remotepath
            print "PORT",port
            print "PASSWORD","*"*len(password)
            print "FIFO",fifo
            
            print "COMMAND",command
            
        return BaseShell.execute(self,SSHExecProcessProtocolParamiko(),
            command, subenv
        ), fifo
    
    def ReadCompressedFromRemote(self,certfile,remoteurl,port=None,password="",fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])
        
        port = port or 22
        
        if not fifo:
            fifo = Fifos.get()
                        
        remoteuserhost,remotepath = remoteurl.split(':',1)
        remoteuser, remotehost = remoteuserhost.split('@',1)
        
        path,filename = os.path.split(remotepath)
        print "REMOTEPATH",path,"=====",filename
            
        command  = [   self.python, self.scp ]
        command += [ "-i", certfile ] if certfile else []
        command += [ "-p", password ] if password else []
        command += [ "-u", remoteuser ] if remoteuser else []
        command += [ "-H", remotehost ] if remotehost else []
        command += [ "-x", 'tar --gzip --directory "%s" --create "%s"'%(path,filename if filename else ".") ]
        command += [ "-O", fifo ]
        command += [ "-N" ]
        
        if DEBUG:
            print "CERTFILE",certfile
            print "REMOTEUSER",remoteuser
            print "REMOTEHOST",remotehost
            print "REMOTEPATH",remotepath
            print "PORT",port
            print "PASSWORD","*"*len(password)
            print "FIFO",fifo
            
            print "COMMAND",command
        
        return BaseShell.execute(self,SSHExecProcessProtocolParamiko(),
            command, subenv
        ), fifo
        
