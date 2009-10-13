"""Sun Grid Engine tools
"""
from twisted.internet import protocol
from twisted.internet import reactor

import re
import stackless
import shlex
from tempfile import mktemp
import os

QSUB_COMMAND = "/opt/sge/6.2u3/bin/lx24-amd64/qsub"             #-N job-101 /home/yabi/test-remote
QSTAT_COMMAND = "/opt/sge/6.2u3/bin/lx24-amd64/qstat"

SUDO = "/usr/bin/sudo"

class QsubProcessProtocol(protocol.ProcessProtocol):
    """ Job returns 'Your job 10 ("jobname") has been submitted'
    """
    regexp = re.compile(r'Your job (\d+) \("(\w+)"\) has been submitted')
    
    def __init__(self):
        self.err = ""
        self.out = ""
        self.exitcode = None
        self.jobid = None
        self.jobname = None
        
    def connectionMade(self):
        # when the process finally spawns, close stdin, to indicate we have nothing to say to it
        self.transport.closeStdin()
        
    def outReceived(self, data):
        self.out += data
        
    def errReceived(self, data):
        self.err += data
            
    def outConnectionLost(self):
        # stdout was closed. this will be our endpoint reference
        re_match = self.regexp.search(self.out)
        print "OUT:",self.out
        print "ERR:",self.err
        print "RE_MATCH:",re_match
        if re_match  and self.exitcode==0:
            print "Group",re_match.groups()
            jobid, jobname = re_match.groups()
            self.jobid = int(jobid)
            self.jobname = jobname
        
    def processEnded(self, status_object):
        self.exitcode = status_object.value.exitCode
        
    def isDone(self):
        return self.exitcode != None
    
def qsub_spawn(jobname, commandfile, user="yabi", stdout="STDOUT.txt", stderr="STDERR.txt"):
    """Spawn a process to run an xml job. return the process handler"""
    subenv = os.environ.copy()
    pp = QsubProcessProtocol()
    reactor.spawnProcess(   pp,
                            SUDO, 
                            args=[
                                SUDO,
                                "-u",
                                user,
                                QSUB_COMMAND,
                                "-N",
                                jobname,
                                commandfile
                            ],
                            env=subenv
                        )

    return pp

def qsub(jobname, command, user="yabi", stdout="STDOUT.txt", stderr="STDERR.txt"):
    # use shlex to parse the command into executable and arguments
    lexer = shlex.shlex(command, posix=True)
    lexer.wordchars += r"-.:;/"
    arguments = list(lexer)
     
     # make a temporary file to store the command in
    tempfile = mktemp()
    temp=open(tempfile,'w+b')
    temp.write(" ".join(arguments))
    temp.write("\n")
    temp.close()
    
    # run the qsub process.
    pp = qsub_spawn(jobname,tempfile)
    
    while not pp.isDone():
        stackless.schedule()
        
    if pp.exitcode!=0:
        err = pp.err
        from ex.connector.ExecConnector import ExecutionError
        raise ExecutionError(err)
    
    # delete temp?
    os.unlink(tempfile)
    
    return pp.jobid

class QstatProcessProtocol(protocol.ProcessProtocol):
    """ Job returns 'Your job 10 ("jobname") has been submitted'
    
job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID 
-----------------------------------------------------------------------------------------------------------------
    12 0.00000 job-101    yabi         qw    10/13/2009 10:42:52                                    1        

    """
    # match line of form  "   12 0.00000 job-101    yabi         qw    10/13/2009 10:42:52                                    1        "
    regexp = re.compile(r"""\s+(\d+)                    # job-ID
                            \s+([\d.]+)                 # prior
                            \s+([\w\-\d_]+)             # name
                            \s+(\w+)                    # user
                            \s+(\w+)                    # state
                            \s+([\d/]+)                 # submit/start
                            \s+(\d+:\d+:\d+)            # at
                            \s+(.+)                     # everything else on the line
                        """, re.VERBOSE)
    
    def __init__(self):
        self.err = ""
        self.out = ""
        self.exitcode = None
        
    def connectionMade(self):
        # when the process finally spawns, close stdin, to indicate we have nothing to say to it
        self.transport.closeStdin()
        
    def outReceived(self, data):
        self.out += data
        
    def errReceived(self, data):
        self.err += data
            
    def outConnectionLost(self):
        # stdout was closed. this will be our endpoint reference
        re_match = self.regexp.search(self.out)
        print "RE_MATCH:",re_match
        if re_match:
            print "groups:",re_match.groups()
        
    def processEnded(self, status_object):
        self.exitcode = status_object.value.exitCode
        
    def isDone(self):
        return self.exitcode != None
    
def qstat_spawn(user="yabi"):
    """return the status of a running job via qstat
    /opt/sge/6.2u3/bin/lx24-amd64/qstat -u yabi
    """
    subenv = os.environ.copy()
    pp = QstatProcessProtocol()
    reactor.spawnProcess(   pp,
                            QSTAT_COMMAND, 
                            args=[
                                QSTAT_COMMAND,
                                "-u",
                                user
                            ],
                            env=subenv
                        )

    return pp

def qstat(user="yabi"):
    # run the qsub process.
    pp = qstat_spawn(user)
    
    while not pp.isDone():
        stackless.schedule()
        
    if pp.exitcode!=0:
        err = pp.err
        from ex.connector.ExecConnector import ExecutionError
        raise ExecutionError(err)
    