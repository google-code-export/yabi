import json
import os
import uuid
import random

import gevent
from twisted.python import log
from twistedweb2 import http, responsecode, http_headers, stream

from yabibe.exceptions import ExecutionError
from ExecConnector import ExecConnector
from SubmissionTemplate import make_script, Submission
from yabibe.conf import config
from yabibe.server.resources.TaskManager.TaskTools import RemoteInfo
from yabibe.utils.RetryController import SSHSGEQsubRetryController, SSHSGEQstatRetryController, SSHSGEQacctRetryController, HARD
from yabibe.utils.geventtools import sleep
from yabibe.utils.protocol import ssh


# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "ssh+sge"

DEBUG = False

import sys
def debug(*args, **kwargs):
    if DEBUG:
        sys.stderr.write("debug<%s>\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))


# where we temporarily store the submission scripts on the submission host
TMP_DIR = "/tmp"


sshauth = ssh.SSHAuth.SSHAuth()             # TODO: remove the reliance on this deprecated code
qsubretry = SSHSGEQsubRetryController()
qstatretry = SSHSGEQstatRetryController()
qacctretry = SSHSGEQacctRetryController()

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
        
class SSHSGEConnector(ExecConnector):
    def __init__(self):
        ExecConnector.__init__(self)
        self.configdir = config.config['backend']['certificates']      #TODO: put our ssh keys in here
        
    def _ssh_qsub(self, yabiusername, working, submission, submission_data, log_cb):
        subdata = Submission(submission).render(submission_data)
        # remote submission script name
        submission_script = os.path.join(TMP_DIR,str(uuid.uuid4())+".sh")

        qsub_command = "'%s' -N '%s' -e '%s' -o '%s' -wd '%s' '%s'"%(    
                                                                    config.config['ssh+sge']['qsub'],
                                                                    "yabi-%s"%random.randint(0,10000),  ###TODO: use the yabi id as a number not random.
                                                                    os.path.join(working,submission_data['stderr']),
                                                                    os.path.join(working,submission_data['stdout']),
                                                                    working,
                                                                    submission_script
                                                                )
        # build up our remote qsub command
        ssh_command = "cat >'%s' && "%(submission_script)
        ssh_command += submission_script
        ssh_command += " ; EXIT=$? "
        ssh_command += " ; rm '%s'"%(submission_script)
        #ssh_command += " ; echo $EXIT"
        ssh_command += " ; exit $EXIT"

        debug(ssh_command=ssh_command)

        # get our creds
        creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")

        with TemporaryFile( creds['key'] ) as sshkey:
            log_cb( "Submission command:\n" + qsub_command )
            log_cb( "Submission script:\n" + subdata )

            pp = ssh.Run.run( sshkey.filename, ssh_command, username=creds['username'], host=creds['hostname'], password=creds['password'], streamin=subdata)
            while not pp.isDone():
                gevent.sleep()

            if pp.exitcode==0:
                # success
                jobid_string = pp.out.strip().split("\n")[-1]
                return jobid_string.split('("')[-1].split('")')[0]
            else:
                # process has exited non-zero. 255 is transport error and should be retried
                if pp.exitcode==255:
                    raise SSHTransportException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))

                # else we need to analyse the result and decide on hard/soft
                error_type = qsubretry.test(pp.exitcode,pp.err)
                if error_type == HARD:
                    # hard error
                    raise SSHQsubHardException("SSHQsub error: SSH exited %d with message %s"%(pp.exitcode,pp.err))

            #soft error
            raise SSHQsubSoftException("SSHQsub error: SSH exited: %d with message %s"%(pp.exitcode,pp.err))
            
    def _ssh_qstat(self, yabiusername, creds, command, working, username, host, stdout, stderr, modules, jobid):
        """This submits via ssh the qstat command. This takes the jobid"""
        assert type(modules) is not str and type(modules) is not unicode, "parameter modules should be sequence or None, not a string or unicode"
        
        ssh_command = "cat > /dev/null && '%s' -f -j '%s'"%( config.config['ssh+sge']['qstat'],jobid )
        
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
                if ":" in line:
                    key, value = line.split(":",1)
                    output[key] = value.strip()
                    
            return {jobid:output}
        else:
            # non zero. 255 is transport error
            if pp.exitcode==255:
                raise SSHTransportException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
            # otherwise we need to analyse the result to see if its a hard or soft failure
            error_type = qstatretry.test(pp.exitcode, pp.err)
            if error_type == HARD:
                # hard error.
                raise SSHQstatHardException("SSHQstat Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
        # everything else is soft
        raise SSHQstatSoftException("SSHQstat Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
         
    def _ssh_qacct(self, yabiusername, creds, command, working, username, host, stdout, stderr, modules, jobid):
        """This submits via ssh the qstat command. This takes the jobid"""
        assert type(modules) is not str and type(modules) is not unicode, "parameter modules should be sequence or None, not a string or unicode"
        
        ssh_command = "cat > /dev/null && '%s' -j '%s'"%( config.config['ssh+sge']['qacct'],jobid )
        
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
                if " " in line:
                    key, value = line.split(None,1)
                    output[key] = value.strip()
                    
            return {jobid:output}
        else:
            if pp.exitcode==255:
                raise SSHTransportException("Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
            # otherwise we need to analyse the result to see if its a hard or soft failure
            error_type = qacctretry.test(pp.exitcode, pp.err)
            if error_type == HARD:
                # hard error.
                raise SSHQacctHardException("SSHQacct Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))
            
        # everything else is soft
        raise SSHQacctSoftException("SSHQacct Error: SSH exited %d with message %s"%(pp.exitcode,pp.err))

    def run(self, yabiusername, working, submission, submission_data, state_cb, jobid_cb, info_cb, log_cb):
        """Runs a command through the SSHSGE backend. Callbacks for info/log/state.

        state: callback to set task state
        jobid: callback to set jobid/taskid/processid
        info: callback to set key/value info
        log: callback for log messages to go to admin
        """
        
        delay_gen = rerun_delays()
            
        while True:        
            try:
                jobid = self._ssh_qsub(yabiusername, working, submission, submission_data, log_cb)
                break               # success... escape retry loop
            except (SSHQsubSoftException, SSHTransportException), softexc:
                #delay then retry. 
                sleep(delay_gen.next())
                
        # send an OK message, but leave the stream open
        log_cb( "Job successfully submitted via qsub. Job ID: %s"%jobid )
        jobid_cb( str(jobid) )
        
        # now the job is submitted, lets remember it
        self.add_running(job, {'username':username})
        
        try:
            self.main_loop( yabiusername, creds, command, working, username, host, remoteurl, client_stream, stdout, stderr, modules, jobid)
            log_cb('The job has completed')
        except (ExecutionError, SSHQstatException), ee:
            import traceback
            traceback.print_exc()
            state_cb('error')
            log_cb('The job has failed with the following exception:\n'+traceback.format_exc())
        finally:
                
            # delete finished job
            self.del_running(jobid)

            
            
    def resume(self, jobid, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
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

                    # TODO HACK FIXME: 
                    # SGE code is broken, we don't get a job_state
                    # setting to job_state R, then fall through to qacct when qstat can't find job
                    jobsummary[jobid]['job_state']='R'         
                    break           # success
                except (SSHQstatSoftException, SSHTransportException), softexc:
                    # delay and then retry
                    try:
                        sleep(delay_gen.next())
                    except StopIteration:
                        # run out of retries.
                        raise softexc
                
                except SSHQstatHardException, qse:
                    if "Following jobs do not exist" in str(qse):
                        # job has errored or completed. We now search using qacct
                        qacctdelay_gen = rerun_delays()
                        while True:
                            try:
                                jobsummary = self._ssh_qacct(yabiusername, creds, command, working, username, host, stdout, stderr, modules, jobid)
                                break
                            except (SSHQacctSoftException, SSHTransportException), softexc:
                                # delay and then retry
                                try:
                                    sleep(qacctdelay_gen.next())
                                except StopIteration:
                                    # run out of retries.
                                    raise softexc
                       
                        # TODO HACK FIXME: 
                        # SGE code is broken, we don't get a job_state
                        # setting to job_state R, then fall through to qacct when qstat can't find job
                        if 'failed' in jobsummary[jobid] and 'exit_status' in jobsummary[jobid] and \
                            jobsummary[jobid]['failed'] != 'undefined' and jobsummary[jobid]['exit_status'] != 'undefined':
                            jobsummary[jobid]['job_state']='C'         
                        else:
                            jobsummary[jobid]['job_state']='R'         

                        break
            
            self.update_running(jobid, jobsummary)
            
            if jobid in jobsummary:
                # job has not finished
                if 'job_state' not in jobsummary[jobid]:
                    newstate="Unsubmitted"
                else:
                    status = jobsummary[jobid]['job_state']
                    
                    log_msg = "ssh+sge jobid:%s is status:%s..."%(jobid,status)
                    
                    if status == 'C':
                        #print "STATUS IS C <=============================================================",jobsummary[jobid]['exit_status']
                        # state 'C' means complete OR error
                        if 'exit_status' in jobsummary[jobid]:
                            log_msg += "exit status present and it is %s"%jobsummary[jobid]['exit_status']
                        
                        if 'exit_status' in jobsummary[jobid] and jobsummary[jobid]['exit_status'] == '0':
                            newstate = "Done"
                        else:
                            newstate = "Error"
                    else:
                        newstate = dict(Q="Unsubmitted", E="Running", H="Pending", R="Running", T="Pending", W="Pending", S="Pending")[status]
                        
                    log.msg(log_msg + " thus we are setting state to: %s"%newstate)
                
                
            else:
                # job has finished
                sleep(15.0)                      # deal with SGE flush bizarreness (files dont flush from remote host immediately. Totally retarded)
                print "ERROR: jobid %s not in jobsummary"%jobid
                print "jobsummary is",jobsummary
                
                # if there is standard error from the qstat command, report that!
                
                
                newstate = "Error"
            if DEBUG:
                print "Job summary:",jobsummary
                
            
            if state!=newstate:
                state=newstate
                #print "Writing state",state
                client_stream.write("%s\n"%state)
                
                # report the full status to the remoteurl
                if remoteurl:
                    if jobid in jobsummary:
                        RemoteInfo(remoteurl,json.dumps(jobsummary[jobid]))
                    else:
                        print "Cannot call RemoteInfo call for job",jobid
                
            if state=="Error":
                #print "CLOSING STREAM"
                client_stream.finish()
                return        

    def new_run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
        modules = [] if not module else [X.strip() for X in module.split(",")]
        
        # send a state
        send_state("Unsubmitted")
        
        # make the submission object
        sub = Submission( submission )
        sub.render(submission_keys)
        
        # this should handle the transport, retries, qsub failures etc.
        jobid = self.submit( sub )
        
        # now the job is submitted, lets remember it
        self.add_running(jobid, {'username':username})
        
        # lets report our id to the caller
        send_id(jobid)
        
        self.main_loop()
        
        # delete finished job
        self.del_running(jobid)

