from twisted.web import client
from twisted.internet import reactor
import json
import stackless
import weakref
import random
import os

from utils.parsers import parse_url

from TaskTools import Copy, RCopy, Sleep, Log, Status, Exec, Mkdir, Rm, List, UserCreds, GETFailure

# if debug is on, full tracebacks are logged into yabiadmin
DEBUG = True

import traceback

class TaskManager(object):
    TASK_HOST = "localhost"
    TASK_PORT = int(os.environ['PORT']) if 'PORT' in os.environ else 8000
    TASK_URL = "/yabiadmin/engine/task/"
    
    JOBLESS_PAUSE = 5.0                 # wait this long when theres no more jobs, to try to get another job
    JOB_PAUSE = 0.0                     # wait this long when you successfully got a job, to get the next job
    
    def __init__(self):
        self.pausechannel = stackless.channel()
    
        self._tasks=weakref.WeakKeyDictionary()                  # keys are weakrefs. values are remote working directory
    
    def start(self):
        """Begin the task manager tasklet. This tasklet continually pops tasks from yabiadmin and sets them up for running"""
        self.runner_thread = stackless.tasklet(self.runner)
        self.runner_thread.setup()
        self.runner_thread.run()
        
    def runner(self):
        """The green task that starts up jobs"""
        while True:                 # do forever.
            self.get_next_task()
            
            # wait for this task to start or fail
            Sleep(self.pausechannel.receive())
        
    def start_task(self, data):
        taskdescription=json.loads(data)
        
        print "starting task:",taskdescription['taskid']
        
        # make the task and run it
        tasklet = stackless.tasklet(self.task)
        tasklet.setup(taskdescription)
        tasklet.run()
        
        # mark in the weakrefdict that this tasklet exists
        self._tasks[tasklet] = None
        
        # task successfully started. Lets try and start anotherone.
        self.pausechannel.send(self.JOB_PAUSE)
         
         
    def get_next_task(self):
        host,port,TASK_URL = self.TASK_HOST,self.TASK_PORT,self.TASK_URL
        if 'YABIADMIN' in os.environ:
            pre,post = os.environ['YABIADMIN'].split('/',1)
            post="/"+post
            if ':' in pre:
                host,port=pre.split(":")
                port=int(port)
            else:
                host=pre
                
            TASK_URL = "/engine/task/"
                
        useragent = "YabiExec/0.1"
        
        factory = client.HTTPClientFactory(
            TASK_URL,
            agent = useragent
            )
        factory.noisy = True
        reactor.connectTCP(host, port, factory)
        
        # now if the page fails for some reason. deal with it
        def _doFailure(data):
            #print "No more jobs. Sleeping for",self.JOBLESS_PAUSE
            # no more tasks. we should wait for the next task.
            self.pausechannel.send(self.JOBLESS_PAUSE)
            
        return factory.deferred.addCallback(self.start_task).addErrback(_doFailure)
        
    def task(self,task, taskrunner=None):
        """Entry point for Task tasklet"""
        taskid = task['taskid']
        if not taskrunner:
            taskrunner=self.task_mainline
        try:
            return taskrunner(task)
        except Exception, exc:
            print "TASK[%s] raised uncaught exception: %s"%(taskid,exc)
            traceback.print_exc()
            if DEBUG:
                Log(task['errorurl'],"Raised uncaught exception: %s"%(traceback.format_exc()))
            else:
                Log(task['errorurl'],"Raised uncaught exception: %s"%(exc))
            Status(task['statusurl'],"error")
        
    def task_mainline(self, task):
        """Our top down greenthread code"""
        print "=========JSON============="
        print task
        print "=========================="
        
        # stage in file
        taskid = task['taskid']
        
        statusurl = task['statusurl']
        errorurl = task['errorurl']
        
        # shortcuts for our status and log calls
        status = lambda x: Status(statusurl,x)
        log = lambda x: Log(errorurl,x)
        
        status("stagein")
        for copy in task['stagein']:
            print "COPY:",copy
            #src_url = "%s/%s%s"%(copy['srcbackend'],task['yabiusername'],copy['srcpath'])
            #dst_url = "%s/%s%s"%(copy['dstbackend'],task['yabiusername'],copy['dstpath'])
            
            src = copy['src']
            dst = copy['dst']
            
            log("Copying %s to %s..."%(src,dst))
            try:
                Copy(src,dst)
                log("Copying %s to %s Success"%(src,dst))
            except GETFailure, error:
                # error copying!
                print "TASK[%s]: Copy %s to %s Error!"%(taskid,src,dst)
                status("error")
                log("Copying %s to %s failed: %s"%(src,dst, error))
                return              # finish task
           
            print "TASK[%s]: Copy %s to %s Success!"%(taskid,src,dst)
        
        # get our credential working directory. We lookup the execution backends auth proxy cache, and get the users home directory from that
        # this comes from their credentials.
        
        scheme, address = parse_url(task['exec']['backend'])
        usercreds = UserCreds(scheme, address.username, address.hostname)
        #homedir = usercreds['homedir']
        workingdir = address.path
        
        print "USERCREDS",usercreds
                
        # make our working directory
        status("mkdir")
        
        fsscheme, fsaddress = parse_url(task['exec']['fsbackend'])
        mkuri = fsscheme+"://"+fsaddress.username+"@"+fsaddress.hostname+workingdir
        
        print "Making directory",mkuri
        self._tasks[stackless.getcurrent()]=workingdir
        try:
            Mkdir(mkuri)
        except GETFailure, error:
            # error making directory
            print "TASK[%s]:Mkdir failed!"%(taskid)
            status("error")
            log("Making working directory of %s failed: %s"%(mkuri,error))
            return 
        
        # now we are going to run the job
        status("exec")
        
        # callback for job execution status change messages
        def _task_status_change(line):
            """Each line that comes back from the webservice gets passed into this callback"""
            line = line.strip()
            print "_task_status_change(",line,")"
            log("Remote execution backend changed status to: %s"%(line))
            status("exec:%s"%(line.lower()))
        
        # submit the job to the execution middle ware
        log("Submitting to %s command: %s"%(task['exec']['backend'],task['exec']['command']))
        
        try:
            Exec(task['exec']['backend'], command=task['exec']['command'], stdout="STDOUT.txt",stderr="STDERR.txt", callbackfunc=_task_status_change)                # this blocks untill the command is complete.
            log("Execution finished")
        except GETFailure, error:
            # error executing
            print "TASK[%s]: Execution failed!"%(taskid)
            status("error")
            log("Execution of %s on %s failed: %s"%(task['exec']['command'],task['exec']['backend'],error))
            return              # finish task
        
        # stageout
        log("Staging out results")
        status('stageout')
        
        # recursively copy the working directory to our stageout area
        log("Staging out remote %s to %s..."%(workingdir,task['stageout']))
        
        # make sure we have the stageout directory
        log("making stageout directory %s"%task['stageout'])
        print "STAGEOUT:",task['stageout']
        try:
            Mkdir(task['stageout'])
        except GETFailure, error:
            pass
        
        try:
            RCopy(mkuri,task['stageout'])
            log("Files successfuly staged out")
        except GETFailure, error:
            # error executing
            print "TASK[%s]: Stageout failed!"%(taskid)
            status("error")
            if DEBUG:
                log("Staging out remote %s to %s failed... \n%s"%(mkuri,task['stageout'],traceback.format_exc()))
            else:
                log("Staging out remote %s to %s failed... %s"%(mkuri,task['stageout'],error))
            return              # finish task
        
        # cleanup
        status("cleaning")
        log("Cleaning up job...")
        
        # cleanup working dir
        for copy in task['stagein']:
            dst_url = mkuri
            log("Deleting %s..."%(dst_url))
            try:
                print "RM1:",dst_url
                Rm(dst_url, recurse=True)
            except GETFailure, error:
                # error copying!
                print "TASK[%s]: Delete %s Error!"%(taskid, dst_url)
                status("error")
                log("Deleting %s failed: %s"%(dst_url, error))
                return              # finish task
            
        ## cleanup working dir
        #try:
            #print "RM2:",mkuri
            #Rm(mkuri, recurse=True)
            #log("Stageout directory %s deleted"%mkuri)
        #except GETFailure, error:
            ## error copying!
            #print "TASK[%s]: Delete %s Error!"%(taskid, mkuri),error
            #status("error")
            #if DEBUG:
                #log("Deleting %s failed: %s"%(mkuri, traceback.format_exc()))
            #else:
                #log("Deleting %s failed: %s"%(mkuri, error))
            #return  
        
        log("Job completed successfully")
        status("complete")
        
        