"""Web2 style resource that is gonna serve our children"""
from twistedweb2 import resource, http_headers, responsecode, http
import os, sys

##
## Filesystem resources
##
from fs.resource import FSResource

# backends

from fs.connector.SSHFilesystem import SSHFilesystem
from fs.connector.S3Filesystem import S3Filesystem
from fs.connector.LocalFilesystem import LocalFilesystem

##
## Execution resources
##
from ex.resource import ExecResource

# backends
from ex.connector.SGEConnector import SGEConnector
from ex.connector.TorqueConnector import TorqueConnector
from ex.connector.SSHConnector import SSHConnector
from ex.connector.SSHTorqueConnector import SSHTorqueConnector
from ex.connector.SSHPbsproConnector import SSHPbsproConnector
from ex.connector.SSHSGEConnector import SSHSGEConnector
from ex.connector.LocalConnector import LocalConnector
from ex.connector.ExplodingConnector import ExplodingConnector

# taskmanager debug
from TaskManager import TaskManagerResource, TaskManagerPickleResource

VERSION = 0.2
class BaseResource(resource.PostableResource):
    """This is the baseclass for out "/" HTTP resource. It does nothing but defines the various children.
    It is also the location where you hook in you tools, or wsgi apps."""
    addSlash = True
    
    def __init__(self, *args, **kw):
        resource.PostableResource.__init__(self, *args, **kw)
        
        ##
        ## our handlers
        ##
        self.fs = self.child_fs = FSResource()
        self.ex = self.child_exec = ExecResource()
        
        #  debug for taskmanager
        self.child_debug = TaskManagerResource()
        self.child_pickle = TaskManagerPickleResource()
        
    def LoadExecConnectors(self, quiet=False):
        self.child_exec.LoadConnectors(quiet)
        
    def LoadFSConnectors(self, quiet=False):
        self.child_fs.LoadConnectors(quiet)
        
    def LoadConnectors(self, quiet=False):
        self.LoadExecConnectors(quiet)
        self.LoadFSConnectors(quiet)
        
    def render(self, ctx):
        """Just returns a helpful text string"""
        return http.Response(responsecode.OK,
                        {'content-type': http_headers.MimeType('text', 'plain')},
                         "Twisted Yabi Core: %s\n"%VERSION)
                         
    def shutdown(self):
        """send signal to each backend that needs info to be written to disk on shutdown.
        at the moment this is only execution backends that are capable of job resumption
        """
        self.child_exec.shutdown()
        
    def startup(self):
        """startup each backend that needs it"""
        self.child_exec.startup()

base = BaseResource()
