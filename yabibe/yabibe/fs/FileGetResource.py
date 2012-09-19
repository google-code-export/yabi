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
from twistedweb2 import resource, http_headers, responsecode, http, server, fileupload
from twisted.internet import defer, reactor

import weakref
import sys, os
import gevent
import json
from MimeStreamDecoder import MimeStreamDecoder, no_intr
import traceback

from Exceptions import PermissionDenied, InvalidPath, NoCredentials, ProxyInitError

from utils.geventtools import WaitForDeferredData
from utils.parsers import parse_url

from twisted.internet.defer import Deferred
from utils.FifoStream import FifoStream

from utils.submit_helpers import parsePOSTData

from decorators import hmac_authenticated

DEFAULT_GET_PRIORITY = 1

DOWNLOAD_BLOCK_SIZE = 8192

class FileGetResource(resource.PostableResource):
    VERSION=0.1
    
    # all the kenames that compose credentials for both src and dst
    KEYSET =    [ 'key','password','username','cert' ]
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileGetResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
        
    def handle_get(self, uri, bytes=None, **kwargs):
        creds = {}
        yabiusername = None
        bytes_to_read = bytes
        
        if 'yabiusername' not in kwargs:
            for keyname in self.KEYSET:
                assert keyname in kwargs, "credentials not passed in correctly"
                
            # compile any credentials together to pass to backend
            for keyname in self.KEYSET:
                if keyname in kwargs:
                    if part not in creds:
                        creds[part]={}
                    creds[part][varname] = kwargs[keyname]
        
        else:
            yabiusername = kwargs['yabiusername']
        
        scheme, address = parse_url(uri)
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
        
        def download_tasklet(req, channel):
            """Tasklet to do file download"""
            try:
                procproto, fifo = bend.GetReadFifo(hostname,username,basepath,port,filename,yabiusername=yabiusername,creds=creds, priority=priority)
                
                def fifo_cleanup(response):
                    os.unlink(fifo)
                    return response
                channel.addCallback(fifo_cleanup)
                
            except NoCredentials, nc:
                print traceback.format_exc()
                return channel.callback(http.Response( responsecode.UNAUTHORIZED, {'content-type': http_headers.MimeType('text', 'plain')}, str(nc) ))
            
            # give the engine a chance to fire up the process
            while not procproto.isStarted():
                gevent.sleep()
            
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
                            datastream = FifoStream(file, truncate=bytes_to_read)
                            datastream.prepush(data)
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                    else:
                        # end of fifo OR empty file OR MAYBE the write process is slow and hasn't written into it yet.
                        # if its an empty file or an unwritten yet file our task is the same... keep trying to read it
                        
                        # Did we error out? Wait until task is finished
                        while not procproto.isDone():
                            data = no_intr(file.read,DOWNLOAD_BLOCK_SIZE)
                            if len(data):
                                datastream = FifoStream(file, truncate=bytes_to_read)
                                datastream.prepush(data)
                                return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                            gevent.sleep()
                        
                        if procproto.exitcode:
                            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Get failed: %s\n"%procproto.err ))
                        else:
                            # transfer the file
                            datastream = FifoStream(file, truncate=bytes_to_read)
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                    
                gevent.sleep()
                
            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Catastrophic codepath violation. This error should never happen. It's a bug!" ))

        
        tasklet = gevent.spawn(download_tasklet, request, client_channel )
        
        return client_channel
        
        
    @hmac_authenticated
    def handle_get_request(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_GET_PRIORITY
        
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        uri = request.args['uri'][0]
        yabiusername = request.args['yabiusername'][0] if 'yabiusername' in request.args else None
        
        # how many bytes to truncate the GET at
        bytes_to_read = int(request.args['bytes'][0]) if 'bytes' in request.args else None
        
        if "yabiusername" in request.args:
            yabiusername = request.args['yabiusername'][0]
            return self.handle_get( uri, bytes_to_read, yabiusername=yabiusername )
        elif False not in [(X in request.args) for X in self.KEYSET]:
            # all the other keys are present
            keyvals = dict( [ (keyname,request.args[keyname][0]) for keyname in self.KEYSET ] )
            return self.handle_get( uri, bytes_to_read, **keyvals)
                                        
        # fall through = error
        return http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, 
            "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        )
    
    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.
    
        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.
        """
        deferred = parsePOSTData(request)
        
        def post_parsed(result):
            return self.handle_get_request(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_get_request(request)
   
