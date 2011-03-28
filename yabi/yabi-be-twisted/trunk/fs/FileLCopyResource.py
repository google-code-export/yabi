# -*- coding: utf-8 -*-
from twisted.web2 import resource, http_headers, responsecode, http, server
from twisted.internet import defer, reactor
import weakref
import sys, os, json

import stackless
from Exceptions import PermissionDenied, InvalidPath, BlockingException, NoCredentials, AuthException, ProxyInitError

from utils.parsers import parse_url

from utils.submit_helpers import parsePOSTData
import traceback

DEFAULT_LCOPY_PRIORITY = 10

class FileLCopyResource(resource.PostableResource):
    VERSION=0.1
    maxMem = 100*1024
    maxFields = 16
    maxSize = 10*1024*102
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileLinkResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
        
    def handle_mkdir(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_LCOPY_PRIORITY

        recurse = False
        if 'recurse' in request.args:
            recurse = bool(request.args['recurse'][0])

        if 'src' not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "link must specify a directory 'target' to link to\n")
        
        if 'dst' not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "link must specify a directory 'link' parameter\n")
        
        srcuri = request.args['src'][0]
        srcscheme, srcaddress = parse_url(srcuri)
        dsturi = request.args['dst'][0]
        dstscheme, dstaddress = parse_url(dsturi)
        
        # check that the uris both point to the same location
        if srcscheme != dstscheme:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "dst and src schemes must be the same\n")
        
        for part in ['username','hostname','port']:
            s = getattr(srcaddress,part)
            d = getattr(dstaddress,part)
            if s != d:
                return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "dst and src %s must be the same\n"%part)
        
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
    
        yabiusername = request.args['yabiusername'][0] if "yabiusername" in request.args else None
        
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        username = srcaddress.username
        hostname = srcaddress.hostname
        port = srcaddress.port
        
        fsresource = self.fsresource()
        if srcscheme not in fsresource.Backends():
            return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found\n"%srcscheme)
            
        bend = fsresource.GetBackend(srcscheme)
        
        # our client channel
        client_channel = defer.Deferred()
        
        def do_lcopy():
            #print "LN hostname=",hostname,"path=",targetaddress.path,"username=",username
            try:
                copyer=bend.cp(hostname,src=srcaddress.path,dst=dstaddress.path,port=port, recurse=recurse, username=username, yabiusername=yabiusername, creds=creds, priority=priority)
                client_channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "OK\n"))
            except BlockingException, be:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(be)))
            except (PermissionDenied,NoCredentials,InvalidPath,ProxyInitError), exception:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.FORBIDDEN, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(exception)))
            except Exception, e:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(e)))
            
        tasklet = stackless.tasklet(do_lcopy)
        tasklet.setup()
        tasklet.run()
        
        return client_channel
    
    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.
    
        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.
        """
        deferred = parsePOSTData(request)
        
        def post_parsed(result):
            return self.handle_mkdir(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_mkdir(request)
    
