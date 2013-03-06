import os
import traceback
import weakref

import gevent
from conditional import conditional
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http

from MimeStreamDecoder import no_intr
from yabibe.exceptions import CredentialNotFound
from yabibe.utils.FifoStream import FifoStream
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData
from yabibe.utils.TemporaryFile import TemporaryFile



DEFAULT_GET_PRIORITY = 1

DOWNLOAD_BLOCK_SIZE = 8192

DEBUG = False

if DEBUG:
    def debug(*args, **kwargs):
        import sys
        sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))
else:
    def debug(*args, **kwargs):
        pass

class FileGetResource(resource.PostableResource):
    VERSION = 0.1
    
    # all the kenames that compose credentials for both src and dst
    KEYSET = [ 'key','password','username','cert' ]
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileGetResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
    
    def get(self,uri, yabiusername=None, creds={}, priority=0, credfilename=None):
        scheme, address = parse_url(uri)
        if not hasattr(address,"username"):
            raise Exception, "No username provided in uri"
        
        username = address.username
        path = address.path
        hostname = address.hostname
        port = address.port
        
        basepath, filename = os.path.split(path)
        
        # get the backend
        fsresource = self.fsresource()
        if scheme not in fsresource.Backends():
            raise Exception, "Backend '%s' not found\n"%scheme
            
        bend = self.fsresource().GetBackend(scheme)

        debug(bend=bend)
        
        # returns ( procproto object, fifo filename )
        return bend.GetReadFifo(hostname,username,basepath,port,filename,yabiusername=yabiusername,creds=creds,credfilename=credfilename)
        
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
                    if keyname not in creds:
                        creds[keyname]={}
                    creds[keyname] = kwargs[keyname]
        else:
            yabiusername = kwargs['yabiusername']
        
        # our client channel
        client_channel = defer.Deferred()
        
        def download_tasklet(channel):
            """Tasklet to do file download"""
            with conditional( 'key' in creds, TemporaryFile(creds['key']) ) as tf:
                try:
                    procproto, fifo = self.get(uri,yabiusername=yabiusername,creds=creds,priority=0,credfilename=tf.filename if tf else None)

                    def fifo_cleanup(response):
                        os.unlink(fifo)
                        return response
                    channel.addCallback(fifo_cleanup)

                except CredentialNotFound, nc:
                    print traceback.format_exc()
                    return channel.callback(http.Response( responsecode.UNAUTHORIZED, {'content-type': http_headers.MimeType('text', 'plain')}, str(nc) ))
                except Exception, exc:
                    print traceback.format_exc()
                    return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, str(exc) ))

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
                                gevent.sleep(0.1)

                            if procproto.exitcode:
                                return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Get failed: %s\n"%procproto.err ))
                            else:
                                # transfer the file
                                datastream = FifoStream(file, truncate=bytes_to_read)
                                return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))

                    gevent.sleep()

                return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Catastrophic codepath violation. This error should never happen. It's a bug!" ))

        
        tasklet = gevent.spawn(download_tasklet, client_channel )
        
        return client_channel
        
        
    #@hmac_authenticated
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
   
