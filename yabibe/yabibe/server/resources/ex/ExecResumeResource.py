import os
import traceback
import weakref

import gevent
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTDataRemoteWriter


DEBUG = False

class ExecResumeResource(resource.PostableResource):
    VERSION=0.1
    
    ALLOWED_OVERRIDE = [("walltime",str), ("memory",str), ("cpus",int), ("queue",str), ("job_type",str), ("directory",str), ("stdout",str), ("stderr",str), ('module',str)]
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileListResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
        
    def handle_resume(self,request):
        args = request.args
        
        if "yabiusername" not in args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Job resumption must have a yabiusername set (so we can get credentials)!\n")
        yabiusername = args['yabiusername'][0]

        if "jobid" not in args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Job resumption must have a jobid set!\n")
        jobid = args['jobid'][0]

        if "command" not in args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Job resumption must have a command!\n")
        command = args['command'][0]
        
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        if DEBUG:
            print "RESUME:",command

        uri = request.args['uri'][0]
        scheme, address = parse_url(uri)
        
        if not hasattr(address,"username"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No username provided in uri\n")
        
        username = address.username
        path = address.path
        hostname = address.hostname
        
        basepath, filename = os.path.split(path)
        
        # get the backend
        fsresource = self.fsresource()
        if DEBUG:
            print "BACKENDS",fsresource.Backends()
        if scheme not in fsresource.Backends():
            return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found\n"%scheme)
            
        bend = self.fsresource().GetBackend(scheme)
        
        kwargs={}
        
        # cast any allowed override variables into their proper format
        for key, cast in self.ALLOWED_OVERRIDE:
            if key in args:
                try:
                    val = cast(args[key][0])
                except ValueError, ve:
                    print traceback.format_exc()
                    return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Cannot convert parameter '%s' to %s: %s\n"%(key,cast,ve))
                #print "setting",key,"to",cast(args[key][0])
                kwargs[key]=val
        
        # we are gonna try submitting the job. We will need to make a deferred to return, because this could take a while
        #client_stream = stream.ProducerStream()
        client_deferred = defer.Deferred()

        print "resume func:",bend.resume

        task = gevent.spawn(bend.resume,jobid, yabiusername, None, command, basepath, scheme, username, hostname, None, client_deferred, **kwargs)                   # TODO: remember and pass through remote_url
        
        return client_deferred
        #return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream )
        
    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.
    
        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.
        """
        deferred = parsePOSTDataRemoteWriter(request)
        
        def post_parsed(result):
            return self.handle_resume(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Resumption Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_resume(request)
    