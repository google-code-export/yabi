import traceback
import weakref

import gevent
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from yabibe.exceptions import PermissionDenied, InvalidPath, BlockingException, NoCredentials, ProxyInitError
from yabibe.utils.decorators import hmac_authenticated
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData


DEFAULT_LINK_PRIORITY = 10

class FileLinkResource(resource.PostableResource):
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
        
    @hmac_authenticated
    def handle_link_request(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_LINK_PRIORITY

        if 'target' not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "link must specify a directory 'target' to link to\n")
        
        if 'link' not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "link must specify a directory 'link' parameter\n")
        
        targeturi = request.args['target'][0]
        targetscheme, targetaddress = parse_url(targeturi)
        linkuri = request.args['link'][0]
        linkscheme, linkaddress = parse_url(linkuri)
        
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
    
        yabiusername = request.args['yabiusername'][0] if "yabiusername" in request.args else None
        
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        # our client channel
        client_channel = defer.Deferred()
        
        def do_ln():
            #print "LN hostname=",hostname,"path=",targetaddress.path,"username=",username
            try:
                linker=self.fsresource().link(target=targeturi,link=linkuri, yabiusername=yabiusername, creds=creds, priority=priority)
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
            
        tasklet = gevent.spawn(do_ln)
        
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
            return self.handle_link_request(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_link_request(request)
    
