import random

import gevent
from twistedweb2 import http, responsecode, http_headers, stream

from ExecConnector import ExecConnector
from yabibe.utils.geventtools import sleep


# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "explode"

DEBUG = False


possible_delay_sets = [
         # normal   
         [   
            (10.0, "Unsubmitted"),
            (10.0, "Pending"),
            (10.0, "Running"),
            (30.0, "Error")
         ],
         
         # no pending
         [   
            (10.0, "Unsubmitted"),
            (10.0, "Running"),
            (30.0, "Error")
         ],
         
         # no running
         [   
            (10.0, "Unsubmitted"),
            (10.0, "Pending"),
            (30.0, "Error")
         ],
         
         # straight to error
         [   
            (10.0, "Unsubmitted"),
            (30.0, "Error")
         ],
         
         # nothing but error
         [   
            (10.0, "Error")
         ],
         
         # speed run
         [   
            (0.1, "Unsubmitted"),
            (0.1, "Pending"),
            (0.1, "Running"),
            (0.1, "Error")
         ],
         
         # speed bomb
         [
            (0, "Unsubmitted"),
            (0, "Pending"),
            (0, "Running"),
            (0, "Error")
         ]
    ]
             
         
class ExplodingConnector(ExecConnector):    
    def run(self, yabiusername, creds, command, working, scheme, username, host, remoteurl, channel, submission, stdout="STDOUT.txt", stderr="STDERR.txt", walltime=60, memory=1024, cpus=1, queue="testing", jobtype="single", module=None,tasknum=None,tasktotal=None):
        client_stream = stream.ProducerStream()
        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))
        gevent.sleep()
        
        times = random.choice(possible_delay_sets)

        print "Exploding Connector: command %s, remoteurl %s, delay_set %s" % (command, remoteurl, str(times))
        
        for delay, message in times:
            sleep(delay)
            print "Exploding Connector: remoteurl %s, message %s" % (remoteurl, message)
            client_stream.write("%s\r\n"%message)
        
        client_stream.finish()
        return
        