import json
import traceback
import weakref

import gevent
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from yabibe.Exceptions import PermissionDenied, InvalidPath, BlockingException, NoCredentials, ProxyInitError
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData


DEFAULT_LIST_PRIORITY = 0                   # immediate by default

DEBUG = False

class FileListResource(resource.PostableResource):
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
        
    def ls(self, uri, recurse=False, yabiusername=None, creds={}, priority=0):
        scheme, address = parse_url(uri)
        bendname = scheme
        username = address.username
        path = address.path
        hostname = address.hostname
        port = address.port
        
        # get the backend
        fsresource = self.fsresource()
        bend = fsresource.GetBackend(bendname)
        
        if DEBUG:
                print "ls() hostname=",hostname,"path=",path,"username=",username,"recurse=",recurse
        return bend.ls(hostname,path=path,port=port, username=username,recurse=recurse, yabiusername=yabiusername, creds=creds, priority=priority)
        
    #@hmac_authenticated
    def handle_list_request(self, request):
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_LIST_PRIORITY

        uri = request.args['uri'][0]
        scheme, address = parse_url(uri)
        
        if not hasattr(address,"username"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No username provided in uri\n")
        
        recurse = 'recurse' in request.args
                
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
        
        yabiusername = request.args['yabiusername'][0] if "yabiusername" in request.args else None
        
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        if DEBUG:
            print "URI",uri
            print "ADDRESS",address
        
 
        # our client channel
        client_channel = defer.Deferred()
        
        def do_list():
            try:
                lister=self.ls(uri, recurse=recurse, yabiusername=yabiusername, creds=creds, priority=priority)
                client_channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream=json.dumps(lister)))
            except BlockingException, be:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(be)))
            except InvalidPath, exception:
                if DEBUG:
                    print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(exception)))
            except (PermissionDenied,NoCredentials,ProxyInitError), exception:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.FORBIDDEN, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(exception)))
            except Exception, e:
                print traceback.format_exc()
                client_channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, stream=str(e)))
            
        tasklet = gevent.spawn(do_list)
        
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
            return self.handle_list_request(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_list_request(request)
