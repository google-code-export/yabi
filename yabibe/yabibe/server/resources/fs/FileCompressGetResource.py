import os
import traceback
import weakref

import gevent
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from MimeStreamDecoder import no_intr
from yabibe.exceptions import NotImplemented
from yabibe.exceptions import CredentialNotFound
from yabibe.utils.FifoStream import FifoStream
from yabibe.utils.decorators import hmac_authenticated
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData


DEFAULT_GET_PRIORITY = 1

DOWNLOAD_BLOCK_SIZE = 8192

class FileCompressGetResource(resource.PostableResource):
    VERSION=0.1
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileGetResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
        
    @hmac_authenticated
    def handle_compress_get(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_GET_PRIORITY
        
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        uri = request.args['uri'][0]
        yabiusername = request.args['yabiusername'][0] if 'yabiusername' in request.args else None
        scheme, address = parse_url(uri)
        
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
        
        # how many bytes to truncate the GET at
        #bytes_to_read = int(request.args['bytes'][0]) if 'bytes' in request.args else None
        
        if not hasattr(address,"username"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No username provided in uri\n")
        
        username = address.username
        path = address.path
        hostname = address.hostname
        port = address.port
        
        basepath, filename = os.path.split(path)
        
        # get the backend
        fsresource = self.fsresource()
        if scheme not in fsresource.Backends():
            return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found\n"%scheme)
            
        bend = self.fsresource().GetBackend(scheme)
        
        # our client channel
        client_channel = defer.Deferred()
        
        def compress_tasklet(req, channel):
            """Tasklet to do file download"""
            try:
                procproto, fifo = bend.GetCompressedReadFifo(hostname,username,basepath,port,filename,yabiusername=yabiusername,creds=creds, priority=priority)
                
                def fifo_cleanup(response):
                    os.unlink(fifo)
                    return response
                channel.addCallback(fifo_cleanup)
                
            except CredentialNotFound, nc:
                print traceback.format_exc()
                return channel.callback(http.Response( responsecode.UNAUTHORIZED, {'content-type': http_headers.MimeType('text', 'plain')}, str(nc) ))
            
            except NotImplemented, ni:
                print traceback.format_exc()
                return channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, "This backend does not support compressed get\n" ))
            
            # give the engine a chance to fire up the process
            while not procproto.isStarted():
                gevent.sleep(0.1)
            
            # nonblocking open the fifo
            fd = no_intr(os.open,fifo,os.O_RDONLY | os.O_NONBLOCK )
            file = os.fdopen(fd)
        
            # make sure file handle is non blocking
            import fcntl, errno
            fcntl.fcntl(file.fileno(), fcntl.F_SETFL, os.O_NONBLOCK) 
            
            # datastream stores whether we have sent an ok response code yet
            datastream = False
            
            data = True
            while data:
                # because this is nonblocking, it might raise IOError 11
                data = no_intr(file.read,DOWNLOAD_BLOCK_SIZE)
                
                if data != True:
                    if len(data):
                        # we have data
                        if not datastream:
                            datastream = FifoStream(file)
                            datastream.prepush(data)
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                    else:
                        # end of fifo OR empty file OR MAYBE the write process is slow and hasn't written into it yet.
                        # if its an empty file or an unwritten yet file our task is the same... keep trying to read it
                        
                        # Did we error out? Wait until task is finished
                        while not procproto.isDone():
                            data = no_intr(file.read,DOWNLOAD_BLOCK_SIZE)
                            if len(data):
                                datastream = FifoStream(file)
                                datastream.prepush(data)
                                return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                            gevent.sleep(0.1)
                        
                        if procproto.exitcode:
                            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Get failed: %s\n"%procproto.err ))
                        else:
                            # transfer the file
                            datastream = FifoStream(file)
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                    
                gevent.sleep()
                
            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Catastrophic codepath violation. This error should never happen. It's a bug!" ))

        
        tasklet = gevent.spawn(compress_tasklet, request, client_channel )
        
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
            return self.handle_compress_get(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_compress_get(request)
   