import gevent
from twistedweb2 import http, responsecode, http_headers, stream

from ExecConnector import ExecConnector
from SubmissionTemplate import make_script
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

class SSHConnector(ExecConnector):    #, ssh.KeyStore.KeyStore):
    ## def __init__(self):
    ##     ExecConnector.__init__(self)
        
    ##     configdir = config.config['backend']['certificates']
    ##     ssh.KeyStore.KeyStore.__init__(self, dir=configdir)
    
    def run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
        # preprocess some stuff
        modules = [] if not module else [X.strip() for X in module.split(",")]
        
        client_stream = stream.ProducerStream()
        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))
        gevent.sleep()
        
        script_string = make_script(submission,working,command,modules,cpus,memory,walltime,yabiusername,username,host,queue, stdout, stderr,tasknum,tasktotal)    
        
        try:
            if DEBUG:
                print "SSH",command,"WORKING:",working,"CREDS passed in:%s"%(creds)    
            client_stream.write("Unsubmitted\n")
            gevent.sleep()
            
            client_stream.write("Pending\n")
            gevent.sleep()
            
            if not creds:
                creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")
        
            usercert = self.save_identity(creds['key'])
            
            # hande log setting
            if config.config['execution']['logcommand']:
                print SCHEMA+" running command: "+command
                
            if config.config['execution']['logscripts']:
                print SCHEMA+" submission script:"
                print script_string
                
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
                print "password:",creds['password']
            pp = ssh.Run.run(usercert,script_string,username,host,working,port="22",stdout=stdout,stderr=stderr,password=creds['password'], modules=modules)
            client_stream.write("Running\n")
            gevent.sleep()
            
            while not pp.isDone():
                gevent.sleep()
                
            if pp.exitcode==0:
                # success
                client_stream.write("Done\n")
                client_stream.finish()
                return
                
            # error
            if DEBUG:
                print "SSH Job error:"
                print "OUT:",pp.out
                print "ERR:",pp.err
            client_stream.write("Error\n")
            client_stream.finish()
            return
                    
        except Exception, ee:
            import traceback
            traceback.print_exc()
            client_stream.write("Error\n")
            client_stream.finish()
            return
        
    def new_run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
        """runs a command through the backend. Callbacks for status/logging.
        """
        modules = [] if not module else [X.strip() for X in module.split(",")]
        script_string = make_script(submission,working,command,modules,cpus,memory,walltime,yabiusername,username,host,queue, stdout, stderr,tasknum,tasktotal)    
        
        state("Pending")
        
        
        
        try:
            if DEBUG:
                print "SSH",command,"WORKING:",working,"CREDS passed in:%s"%(creds)    
            client_stream.write("Unsubmitted\n")
            gevent.sleep()
            
            client_stream.write("Pending\n")
            gevent.sleep()
            
            if not creds:
                creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, "/", credtype="exec")
        
            usercert = self.save_identity(creds['key'])
            
            # hande log setting
            if config.config['execution']['logcommand']:
                print SCHEMA+" running command: "+command
                
            if config.config['execution']['logscripts']:
                print SCHEMA+" submission script:"
                print script_string
                
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
                print "password:",creds['password']
            pp = ssh.Run.run(usercert,script_string,username,host,working,port="22",stdout=stdout,stderr=stderr,password=creds['password'], modules=modules)
            client_stream.write("Running\n")
            gevent.sleep()
            
            while not pp.isDone():
                gevent.sleep()
                
            if pp.exitcode==0:
                # success
                client_stream.write("Done\n")
                client_stream.finish()
                return
                
            # error
            if DEBUG:
                print "SSH Job error:"
                print "OUT:",pp.out
                print "ERR:",pp.err
            client_stream.write("Error\n")
            client_stream.finish()
            return
                    
        except Exception, ee:
            import traceback
            traceback.print_exc()
            client_stream.write("Error\n")
            client_stream.finish()
            return
        
