"""Implement scp connections"""
import os
import sys

from BaseShell import BaseShell, BaseShellProcessProtocol
from yabibe.conf import config


DEBUG = False

import sys
def debug(*args, **kwargs):
    if DEBUG:
        sys.stderr.write("debug<%s>\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

class SSHExecProcessProtocolParamiko(BaseShellProcessProtocol):
    def __init__(self, stdin_data=None):
        BaseShellProcessProtocol.__init__(self)
        self.started = False
        self.stdin_data = stdin_data
        
    def connectionMade(self):
        debug("connectionMade")
        if self.stdin_data:
            debug('write')
            self.transport.write(self.stdin_data)

        debug("closing")        
        self.transport.closeStdin()
        self.started = True

        debug("started")
                
    def isStarted(self):
        debug("isStarted")
        return self.started
        
class SSHError(Exception):
    pass
        
class SSHRun(BaseShell):
    ssh_exec = os.path.join( os.path.dirname(os.path.realpath(__file__)), "paramiko-ssh.py" )
    python = sys.executable                     # use the same python that yabi backend is running under
    
    def run(self, certfile, remote_command="hostname", username="yabi", host="faramir.localdomain", working="/tmp", port="22", stdout="STDOUT.txt", stderr="STDERR.txt",password="",modules=[],streamin=None):
        """Spawn a process to run a remote ssh job. return the process handler"""
        subenv = self._make_env()
        
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])
        
        if modules:
            remote_command = "&&".join(["module load %s"%module for module in modules]+[remote_command])
        
        debug("running remote command:",remote_command)
        
        command = [self.python, self.ssh_exec ]
        command += ["-i",certfile] if certfile else []
        command += ["-p",password] if password else []
        command += ["-u",username] if username else []
        command += ["-H",host] if host else []
        command.extend( [ "-x", remote_command ] )
        
        debug("COMMAND:",command)
            
        # hande log setting
        #if config.config['execution']['logcommand']:
            # screen out password from the command
        #    command_log = command[:]
	    #if "-p" in command_log:
        # 	index = command_log.index("-p")+1
        #	command_log[index]="*"*len(command_log[index])
        #    print "ssh running command: "+str(command_log)
            
        #if config.config['execution']['logscripts']:
        #    print "ssh attempting remote command: "+remote_command
            
        return BaseShell.execute(self,SSHExecProcessProtocolParamiko(streamin),command,subenv)
