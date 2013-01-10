import json
import os
import uuid

import gevent
from twisted.python import log
from twistedweb2 import http, responsecode, http_headers, stream

from yabibe.exceptions import ExecutionError
from ExecConnector import ExecConnector
from SubmissionTemplate import make_script
from yabibe.conf import config
from yabibe.server.resources.TaskManager.TaskTools import RemoteInfo
from yabibe.utils.RetryController import PbsproQsubRetryController, PbsproQstatRetryController, HARD
from yabibe.utils.geventtools import sleep
from yabibe.utils.protocol import ssh


# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "ssh+pbspro"

DEBUG = False

# where we temporarily store the submission scripts on the submission host
TMP_DIR = "/tmp"


sshauth = ssh.SSHAuth.SSHAuth()
qsubretry = PbsproQsubRetryController()
qstatretry = PbsproQstatRetryController()

# for Job status updates, poll this often
def JobPollGeneratorDefault():
    """Generator for these MUST be infinite. Cause you don't know how long the job will take. Default is to hit it pretty hard."""
    delay = 10.0
    while delay<60.0:
        yield delay
        delay *= 1.05           # increase by 5%
    
    while True:
        yield 60.0

# now we inherit our particular errors
class SSHQsubException(Exception): pass
class SSHQstatException(Exception): pass
class SSHTransportException(Exception): pass

# and further inherit hard and soft under those
class SSHQsubSoftException(Exception): pass
class SSHQstatSoftException(Exception): pass
class SSHQsubHardException(Exception): pass
class SSHQstatHardException(Exception): pass

def rerun_delays():
    # when our retry system is fully expressed (no corner cases) we could potentially make this an infinite generator
    delay = 5.0
    while delay<300.0:
        yield delay
        delay *= 2.0
    totaltime=0.0
    while totaltime<21600.0:                    # 6 hours
        totaltime+=300.0
        yield 300.0

class SSHPbsproConnector(ExecConnector, ssh.KeyStore.KeyStore):
    def __init__(self):
        ExecConnector.__init__(self)
        
        configdir = config.config['backend']['certificates']
        ssh.KeyStore.KeyStore.__init__(self, dir=configdir)
    
    def _ssh_qsub(self, yabiusername, creds, command, working, username, host, remoteurl, submission, stdout, stderr, modules, walltime=None, memory=None, cpus=None, queue=None, tasknum=None, tasktotal=None ):
        """This submits via ssh the qsub command. This returns the jobid, or raises an exception on an error"""
        assert type(modules) is not str and type(modules) is not unicode, "parameter modules should be sequence or None, not a string or unicode"
        
        submission_script = os.path.join(TMP_DIR,str(uuid.uuid4())+".sh")
        if DEBUG:
            print "submission script path is %s"%(submission_script)
        
        qsub_submission_script = "qsub -N '%s' -e '%s' -o '%s' '%s'"%(
                                                                        "yabi"+remoteurl.rsplit('/')[-1],
                                                                        os.path.join(working,stderr),
                                                                        os.path.join(working,stdout),
                                                                        submission_script
                                                                    )
        
        # build up our remote qsub command
        ssh_command = "cat >'%s' && "%(submission_script)
        ssh_command += qsub_submission_script
        ssh_command += " ; EXIT=$? "
        ssh_command += " ; rm '%s'"%(submission_script)
        #ssh_command += " ; echo $EXIT"
        ssh_command += " ; exit $EXIT"

        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")
    
        usercert = self.save_identity(creds['key'])
        
        script_string = make_script(submission,working,command,modules,cpus,memory,walltime,yabiusername,username,host,queue, stdout, stderr, tasknum, tasktotal)    
        
        # hande log setting
        if config.config['execution']['logcommand']:
            print SCHEMA+" attempting submission command: "+qsub_submission_script
            
        if config.config['execution']['logscripts']:
            print SCHEMA+" submission script:"
            print script_string
            
        
        if DEBUG:
            print "_ssh_qsub"
            print "usercert:",usercert
            print "command:",command
            print "username:",username
            print "host:",host
            print "working:",working
            print "port:","22"
            print "stdout:",stdout
            print "stderr:",stderr
            print "modules",modules
            print "password:","*"*len(creds['password'])
            print "script:",repr(script_string)
            
        pp = ssh.Run.run(usercert,ssh_command,username,host,working=None,port="22",stdout=None,stderr=None,password=creds['password'], modules=modules, streamin=script_string)
        while not pp.isDone():
            gevent.sleep()
          
        if DEBUG:
            print "EXITCODE:",pp.exitcode
            print "STDERR:",pp.err
            print "STDOUT:",pp.out
            
        if pp.exitcode==0:
            # success
            return pp.out.strip().split("\n")[-1]
        else:
            # so the process has exited non zero. If the exit code is 255 its a transport error... we should retry.
            if pp.exitcode==255:
                raise SSHTransportException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
            # otherwise we need to analyse the result to see if its a hard or soft failure
            error_type = qsubretry.test(pp.exitcode, pp.err)
            if error_type == HARD:
                # hard error.
                raise SSHQsubHardException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
        # everything else is soft
        raise SSHQsubSoftException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
                
    def _ssh_qstat(self, yabiusername, creds, command, working, username, host, stdout, stderr, modules, jobid):
        """This submits via ssh the qstat command. This takes the jobid"""
        assert type(modules) is not str and type(modules) is not unicode, "parameter modules should be sequence or None, not a string or unicode"
        
        ssh_command = "cat > /dev/null && qstat -x -f '%s'"%( jobid )
        ssh_command += " | sed -ne '1h;1!H;${;g;s/\\n\\t//g;p;}'"
        
        
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")
    
        usercert = self.save_identity(creds['key'])
        
        if DEBUG:
            print "usercert:",usercert
            print "command:",command
            print "username:",username
            print "host:",host
            print "working:",working
            print "port:","22"
            print "stdout:",stdout
            print "stderr:",stderr
            print "modules",modules
            print "password:","*"*len(creds['password'])
            
        pp = ssh.Run.run(usercert,ssh_command,username,host,working=None,port="22",stdout=None,stderr=None,password=creds['password'], modules=modules )
        while not pp.isDone():
            gevent.sleep()
            
        if pp.exitcode==0:
            # success. lets process our qstat results
            output={}
            
            for line in pp.out.split("\n"):
                line = line.strip()
                if " = " in line:
                    key, value = line.split(" = ")
                    output[key] = value
                    
            return {jobid:output}
        else:
            # so the process has exited non zero. If the exit code is 255 its a transport error... we should retry.
            if pp.exitcode==255:
                raise SSHTransportException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
            # otherwise we need to analyse the result to see if its a hard or soft failure
            error_type = qstatretry.test(pp.exitcode, pp.err)
            if error_type == HARD:
                # hard error.
                raise SSHQstatHardException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
        # everything else is soft
        raise SSHQstatSoftException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
    def run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None, tasknum=None, tasktotal=None):
        modules = [] if not module else [X.strip() for X in module.split(",")]    
        delay_gen = rerun_delays()

        while True:                 # retry on soft failure
            try:
                jobid = self._ssh_qsub(yabiusername,creds,command,working,username,host,remoteurl,submission,stdout,stderr,modules,walltime,memory,cpus,queue,tasknum,tasktotal)
                break               # success... now we continue
            except (SSHQsubHardException, ExecutionError), ee:
                channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream = str(ee) ))
                return
            except (SSHQsubSoftException, SSHTransportException), softexc:
                # delay and then retry
                try:
                    sleep(delay_gen.next())
                except StopIteration:
                    # run our of retries.
                    channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream = str(softexc) ))
                    return
                
        # send an OK message, but leave the stream open
        client_stream = stream.ProducerStream()
        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))
        
        # now the job is submitted, lets remember it
        self.add_running(jobid, {'username':username})
        
        # lets report our id to the caller
        client_stream.write("id=%s\n"%jobid)
        
        try:
            self.main_loop( yabiusername, creds, command, working, username, host, remoteurl, client_stream, stdout, stderr, modules, jobid)
        except (ExecutionError, SSHQstatException), ee:
            import traceback
            traceback.print_exc()
            client_stream.write("Error\n")
        finally:
                
            # delete finished job
            self.del_running(jobid)
            
            client_stream.finish()
    
    def resume(self, jobid, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None, tasknum=None, tasktotal=None):
        # send an OK message, but leave the stream open
        client_stream = stream.ProducerStream()
        modules = [] if not module else [X.strip() for X in module.split(",")]
        
        try:
            username = self.get_running(jobid)['username']
        except KeyError, ke:
            channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream = "No such jobid resumable: %s"%jobid ))
        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))

        self.main_loop( yabiusername, creds, command, working, username, host, remoteurl, client_stream, stdout, stderr, modules, jobid)
        
        # delete finished job
        self.del_running(jobid)
            
        client_stream.finish()            
    
    def main_loop(self, yabiusername, creds, command, working, username, host, remoteurl, client_stream, stdout, stderr, modules, jobid):
        newstate = state = None
        delay = JobPollGeneratorDefault()
        while state!="Done":
            # pause
            sleep(delay.next())
            
            delay_gen = rerun_delays()
            while True:
                try:
                    jobsummary = self._ssh_qstat(yabiusername, creds, command, working, username, host, stdout, stderr, modules, jobid)
                    break               # success... now we continue
                except (SSHQstatSoftException, SSHTransportException), softexc:
                    # delay and then retry
                    try:
                        sleep(delay_gen.next())
                    except StopIteration:
                        # run out of retries.
                        raise softexc
            
            self.update_running(jobid,jobsummary)
            
            if jobid in jobsummary:
                # job has not finished
                if 'job_state' in jobsummary[jobid]:
                    status = jobsummary[jobid]['job_state']
                    
                    log_msg="ssh+pbspro jobid:%s is status:%s... "%(jobid,status)
                    
                    if status == 'F' or status == "X":
                        if 'Exit_status' in jobsummary[jobid]:
                            log_msg += "exit status present and it is %s"%jobsummary[jobid]['Exit_status']
                        
                        # state 'F' means complete OR error
                        if 'Exit_status' in jobsummary[jobid] and jobsummary[jobid]['Exit_status'] == '0':
                            newstate = "Done"
                        else:
                            newstate = "Error"
                    else:
                        newstate = dict(B="Running", E="Running", F="Done", H="Pending", M="Pending", Q="Unsubmitted", R="Running", S="Running", T="Pending", U="Pending", W="Pending", X="Done")[status]
                    
                    log.msg(log_msg + "thus setting job state to: %s"%newstate)
                    
                else:
                    print "Error! We atempted to qstat the job <%s>, the call was successful, but we got no data at all. The job just VANISHED! We are ignoring this job at this time and will check again later"%jobid

            else:
                # job has finished
                sleep(15.0)                      # deal with SGE flush bizarreness (files dont flush from remote host immediately. Totally retarded)
                print "ERROR: jobid %s not in jobsummary"%jobid
                print "jobsummary is",jobsummary
                
                # if there is standard error from the qstat command, report that!
                
                
                newstate = "Error"
            
            #if DEBUG:
                #print "Job summary:",jobsummary
                
            
            if state!=newstate:
                state=newstate
                #print "Writing state",state
                client_stream.write("%s\n"%state)
                
                # report the full status to the remote_url
                if remoteurl:
                    if jobid in jobsummary and jobsummary[jobid]:
                        RemoteInfo(remoteurl,json.dumps(jobsummary[jobid]))
                    else:
                        print "Cannot call RemoteInfo call for job",jobid
                
            if state=="Error":
                #print "CLOSING STREAM"
                client_stream.finish()
                return        
 