import gevent
from twistedweb2 import http, responsecode, http_headers, stream

from ExecConnector import ExecConnector
from SubmissionTemplate import make_script, Submission
from yabibe.conf import config
from yabibe.utils.protocol import ssh


# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "ssh"

DEBUG = False


sshauth = ssh.SSHAuth.SSHAuth()

class SSHConnector(ExecConnector, ssh.KeyStore.KeyStore):    #, ssh.KeyStore.KeyStore):
    ## def __init__(self):
    ##     ExecConnector.__init__(self)
        
    ##     configdir = config.config['backend']['certificates']
    ##     ssh.KeyStore.KeyStore.__init__(self, dir=configdir)
   
    def run(self, yabiusername, submission, submission_data, state, jobid, info, log,creds=None):
        try:
            # preprocess some stuff
            module = submission_data.get('module')
            modules = [] if not module else [X.strip() for X in module.split(",")]

            working = submission_data['working']
            state("Unsubmitted")
            gevent.sleep()
            state("Pending")
            gevent.sleep()

            sub = Submission(submission)
            sub.render(submission_data)

            creds = submission_data.get('creds')
            import sys
            if creds is None:
                creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")
                usercert = self.save_identity(creds['key'])
                pass
            else:
                usercert = None
            password = creds['password']
            
            # handle log setting
            #print >> sys.stderr, config.config
            #if config.config['execution']['logcommand']:
            #    print SCHEMA+" running command: "+command
                
            #if config.config['execution']['logscripts']:
            #    print SCHEMA+" submission script:"
            #    print script_string
                
            pp = ssh.Run.run(usercert,sub.render(),submission_data['username'],submission_data['hostname'],working,port="22",stdout=submission_data['stdout'],stderr=submission_data['stderr'],password=password, modules=modules)

            state("Running")
            gevent.sleep()
            
            while not pp.isDone():
                gevent.sleep()
                
            if pp.exitcode==0:
                # success
                state("Done")
                return

            # error
            DEBUG = True
            if DEBUG:
                print "SSH Job error:"
                print "OUT:",pp.out
                print "ERR:",pp.err
            state("Error")
            return
                    
        except Exception, ee:
            import traceback
            traceback.print_exc()
            state("Error")
            raise
            return
 
