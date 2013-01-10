import json
import gevent
import random
import os
import pickle

from yabibe.utils.parsers import parse_url

import traceback
from yabibe.exceptions import BlockingException

DEBUG = False

class TaskFailed(Exception):
    pass

class Task(object):
    def __init__(self, json=None):
        self.blocked_stage = None
        
        # stage in file
        if json:
            self.load_json(json)
        
    def load_json(self, json, stage=0):
        self.json = json
        
        # check json is okish
        self._sanity_check()
                
        self.taskid = json['taskid']
        self.statusurl = json['statusurl']
        self.errorurl = json['errorurl']
        self.yabiusername = json['yabiusername']
                        
        self.submission = json['exec']['submission']
                        
        self.setup_lambdas()
        
        # stage keeps track of where we are in completing the tasklet, so if we need to restart we can skip
        # parts that are already completed
        self.stage = stage
        
    def setup_lambdas(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections
        # shortcuts for our status and log calls
        self.status = lambda x: Status(self.statusurl,x)
        self.log = lambda x: Log(self.errorurl,x)
        
    def get_pickle_data(self):
        #print
        #print dir(self)
        #for key in dir(self):
            #print key,"=>",getattr(self,key)
        #print
        
        keynames = [ 'blocked_stage', 'errorurl', 'exec_status', 'json', 'outdir', 'outuri', 'stage', 'statusurl', 'submission', 'taskid', 'yabiusername' ]
        
        output = {}
        for key in keynames:
            if hasattr(self,key):
                output[key] = getattr(self,key)
        
        return output
        
    def set_from_pickle_data(self, data):
        for key in data.keys():
            setattr(self,key,data[key])
    
    def run(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections
        try:
            self.main()
        except BlockingException, be:
            # this is to deal with a problem that is temporary and leads to a blocked status
            self._blocked()
            traceback.print_exc()
            self.log("Task moved into blocking state: %s"%be)
            self.status("blocked")
            
        except GETFailure, gf:
            if '503' in gf.message[1]:
                # blocked!
                #print "BLOCKED"
                self._blocked()
                traceback.print_exc()
                self.log("Task moved into blocking state: %s"%gf)
                self.status("blocked")
            else:
                #print "ERROR"
                self._errored()
                traceback.print_exc()
                self.log("Task raised GETFailure: %s"%gf)
                self.status("error")
            
        except Exception, e:
            self._errored()
            traceback.print_exc()
            self.log("Task raised exception: %s"%e)
            self.status("error")
    
    
    def _next_stage(self):
        """Move to the next stage of the tasklet"""
        self.stage += 1
        
    def _set_stage(self, stage):
        self.stage = stage
        
    def _end_stage(self):
        """Mark as ended"""
        self.stage = -1
        
    def _errored(self):
        self.stage = -2

    def _blocked(self):
        # move to blocked. keep the old stage stored
        self.blocked_stage = self.stage
        self.stage = -3
        
    def unblock(self):
        # for a job that is sitting in blocking, move it back out and into its last execution stage
        assert self.blocked_stage != None, "Trying to unblock a task that was never blocked"
        self.stage = self.blocked_stage
        self.blocked_stage = None
        
    def finished(self):
        return self.stage == -1
        
    def errored(self):
        return self.stage == -2

    def blocked(self):
        return self.stage == -3

    def _sanity_check(self):
        # sanity check...
        for key in ['errorurl','exec','stagein','stageout','statusurl','taskid','yabiusername']:
            assert key in self.json, "Task JSON description is missing a vital key '%s'"%key
        
        # check the exec section
        for key in ['backend', 'command', 'fsbackend', 'workingdir', 'submission']:
            assert key in self.json['exec'], "Task JSON description is missing a vital key inside the 'exec' section. Key name is '%s'"%key
           
class NullBackendTask(Task):
    def load_json(self, json, stage=0):
        Task.load_json(self, json, stage)
        
        # check if exec scheme is null backend. If this is the case, we need to run our special null backend tasklet
        scheme, address = parse_url(json['exec']['backend'])
        assert scheme.lower() == "null"
    
    def main(self):
        if self.stage == 0:
            self.log("null backend... skipping task and copying files")
           
            self.log("making stageout directory %s"%self.json['stageout'])
            self.make_stageout()
        
            self._next_stage()
        
        if self.stage == 1:
            self.status("stagein")
            self.stage_in_files()

            self._next_stage()

        if self.stage == 2:
            self.status("complete")              # null backends are always marked complete

            self._end_stage()

    def make_stageout(self):
        from TaskTools import Mkdir

        stageout = self.json['stageout']
        
        if DEBUG:
            print "STAGEOUT:",stageout
        try:
            Mkdir(stageout, yabiusername=self.yabiusername)
        except GETFailure, error:
            raise BlockingException("Make directory failed: %s"%error.message[2])
        
    def stage_in_files(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        dst = self.json['stageout']
        status = self.status
        log = self.log
        
        # for each stagein, copy to stageout NOT the stagein destination
        for copy in self.json['stagein']:
            src = copy['src']
            method = copy['method'] if 'method' in copy else 'copy'                     # copy or link
            
            # sanity check method and fail back to copy if needed
            if method=='link' or method=='lcopy':
                sscheme,sparse = parse_url(src)
                dscheme,dparse = parse_url(dst)
                if sscheme!=dscheme or sparse.hostname!=dparse.hostname or sparse.username!=dparse.username or sparse.port!=dparse.port:
                    # fall back to copy
                    method='copy'
            
            # check that destination directory exists.
            scheme,address = parse_url(dst)
            
            directory, file = os.path.split(address.path)
            remotedir = scheme+"://"+address.netloc+directory
            if DEBUG:
                print "CHECKING remote:",remotedir
            try:
                listing = List(remotedir, yabiusername=self.yabiusername)
                if DEBUG:
                    print "list result:", listing
            except Exception, error:
                # directory does not exist
                # make dir
                try:
                    Mkdir(remotedir, yabiusername=self.yabiusername)
                except GETFailure, gf:
                    raise BlockingException("Make directory failed: %s"%gf.message[2])
            
            if src.endswith("/"):
                log("RCopying %s to %s..."%(src,dst))
                try:
                    RCopy(src,dst, yabiusername=self.yabiusername,log_callback=log)
                    log("RCopying %s to %s Success"%(src,dst))
                except GETFailure, error:
                    # error copying!
                    print "TASK[%s]: RCopy %s to %s Error!"%(self.taskid,src,dst)
                    status("error")
                    log("RCopying %s to %s failed: %s"%(src,dst, error))
                    return              # finish task
            
                print "TASK[%s]: RCopy %s to %s Success!"%(self.taskid,src,dst)
            else: 
                if method=='copy' or method=='lcopy':
                    self.log("Copying %s to %s using method %s..."%(src,dst,method))
                    try:
                        SmartCopy(method,src,dst, yabiusername=self.yabiusername,log_callback=log)
                        self.log("Copying %s to %s Success"%(src,dst))
                    except GETFailure, error:
                        if "503" in error.message[1]:
                            raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                        # error copying!
                        print "TASK[%s]: Copy %s to %s Error!"%(self.taskid,src,dst)
                        self.status("error")
                        self.log("Copying %s to %s failed: %s"%(src,dst, error))
                        
                        raise TaskFailed("Stage In failed")
            
                    print "TASK[%s]: Copy %s to %s Success!"%(self.taskid,src,dst)
                elif method=='link':
                    self.log("Linking %s to point to %s"%(dst,src))
                    try:
                        Ln(src,dst,yabiusername=self.yabiusername,log_callback=log)
                        self.log("Linking %s to point to %s success"%(dst,src))
                    except GETFailure, error:
                        if "503" in error.message[1]:
                            raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                        # error copying!
                        print "TASK[%s]: Link %s to point to %s Error!"%(self.taskid,dst,src)
                        self.status("error")
                        self.log("Linking %s to point to %s failed: %s"%(dst, src, error))
                        
                        raise TaskFailed("Stage In failed")
                        
                else:
                    raise TaskFailed("Stage in failed: unknown stage in method %s"%method)
            
class MainTask(Task):
    STAGEIN = 0
    MKDIR = 1
    EXEC = 2
    STAGEOUT = 3
    CLEANUP = 4
    
    def __init__(self, json=None):
        Task.__init__(self,json)
        
        # for resuming started backend execution jobs
        self._jobid = None
        
        self._failed = False
    
    def load_json(self, json, stage=0):
        Task.load_json(self, json, stage)
        
        # check if exec scheme is null backend. If this is the case, we need to run our special null backend tasklet
        scheme, address = parse_url(json['exec']['backend'])
        assert scheme.lower() != "null"
           
    def main(self):
        
        if self.stage == self.STAGEIN:
            self.status("stagein")
            self.stage_in_files()
                
            self._next_stage()
                
        if self.stage == self.MKDIR:
            # make our working directory
            self.status("mkdir")
            self.outuri, self.outdir = self.mkdir()                     # make the directories we are working in
        
            self._next_stage()
        
        if self.stage == self.EXEC:
            # now we are going to run the job
            self.status("exec")
            try:
                if self._jobid is None:
                    # start a fresh taskjob
                    if DEBUG:
                        print "Executing fresh:",self._jobid
                    self.execute(self.outdir)                        # TODO. implement picking up on this exec task without re-running it??
            
                else:
                    # reconnect with this taskjob
                    if DEBUG:
                        print "Reconnecting with taskjob:",self._jobid
                    self.resume(self.outdir)
            
            except TaskFailed, ex:
                # task has errored. Lets stage out any remnants.
                self._failed = True
                self.log('Task has failed. Staging out any job remnants...')
            
            self._set_stage(self.STAGEOUT)
 
        if self.stage == self.STAGEOUT:
            # stageout
            self.log("Staging out results")
            self.status('stageout')
        
            # recursively copy the working directory to our stageout area
            self.log("Staging out remote %s to %s..."%(self.outdir,self.json['stageout']))
        
            # make sure we have the stageout directory
            self.log("making stageout directory %s"%self.json['stageout'])
            self.make_stageout()
        
            self.stageout(self.outuri)
        
            self._next_stage()
            
        if self.stage == self.CLEANUP:
        
            # cleanup
            self.status("cleaning")
            self.log("Cleaning up job...")
        
            self.cleanup()
        
            if self._failed:
                self.log("Task failed")
                self.status("error")
            else:
                self.log("Task completed successfully")
                self.status("complete")
                
            self._end_stage()
        
    def stage_in_files(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        task = self.json
        for copy in task['stagein']:
            src = copy['src']
            dst = copy['dst']
            method = copy['method'] if 'method' in copy else 'copy'                     # copy or link
            
            # check that destination directory exists.
            scheme,address = parse_url(dst)
            
            directory, file = os.path.split(address.path)
            remotedir = scheme+"://"+address.netloc+directory
            if DEBUG:
                print "CHECKING remote:",remotedir
            try:
                listing = List(remotedir, yabiusername=self.yabiusername)
                if DEBUG:
                    print "list result:", listing
            except Exception, error:
                # directory does not exist
                #make dir
                try:
                    Mkdir(remotedir, yabiusername=self.yabiusername)
                except GETFailure, gf:
                    raise BlockingException("Make directory failed: %s"%gf.message[2])
            
            if method=='copy' or method=='lcopy':
                self.log("Copying %s to %s using method %s..."%(src,dst,method))
                try:
                    SmartCopy(method, src,dst, yabiusername=self.yabiusername,log_callback=self.log)
                    self.log("Copying %s to %s Success"%(src,dst))
                except GETFailure, error:
                    if "503" in error.message[1]:
                        raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                    # error copying!
                    print "TASK[%s]: Copy %s to %s Error!"%(self.taskid,src,dst)
                    self.status("error")
                    self.log("Copying %s to %s failed: %s"%(src,dst, error))
                    
                    raise TaskFailed("Stage In failed")
        
                print "TASK[%s]: Copy %s to %s Success!"%(self.taskid,src,dst)
            elif method=='link':
                self.log("Linking %s to point to %s"%(dst,src))
                try:
                    Ln(src,dst,yabiusername=self.yabiusername,log_callback=self.log)
                    self.log("Linking %s to point to %s success"%(dst,src))
                except GETFailure, error:
                    if "503" in error.message[1]:
                        raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                    # error copying!
                    print "TASK[%s]: Link %s to point to %s Error!"%(self.taskid,dst,src)
                    self.status("error")
                    self.log("Linking %s to point to %s failed: %s"%(dst, src, error))
                    
                    raise TaskFailed("Stage In failed")
                    
            else:
                raise TaskFailed("Stage in failed: unknown stage in method %s"%method)
                
        
    def mkdir(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        task=self.json
        
        # get our credential working directory. We lookup the execution backends auth proxy cache, and get the users home directory from that
        # this comes from their credentials.
        scheme, address = parse_url(task['exec']['backend'])
        usercreds = UserCreds(self.yabiusername, task['exec']['backend'], credtype="exec")
        workingdir = task['exec']['workingdir']
        
        assert address.path=="/", "Error. JSON[exec][backend] has a path. Execution backend URI's must not have a path (path is %s)"%address.path 
        
        if DEBUG:
            print "USERCREDS",usercreds
        
        fsbackend = task['exec']['fsbackend']
        
        outputuri = fsbackend + ("/" if not fsbackend.endswith('/') else "") + "output/"
        outputdir = workingdir + ("/" if not workingdir.endswith('/') else "") + "output/"
        
        try:
            Mkdir(outputuri, yabiusername=self.yabiusername)
        except GETFailure, error:
            if "503" in error.message[1]:
                    raise                               # reraise a blocking error so our top level catcher will catch it and block the task
            # error making directory
            print "TASK[%s]:Mkdir failed!"%(self.taskid)
            self.status("error")
            self.log("Making working directory of %s failed: %s"%(outputuri,error))
            
            raise TaskFailed("Mkdir failed")
        
        return outputuri,outputdir
        
    def make_stageout(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        stageout = self.json['stageout']
        
        if DEBUG:
            print "STAGEOUT:",stageout
        try:
            Mkdir(stageout, yabiusername=self.yabiusername)
        except GETFailure, error:
            raise BlockingException("Make directory failed: %s"%error.message[2])
    
    def do(self, outputdir, callfunc):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        task=self.json
        retry=True
        while retry:
            retry=False
            
            try:
                self.exec_status = []
                
                # callback for job execution status change messages
                def _task_status_change(line):
                    """Each line that comes back from the webservice gets passed into this callback"""
                    line = line.strip()
                    self.log("Remote execution backend sent status message: %s"%(line))
                    status = line.lower()
                    self.exec_status.append(status)
                    self.status("exec:%s"%(status))
                    
                def _task_id_change(value):
                    # check for job id number
                    self._jobid = value
                
                # submit the job to the execution middle ware
                self.log("Submitting to %s command: %s"%(task['exec']['backend'],task['exec']['command']))
                
                try:
                    cull_trailing_slash = lambda s: s[:-1] if (len(s) and s[-1]=='/') else s
                    uri = cull_trailing_slash(task['exec']['backend'])+outputdir
                    
                    # create extra parameter list
                    extras = {}
                    for key in [ 'cpus', 'jobtype', 'memory', 'module', 'queue', 'walltime', 'tasknum', 'tasktotal' ]:
                        if key in task['exec'] and task['exec'][key]:
                            extras[key]=task['exec'][key]
                    
                    submission_data = {
                        'command':task['exec']['command'],
                        'stdout':'STDOUT.txt',
                        'stderr':'STDERR.txt'
                    }
                    submission_data.apply(extras)
                    
                    #print "callfunc is",callfunc
                    #callfunc(uri, command=task['exec']['command'], remote_info=task['remoteinfourl'], submission=self.submission, stdout="STDOUT.txt",stderr="STDERR.txt", callbackfunc=_task_status_change, yabiusername=self.yabiusername, **extras)     # this blocks untill the command is complete. or the execution errored
                    callfunc(uri, self.submission, submission_data, self.yabiusername, _task_status_change, _task_id_change)
                    
                    unfinished = set(("pending", "unsubmitted", "running"))
                    received_so_far = set(self.exec_status)
                    # Loop while all statuses received so far are unfinished
                    while len(received_so_far - unfinished) == 0:
                        gevent.sleep(1.0)
                        received_so_far = set(self.exec_status)

                    if filter(lambda s: 'error' in s, self.exec_status):
                        print "TASK[%s]: Execution failed!"%(self.taskid)
                        self.status("error")
                        self.log("Execution of %s on %s failed with status %s"%(task['exec']['command'],task['exec']['backend'],self.exec_status[0]))
                        
                        # finish task
                        raise TaskFailed("Execution failed")
                    else:
                        self.log("Execution finished")
                except GETFailure, error:
                    if "503" in error.message[1]:
                        raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                    # error executing
                    print "TASK[%s]: Execution failed!"%(self.taskid)
                    self.status("error")
                    self.log("Execution of %s on %s failed: %s"%(task['exec']['command'],task['exec']['backend'],error))
                    
                    # finish task
                    raise TaskFailed("Execution failed")
                
            except CloseConnections, cc:
                retry=True
                
            gevent.sleep(1.0)
        
    def execute(self, outputdir):
        from TaskTools import  Exec
        return self.do(outputdir, Exec)

    def resume(self, outputdir):
        # curry resume into the do method
        from TaskTools import Resume
        return self.do(outputdir, lambda *x, **y: Resume( self._jobid, *x, **y))
        
    def stageout(self,outputuri):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        task=self.json
        if DEBUG:
            print "STAGEOUT:",task['stageout'],"METHOD:",task['stageout_method']
        
        if task['stageout_method']=='copy':   
            try:
                if DEBUG:
                    print "Mkdir(",task['stageout'],",",self.yabiusername,")"
                Mkdir(task['stageout'], yabiusername=self.yabiusername)
            except GETFailure, error:
                pass
            
            try:
                if DEBUG:
                    print "RCopy(",outputuri,",",task['stageout'],",",self.yabiusername,")"
                RCopy(outputuri,task['stageout'],yabiusername=self.yabiusername,contents=True,log_callback=self.log)
                self.log("Files successfuly staged out")
            except GETFailure, error:
                if "503" in error.message[1]:
                        raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                # error executing
                print "TASK[%s]: Stageout failed!"%(self.taskid)
                self.status("error")
                if DEBUG:
                    self.log("Staging out remote %s to %s failed... \n%s"%(outputuri,task['stageout'],traceback.format_exc()))
                else:
                    self.log("Staging out remote %s to %s failed... %s"%(outputuri,task['stageout'],error))
                
                # finish task
                raise TaskFailed("Stageout failed")
        elif task['stageout_method']=='lcopy':
            try:
                Mkdir(task['stageout'], yabiusername=self.yabiusername)
            except GETFailure, error:
                pass
            
            try:
                SmartCopy('lcopy',outputuri,task['stageout'],yabiusername=self.yabiusername,log_callback=self.log,recurse=True)
                self.log("Files successfuly staged out")
            except GETFailure, error:
                if "503" in error.message[1]:
                        raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                # error executing
                print "TASK[%s]: Stageout failed!"%(self.taskid)
                self.status("error")
                if DEBUG:
                    self.log("Staging out remote %s to %s failed... \n%s"%(outputuri,task['stageout'],traceback.format_exc()))
                else:
                    self.log("Staging out remote %s to %s failed... %s"%(outputuri,task['stageout'],error))
                
                # finish task
                raise TaskFailed("Stageout failed")
        else:
            raise TaskFailed("Unsupported stageout method %s"%task['stageout_method'])
            
    def cleanup(self):
        from TaskTools import Copy, Ln, LCopy, RCopy, SmartCopy, Sleep, Log, Status, Exec, Resume, Mkdir, Rm, List, UserCreds, GETFailure, CloseConnections

        task=self.json
        # cleanup working dir
        for copy in self.json['stagein']:
            dst_url = copy['dst']
            self.log("Deleting %s..."%(dst_url))
            try:
                if DEBUG:
                    print "RM1:",dst_url
                Rm(dst_url, yabiusername=self.yabiusername, recurse=True)
            except GETFailure, error:
                if "503" in error.message[1]:
                    raise                               # reraise a blocking error so our top level catcher will catch it and block the task
                # error deleting. This is logged but is non fatal
                print "TASK[%s]: Delete %s Error!"%(self.taskid, dst_url)
                #status("error")
                self.log("Deleting %s failed: %s"%(dst_url, error))
                
                # finish task
                raise TaskFailed("Cleanup failed")
            
        dst_url = task['exec']['fsbackend']
        self.log("Deleting containing folder %s..."%(dst_url))
        try:
            if DEBUG:
                print "RM2:",dst_url
            Rm(dst_url, yabiusername=self.yabiusername, recurse=True)
        except GETFailure, error:
            if "503" in error.message[1]:
                    raise                               # reraise a blocking error so our top level catcher will catch it and block the task
            # error deleting. This is logged but is non fatal
            print "TASK[%s]: Delete %s Error!"%(self.taskid, dst_url)
            #status("error")
            self.log("Deleting %s failed: %s"%(dst_url, error))
            
            # finish task
            raise TaskFailed("Cleanup failed")
                