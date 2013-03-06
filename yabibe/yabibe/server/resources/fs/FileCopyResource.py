import os, signal
import traceback
import weakref, json
import gevent
from conditional import conditional


from yabibe.exceptions import BlockingException
from twisted.internet import defer
from twistedweb2 import resource, http_headers, responsecode, http
from yabibe.utils.decorators import hmac_authenticated
from yabibe.utils.parsers import parse_url
from yabibe.utils.submit_helpers import parsePOSTData
from yabibe.utils.TemporaryFile import TemporaryFile

# how often to check back on a process. 
PROCESS_CHECK_TIME = 0.01

DEFAULT_COPY_PRIORITY = 1                   # not immediate by default but high priority

DEBUG = False

if DEBUG:
    def debug(*args, **kwargs):
        import sys
        sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))
else:
    def debug(*args, **kwargs):
        pass

# module level storage for a summary of all the present copy jobs
# key = yabiusername
# value = (src,dst,readprocproto_weakref, writeprocproto_weakref)
copies_in_progress = {}


class FileCopyResource(resource.PostableResource):
    VERSION=0.1
    maxMem = 100*1024
    maxFields = 16
    maxSize = 10*1024*102
    
    # all the kenames that compose credentials for both src and dst
    KEYSET =    [ "%s_%s"%(part,varname) 
                    for part in ('src','dst') 
                    for varname in ('key','password','username','cert')
                ]
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileCopyResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)

    def handle_copy(self, src, dst, **kwargs):
        """call with 
        src and dst - uris.
        then your credentials as one of:
        yabiusername: just pass this in to have backend gather credentials
        or
        src_key, src_password, src_username, src_cert, dst_key, dst_password, dst_username, dst_cert: If you have the creds pass them in like this
        """
        creds = {}
        yabiusername = None
                            
        src_scheme, src_address = parse_url(src)
        dst_scheme, dst_address = parse_url(dst)
        
        src_username = src_address.username
        dst_username = dst_address.username
        src_path, src_filename = os.path.split(src_address.path)
        dst_path, dst_filename = os.path.split(dst_address.path)
        src_hostname = src_address.hostname
        dst_hostname = dst_address.hostname
        src_port = src_address.port
        dst_port = dst_address.port
        
        # backends
        sbend = self.fsresource().GetBackend(src_scheme)
        dbend = self.fsresource().GetBackend(dst_scheme)
        
        # create our delay generator in case things go pear shape
        # TODO: actually use these things
        src_fail_delays = sbend.NonFatalRetryGenerator()
        dst_fail_delays = dbend.NonFatalRetryGenerator()
        
        src_retry_kws = sbend.NonFatalKeywords
        dst_retry_kws = dbend.NonFatalKeywords
        
        # if no dest filename is provided, use the src_filename
        dst_filename = src_filename if not len(dst_filename) else dst_filename

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

            # we should get our creds now... because the new context manager tempfile store will need them before calling for the fifos
            creds['dst'] = dbend.Creds(yabiusername, {}, dst)
            creds['src'] = sbend.Creds(yabiusername, {}, src)
        
        def copy(channel):
            debug(CREDS=creds)
            
            with conditional(
                    'src' in creds and 'key' in creds['src'],
                    TemporaryFile(creds['src']['key'] if 'src' in creds and 'key' in creds['src'] else None)
                    ) as sourcekey:

                with conditional(
                        'dst' in creds and 'key' in creds['dst'],
                        TemporaryFile(creds['dst']['key'] if 'dst' in creds and 'key' in creds['dst']  else None)
                        ) as destkey:
                    try:
                        writeproto, fifo = dbend.GetWriteFifo(dst_hostname, dst_username, dst_path, dst_port, dst_filename,yabiusername=yabiusername,creds=creds['dst'] if 'dst' in creds else {}, credfilename = destkey.filename if destkey else None )
                        readproto, fifo2 = sbend.GetReadFifo(src_hostname, src_username, src_path, src_port, src_filename, fifo,yabiusername=yabiusername,creds=creds['src'] if 'src' in creds else {}, credfilename = sourcekey.filename if sourcekey else None )

                        def fifo_cleanup(response):
                            os.unlink(fifo)
                            return response
                        channel.addCallback(fifo_cleanup)

                    except BlockingException, be:
                        print traceback.format_exc()
                        channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)))
                        return

                    # keep a weakref in the module level info store so we can get a profile of all copy operations
                    if yabiusername not in copies_in_progress:
                        copies_in_progress[yabiusername]=[]
                    copies_in_progress[yabiusername].append( (src,dst,weakref.ref(readproto),weakref.ref(writeproto)) )

                    debug( "READ:",readproto,fifo2 )
                    debug( "WRITE:",writeproto,fifo )

                    # wait for one to finish
                    while not readproto.isDone() and not writeproto.isDone():
                        gevent.sleep()

                    # if one died and not the other, then kill the non dead one
                    if readproto.isDone() and readproto.exitcode!=0 and not writeproto.isDone():
                        # readproto failed. write proto is still running. Kill it
                        debug( "READ FAILED",readproto.exitcode,writeproto.exitcode )
                        print "read failed. attempting os.kill(",writeproto.transport.pid,",",signal.SIGKILL,")",type(writeproto.transport.pid),type(signal.SIGKILL)
                        while writeproto.transport.pid==None:
                            #print "writeproto transport pid not set. waiting for setting..."
                            gevent.sleep()
                        os.kill(writeproto.transport.pid, signal.SIGKILL)
                    else:
                        # wait for write to finish
                        if DEBUG:
                            print "WFW",readproto.exitcode,writeproto.exitcode
                        while writeproto.exitcode == None:
                            gevent.sleep()

                        # did write succeed?
                        if writeproto.exitcode == 0:
                            if DEBUG:
                                print "WFR",readproto.exitcode,writeproto.exitcode
                            while readproto.exitcode == None:
                                gevent.sleep()

                    if readproto.exitcode==0 and writeproto.exitcode==0:
                        debug( "Copy finished exit codes 0")
                        debug( "readproto:" )
                        debug( "ERR:",readproto.err )
                        debug( "OUT:",readproto.out )
                        debug( "writeproto:" )
                        debug( "ERR:",writeproto.err )
                        debug( "OUT:",writeproto.out )

                        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "Copy OK\n"))
                    else:
                        rexit = "Killed" if readproto.exitcode==None else str(readproto.exitcode)
                        wexit = "Killed" if writeproto.exitcode==None else str(writeproto.exitcode)

                        msg = "Copy failed:\n\nRead process: "+rexit+"\n"+readproto.err+"\n\nWrite process: "+wexit+"\n"+writeproto.err+"\n"
                        channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, msg))
                
        client_channel = defer.Deferred()
        
        tasklet = gevent.spawn(copy,client_channel)
        
        return client_channel
        
    #@hmac_authenticated
    def handle_copy_request(self, request):
        # override default priority
        priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_COPY_PRIORITY

        # break our request path into parts
        #print "Copy",request,request.args
        if 'src' not in request.args or 'dst' not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "copy must specify source 'src' and destination 'dst'\n")
        
        if "yabiusername" in request.args:
            yabiusername = request.args['yabiusername'][0]
            return self.handle_copy( request.args['src'][0], request.args['dst'][0], yabiusername=yabiusername )
        elif False not in [(X in request.args) for X in self.KEYSET]:
            # all the other keys are present
            keyvals = dict( [ (keyname,request.args[keyname][0]) for keyname in self.KEYSET ] )
            return self.handle_copy( request.args['src'][0], request.args['dst'][0], **keyvals)
                                        
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
            return self.handle_copy_request(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Copy Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_copy_request(request)

