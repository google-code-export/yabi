import gevent
from twistedweb2 import resource, http_headers, responsecode, http

from TaskManager import Tasks
from Tasklets import tasklets
from yabibe.conf import config


def startup():
    """Start up the TaskManager, so it can go and get some jobs..."""
    print "Starting TaskManager..."
    Tasks.start()
    
    # load up saved tasklets
    print "Loading Tasks..."
    tasklets.load(directory=config.config['backend']['tasklets'])
    print "Tasks loaded"
    
def shutdown():
    """pickle tasks to disk"""
    print "Saving tasklets..."
    
    # we need to make sure any new tasklets that are just starting start up...
    # trying to fix 'requested' shutdown problem.
    Tasks.stop()
    
    # wait for any left overs to start
    gevent.sleep(1.0)
    
    tasklets.save(directory=config.config['backend']['tasklets'])


# the following is used for the yabitests backend start stop tests, to check that serialised tasks are resumed correctly
class TaskManagerResource(resource.Resource):
    """When this resource is hit... tasklets are purged"""
    VERSION=0.2
    addSlash = True
    
    def __init__(self,*args,**kwargs):
        resource.Resource.__init__(self,*args,**kwargs)
    
    def render(self, request):
        #tasklets.purge()
        
        return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, tasklets.debug_json())

class TaskManagerPickleResource(resource.Resource):
    """This is the resource that connects to all the filesystem backends"""
    VERSION=0.2
    addSlash = True
    
    def __init__(self,*args,**kwargs):
        resource.Resource.__init__(self,*args,**kwargs)
    
    def render(self, request):
        tasklets.purge()
        gevent.sleep()
        return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, tasklets.pickle())
    
