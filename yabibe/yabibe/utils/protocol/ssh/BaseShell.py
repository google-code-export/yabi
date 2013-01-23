import os
from twisted.internet import protocol
from twisted.internet import reactor
    
DEBUG = False

import sys
def debug(*args, **kwargs):
    if DEBUG:
        sys.stderr.write("debug<%s>\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))
    
class BaseShellProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, stdin=None):
        self.stdin=stdin
        self.err = ""
        self.out = ""
        self.exitcode = None
        debug("init")
        
    def connectionMade(self):
        # when the process finally spawns, close stdin, to indicate we have nothing to say to it
        debug("connectionMade")
        if self.stdin:
            self.transport.write(self.stdin)
        self.transport.closeStdin()

    def outReceived(self, data):
        self.out += data
        debug("OUT:",data)
        
    def errReceived(self, data):
        self.err += data
        debug("ERR:",data)
    
    def outConnectionLost(self):
        # stdout was closed. this will be our endpoint reference
        debug("Out lost")
        self.unifyLineEndings()
        
    def inConenctionLost(self):
        debug("In lost")
        self.unifyLineEndings()
        
    def errConnectionLost(self):
        debug("Err lost")
        self.unifyLineEndings()
        
    def processEnded(self, status_object):
        self.exitcode = status_object.value.exitCode
        debug("proc ended",self.exitcode)
        self.unifyLineEndings()

    def processExited(self, reason):
        debug("proc exit",reason)
        self.exitcode = reason.value.exitCode
        self.unifyLineEndings()
        
    def unifyLineEndings(self):
        # try to unify the line endings to \n
        self.out = self.out.replace("\r\n","\n")
        self.err = self.err.replace("\r\n","\n")
        
    def isDone(self):
        return self.exitcode != None
        
    def isFailed(self):
        return self.isDone() and self.exitcode != 0

class BaseShell(object):
    def __init__(self):
        pass

    def _make_path(self):
        return "/usr/bin"    

    def _make_env(self, environ=None):
        """Return a custom environment for the specified cert file"""
        subenv = environ.copy() if environ!=None else os.environ.copy()
        return subenv    

    def execute(self, pp, command, env=None):
        """execute a command using a process protocol"""

        subenv = env or self._make_env()
        debug("exec:",command,pp)
        reactor.spawnProcess(   pp,
                                command[0],
                                command,
                                env=subenv,
                                path=self._make_path(),
                            )
        return pp
