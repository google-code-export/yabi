# -*- coding: utf-8 -*-

import pickle
import os
import dircache
import stackless

from TaskTools import CloseConnections

class Tasklets(object):
    """This is a store for all the tasklets running in back end system. 
    From here they can be saved to disk and reloaded when the server is restarted
    """
    
    def __init__(self):
        self.tasks = []
        
    def add(self, tasklet):
        print "ADD",tasklet
        self.tasks.append(tasklet)
        
    def purge(self):
        """purge dead tasks from the list"""
        for task in self.tasks:
            if task.frame==None:
                self.tasks.remove(task)
        
    def save(self, directory):
        print "TASKS Save",self.tasks
        
        for task in self.tasks:
            # before we pickle it, if we are waiting on a connection in our stack frame, then set it to have failed
            # so that when we are resurrected in the future, the connection will immediately be marked as failed
            task.remove()
            print "task.frame=",task.frame
            print "dir(task.frame)=",dir(task.frame)
            if hasattr(task.frame,"f_back"):
                print "task.frame.f_back=",task.frame.f_back
                print "dir(task.frame.f_back)=",dir(task.frame.f_back)
            print "---"
                
            frame = task.frame 
            while frame and not hasattr(frame,"f_locals"):
                frame = frame.f_back
            
            if frame and 'get_failed' in frame.f_locals:
                print frame.f_locals
                frame.f_locals['get_failed'][0]=True
            print "---"
            
            #task.frame = frame
        
        for task in self.tasks:
            #print "pickling:",task
            pickled_task = pickle.dumps(task,1)
            with open(os.path.join(directory,str(id(task))), 'wb') as fh:
                fh.write(pickled_task) 
            
    def load(self,directory):
        self.tasks=[]
            
        for f in dircache.listdir(directory):
            with open(os.path.join(directory,f), 'rb') as fh:
                data = fh.read()
             
            task = pickle.loads(data)
            #print "LOAD",f,task
            os.unlink(os.path.join(directory,f))
            
            try:
                task.insert()
                self.tasks.append(task)
                print "task",task,"loaded"
            except RuntimeError, re:
                print "TASK is a dead task. skipping...",re
                
    def debug(self):
        
        def dump_obj(obj):
            out = ""
            keys = dir(obj)
            #for key in [K for K in keys if not K.startswith("_")]:
            keys.remove("cstate")
            for key in keys:
                out+=key+": "+str(getattr(obj,key))+"\n"
            return out    
        
        output=""
        for task in self.tasks:
            section=str(task)+"\n"+("="*len(str(task)))+"\n"
            section+=dump_obj(task)
            section+="\n"
            
            output = "%s%s\n"%(output,section)
        return output
    
tasklets = Tasklets()