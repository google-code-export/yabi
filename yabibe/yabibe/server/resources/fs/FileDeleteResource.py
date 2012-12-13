import traceback
import weakref

import gevent
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from yabibe.exceptions import PermissionDenied, InvalidPath, BlockingException, NoCredentials, ProxyInitError
from yabibe.utils.decorators import hmac_authenticated
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData


DEFAULT_DELETE_PRIORITY = 2                         

# print out extra debug information to the log
DEBUG = False

# diable the rm function (can be helpful during debug)
DISABLED = False

class FileDeleteResource(resource.PostableResource):
    VERSION=0.1
    maxMem = 100*1024
    maxFields = 16
    maxSize = 10*1024*102
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileListResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
    
    @hmac_authenticated
    def handle_delete_request(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_DELETE_PRIORITY
        
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        uri = request.args['uri'][0]
        scheme, address = parse_url(uri)
        
        if not hasattr(address,"username"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No username provided in uri\n")
        
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
        
        yabiusername = request.args['yabiusername'][0] if "yabiusername" in request.args else None
        
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        recurse = 'recurse' in request.args
        
        # our client channel
        client_channel = defer.Deferred()
        
        def do_rm():
            if DEBUG:
                print "DO_RM hostname=",hostname,"path=",path,"username=",username,"recurse=",recurse
            try:
                # if delete function is not disabled (for DEBUG purposes)
                deleter=self.fsresource().rm(uri,recurse=recurse, yabiusername=yabiusername, creds=creds, priority=priority)
                client_channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "OK\n"))
            except (PermissionDenied,NoCredentials,InvalidPath,ProxyInitError), exception:
                print traceback.format_exc()
                #print "rm call failed...\n%s"%traceback.format_exc()
                client_channel.callback(http.Response( responsecode.FORBIDDEN, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(exception)))
            except BlockingException, be:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(be)))
            except Exception, exception:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(exception)))    
            
        tasklet = gevent.spawn(do_rm)
        
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
            return self.handle_delete_request(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_delete_request(request)

