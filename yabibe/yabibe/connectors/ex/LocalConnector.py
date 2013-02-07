
from yabibe.exceptions import ExecutionError
from ExecConnector import ExecConnector

# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "localex"

DEBUG = True

if DEBUG:
    import sys
    def debug(*args, **kwargs):
        sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))
else:
    def debug(*args, **kwargs):
        return

from twistedweb2 import http, responsecode, http_headers, stream

import shlex
import os
import gevent
import tempfile

from yabibe.utils.geventtools import sleep

from yabibe.conf import config
from SubmissionTemplate import make_script, Submission

from twisted.internet import protocol
from twisted.internet import reactor

class LocalExecutionProcessProtocol(protocol.ProcessProtocol):
    unify_line_endings=True
    
    def __init__(self, stdin=None, stdout=None, stderr=None, cleanup=None):
        self.stdin=stdin
        self.stderr = stderr
        self.stdout = stdout
        self.exitcode = None
        self.cleanup = cleanup              # if we need to run a cleanup closure post execution
        self.pid = None
                
    def connectionMade(self):
        # when the process finally spawns, close stdin, to indicate we have nothing to say to it
        if self.stdin:
            self.transport.write(self.stdin)
        self.transport.closeStdin()
        self.started = True
        self.pid = self.transport.pid
                
    def outReceived(self, data):
        self.stdout.write(data.replace("\r\n","\n") if self.unify_line_endings else data )
        
    def errReceived(self, data):
        self.stderr.write(data.replace("\r\n","\n") if self.unify_line_endings else data )
    
    def processEnded(self, status_object):
        if self.cleanup:
            self.cleanup()
        self.exitcode = status_object.value.exitCode
        
    def isDone(self):
        return self.exitcode != None
        
    def isFailed(self):
        return self.isDone() and self.exitcode != 0
        
    def isStarted(self):
        return self.started
    
        
class LocalExecutionShell(object):
    def __init__(self):
        self.subenv={}

    def _make_path(self):
        return "/usr/bin"    

    def _make_env(self, environ=None):
        """Return a custom environment for the specified cert file"""
        subenv = environ.copy() if environ!=None else os.environ.copy()
        return subenv    

    def execute(self, pp, command, working):
        """execute a command using a process protocol"""
        
        self.subenv = subenv = self._make_env()
        subprocess = reactor.spawnProcess(   pp,
                                command[0],
                                command,
                                env=subenv,
                                path=working
                            )
        return subprocess

class LocalRun(LocalExecutionShell):
    def run(self,working, submission, submission_stdout, submission_stderr):
        """spawn a local task.
        run it in working directory 'working'
        run submission script in a shell
        write submission script stdout and stderr streams
        """
        
        # write submission script into tempfile
        from yabibe.conf import config
        
        temp_fd, temp_fname = config.mktemp(".sh")
        with open(temp_fname, 'w') as fh:
            fh.write(submission.render())
        
        # write a little cleanup closure to pass to P.P.
        def cleanup():
            os.unlink(temp_fname)                                   # delete submission file on task end.
        
        pp = LocalExecutionProcessProtocol(stdout=submission_stdout,stderr=submission_stderr,cleanup=cleanup)
        subprocess = self.execute(pp,["/bin/bash",temp_fname],working)
        
        return subprocess, pp

class StreamLogger(object):
    """write() on this behaves like file stream but sends data via log callback
    """
    def __init__(self,callback):
        self.callback = callback
        
    def write(self,string):
        self.callback(string)

class LocalConnector(ExecConnector):
    delay = 0.1
    
    #"command":command,
                    #"working":working,
                    #"stdout":stdout,
                    #"stderr":stderr,
                    #"walltime":walltime,
                    #"memory":memory,
                    #"cpus":cpus,
                    #"queue":queue,
                    #"jobtype":jobtype, 
                    #"modules":modules,
                    #"tasknum":tasknum,
                    #"tasktotal":tasktotal
    
    #def run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
    def run(self, yabiusername, working, submission, submission_data, state, jobid, info, log):
        """runs a command through the Local execution backend. Callbacks for status/logging.
        
        state: callback to set task state
        jobid: callback to set jobid/taskid/processid
        info: callback to set key/value info
        log: callback for log messages to go to admin
        """
        try:
            debug("calling state!",state)
            state("Unsubmitted")
            gevent.sleep(self.delay)
            state("Pending")
            gevent.sleep(self.delay)
            
            sub = Submission(submission)
            sub.render(submission_data)
            
            outstream = StreamLogger(lambda x: log("sub out:"+x))
            errstream = StreamLogger(lambda x: log("sub err:"+x))
            
            if len(sub.render().strip()):
                log("rendered submission script is:\n"+sub.render())
            else:
                log("WARNING: submission template renders to an empty script. Nothing will run.")
            
            localrun = LocalRun()
            subprocess, pp = localrun.run(working, sub, submission_stdout=outstream, submission_stderr=errstream)
            
            # wait for task to start then store its process id
            while not pp.isStarted():
                gevent.sleep(self.delay)

            state("Running")
            gevent.sleep(self.delay)
                
            # get pid and log it
            jobid(str(pp.pid))
            
            # get env and info it
            info(localrun.subenv)
        
            while not pp.isDone():
                gevent.sleep(self.delay)
            
            if pp.exitcode==0:
                # success
                state("Done")
                return
                
            state("Error")               
        except Exception, ee:
            debug(ee)
            import traceback
            traceback.print_exc()
            state("Error")
       
