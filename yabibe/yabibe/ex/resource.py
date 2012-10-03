# -*- coding: utf-8 -*-
### BEGIN COPYRIGHT ###
#
# (C) Copyright 2011, Centre for Comparative Genomics, Murdoch University.
# All rights reserved.
#
# This product includes software developed at the Centre for Comparative Genomics 
# (http://ccg.murdoch.edu.au/).
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, YABI IS PROVIDED TO YOU "AS IS," 
# WITHOUT WARRANTY. THERE IS NO WARRANTY FOR YABI, EITHER EXPRESSED OR IMPLIED, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT OF THIRD PARTY RIGHTS. 
# THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF YABI IS WITH YOU.  SHOULD 
# YABI PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR
# OR CORRECTION.
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, OR AS OTHERWISE AGREED TO IN 
# WRITING NO COPYRIGHT HOLDER IN YABI, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR 
# REDISTRIBUTE YABI AS PERMITTED IN WRITING, BE LIABLE TO YOU FOR DAMAGES, INCLUDING 
# ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE 
# USE OR INABILITY TO USE YABI (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR 
# DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES 
# OR A FAILURE OF YABI TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER 
# OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
# 
### END COPYRIGHT ###
# -*- coding: utf-8 -*-
"""Our twisted filesystem server resource"""

from twistedweb2 import resource, http_headers, responsecode, http, server
from twisted.internet import defer, reactor

import weakref
import sys, os

from ExecRunResource import ExecRunResource
from ExecResumeResource import ExecResumeResource
from ExecInfoResource import ExecInfoResource
from utils.BackendResource import BackendResource

class ExecResource(resource.Resource, BackendResource):
    """This is the resource that connects to all the filesystem backends"""
    VERSION=0.2
    addSlash = True
    
    def __init__(self,*args,**kwargs):
        BackendResource.__init__(self,*args,**kwargs)
        
    def LoadConnectors(self, quiet=False):
        """Load all the backend connectors into our backends"""
        import connector
        return BackendResource.LoadConnectors(self,connector,'ExecConnector','exec', quiet=quiet)
  
    def render(self, request):
        # break our request path into parts
        parts = request.path.split("/")
        assert parts[0]=="", "Expected a leading '/' on the request path"
        
        backendname = parts[2]
        
        # no name? just status
        if not backendname and len(parts)==3:
            # status page
            page = "Yabi Exec Connector Resource Version: %s\n"%self.VERSION
            page += "Available backends: "+", ".join(self.backends.keys())
            page += "\n\n"
            return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, page)
        
        # check for backend name
        if backendname not in self.backends:
            return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found"%backendname)
        
        backend = self.backends[backendname]
        page = "Hello, %s!"%backend
        
        return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, page)
    
    def locateChild(self, request, segments):
        # return our local file resource for these segments
        if segments[0]=="run":
            return ExecRunResource(request,segments,fsresource = self), []
        elif segments[0]=="resume":
            return ExecResumeResource(request,segments,fsresource = self), []
        elif segments[0]=="info":
            return ExecInfoResource(request,segments,fsresource = self), []
            
        
        return resource.Resource.locateChild(self,request,segments)
        
    def run(self, uri, command, submission, yabiusername, remote_info_url=None):
        """ an optional remote info url can be submitted. If it is submitted with a job, then everytime the status of this job changes,
        this sends a POST to the url with a json key/value set with info on the backend task
        """
        
        if DEBUG:
            print "RUN:",command

        scheme, address = parse_url(uri)
        
        if not hasattr(address,"username"):
            raise Exception, "No username provided in uri\n"
        
        username = address.username
        path = address.path
        hostname = address.hostname
        
        basepath, filename = os.path.split(path)
        
        # get the backend
        if DEBUG:
            print "BACKENDS",self.backends
            print "SCHEME",scheme
        if scheme not in self.backends:
            raise Exception, "Backend '%s' not found\n"%scheme
            
        bend = self.GetBackend(scheme)
        
        kwargs={}
        
        # cast any allowed override variables into their proper format
        for key, cast in self.ALLOWED_OVERRIDE:
            if key in args:
                try:
                    val = cast(args[key][0])
                except ValueError, ve:
                    print traceback.format_exc()
                    return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Cannot convert parameter '%s' to %s\n"%(key,cast))
                #print "setting",key,"to",cast(args[key][0])
                kwargs[key]=cast(args[key][0])
        
        # we are gonna try submitting the job. We will need to make a deferred to return, because this could take a while
        #client_stream = stream.ProducerStream()
        client_deferred = defer.Deferred()
        
        if DEBUG:
            print "starting tasklet",bend.run
            print "COMMAND:",command
            print "KWARGS:",kwargs
        task = gevent.spawn(bend.run,yabiusername, None, command, basepath, scheme, username, hostname, remote_info_url, client_deferred, submission, **kwargs)
        if DEBUG:
            print "running tasklet",task,"with inputs",(yabiusername, command, basepath, scheme, username, hostname, remote_info_url, client_deferred, submission, kwargs)
        
        return client_deferred
    
    def resume(self):
        pass
        