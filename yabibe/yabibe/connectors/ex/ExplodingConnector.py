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
    def run(self, yabiusername, working, submission, submission_data, state, jobid, info, log):
        gevent.sleep()
        
        times = random.choice(possible_delay_sets)

        for delay, message in times:
            sleep(delay)
            state(message)
        
        return
        
