"""Our twisted filesystem server resource"""
from twistedweb2 import resource, http_headers, responsecode, http

from FileCompressGetResource import FileCompressGetResource
from FileCompressPutResource import FileCompressPutResource
from FileCopyResource import FileCopyResource, FileCopyProgressResource
from FileDeleteResource import FileDeleteResource
from FileGetResource import FileGetResource
from FileLCopyResource import FileLCopyResource
from FileLinkResource import FileLinkResource
from FileListResource import FileListResource
from FileMkdirResource import FileMkdirResource
from FilePutResource import FilePutResource
from FileRCopyResource import FileRCopyResource
from yabibe.utils.BackendResource import BackendResource
from yabibe.utils.parsers import parse_url


RM_DISABLED = False

class FSResource(resource.Resource, BackendResource):
    """This is the resource that connects to all the filesystem backends"""
    VERSION=0.2
    addSlash = True
    
    def __init__(self,*args,**kwargs):
        BackendResource.__init__(self,*args,**kwargs)
    
    def LoadConnectors(self, quiet=False):
        """Load all the backend connectors into our backends"""
        from yabibe.connectors import fs
        return BackendResource.LoadConnectors(self,fs,'FSConnector','fs', quiet=quiet)
    
    def render(self, request):
        # break our request path into parts
        parts = request.path.split("/")
        assert parts[0]=="", "Expected a leading '/' on the request path"
        
        backendname = parts[2]
        
        # no name? just status
        if not backendname and len(parts)==3:
            # status page
            page = "Yabi Filesystem Connector Resource Version: %s\n"%self.VERSION
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
        if segments[0]=="copy":
            # wanting the file copy resource
            return FileCopyResource(request,segments,fsresource = self), []
        elif segments[0]=="copyprogress":
            # wanting the file copy resource
            return FileCopyProgressResource(), []
        elif segments[0]=="mkdir":
            return FileMkdirResource(request,segments,fsresource=self), []
        elif segments[0]=="ls":
            return FileListResource(request,segments,fsresource=self), []
        elif segments[0]=="ln":
            return FileLinkResource(request,segments,fsresource=self), []
        elif segments[0]=="lcopy":
            return FileLCopyResource(request,segments,fsresource=self), []
        elif segments[0]=="rm":
            return FileDeleteResource(request,segments,fsresource=self), []
        elif segments[0]=="rcopy":
            return FileRCopyResource(request,segments,fsresource=self), []
        elif segments[0]=="put":
            return FilePutResource(request,segments,fsresource=self), []
        elif segments[0]=="get":
            return FileGetResource(request,segments,fsresource=self), []
        elif segments[0]=="uploadstatus":
            return UploadStatus(request, segments, fsresource=self), []
        elif segments[0]=="ticket":
            return UploadTicket(request, segments, fsresource=self), []
        elif segments[0]=="upload":
            return FileUploadResource(request, segments, fsresource=self), segments[1:]
        elif segments[0]=="zget":
            return FileCompressGetResource(request, segments, fsresource=self), segments[1:]
        elif segments[0]=="zput":
            return FileCompressPutResource(request, segments, fsresource=self), segments[1:]
        
        return resource.Resource.locateChild(self,request,segments)
        
    #
    # generic fs functions for direct calls from within yabibe
    #
    def mkdir(self, uri, yabiusername=None, creds={}, priority=0):
        """This is a call for an inner coroutine. This basically works out from the uri what backend is in action,
        and calls the relevant mkdir. Exceptions bubble out of this. For REST action, you need to catch the return/exceptions
        and make the relevant http callbacks
        """
        scheme, address = parse_url(uri)
        username = address.username
        path = address.path
        hostname = address.hostname
        port = address.port
        
        if scheme not in self.backends:
            raise Exception, "Backend '%s' not found. Available schemes are: %s\n"%(scheme, ", ".join(self.backends))
            
        return self.GetBackend(scheme).mkdir(hostname,path=path,port=port, username=username, yabiusername=yabiusername, creds=creds, priority=priority)

    def rm(self, uri, recurse=False, yabiusername=None, creds={}, priority=0):
        scheme, address = parse_url(uri)
        bendname = scheme
        username = address.username
        path = address.path
        hostname = address.hostname
        port = address.port
        
        if scheme not in self.backends:
            raise Exception, "Backend '%s' not found\n"%scheme
            
        if not RM_DISABLED:
            return self.GetBackend(scheme).rm(hostname,path=path, port=port, username=username,recurse=recurse, yabiusername=yabiusername, creds=creds, priority=priority)
        
    def link(self, target, link, yabiusername=None, creds={}, priority=0):
        targetscheme, targetaddress = parse_url(target)
        linkscheme, linkaddress = parse_url(link)
        
        # sanity checks
        if targetscheme != linkscheme:
            raise Exception, "scheme of target and link must be the same"
        
        for part in ['username','hostname','port']:
            t = getattr(targetaddress,part)
            l = getattr(linkaddress,part)
            if t != l:
                raise Exception, "link and target %s must be the same\n"%part
            
        username = targetaddress.username
        hostname = targetaddress.hostname
        port = targetaddress.port
        
        if linkscheme not in self.backends:
            raise Exception, "Backend '%s' not found\n"%linkscheme
        
        return self.GetBackend(scheme).ln(hostname,target=targetaddress.path,link=linkaddress.path,port=port, username=username, yabiusername=yabiusername, creds=creds, priority=priority)

    def lcopy(self, src, dst, recurse, yabiusername=None, creds={}, priority=0):
        srcscheme, srcaddress = parse_url(src)
        dstscheme, dstaddress = parse_url(dst)
        
        # check that the uris both point to the same location
        if srcscheme != dstscheme:
            raise Exception, "dst and src schemes must be the same"
        for part in ['username','hostname','port']:
            s = getattr(srcaddress,part)
            d = getattr(dstaddress,part)
            if s != d:
                raise Exception, "dst and src %s must be the same\n"%part
            
        username = srcaddress.username
        hostname = srcaddress.hostname
        port = srcaddress.port
        
        if srcscheme not in self.backends:
            raise Exception, "Backend '%s' not found\n"%srcscheme
        
        return self.GetBackend(srcscheme).cp(hostname,src=srcaddress.path,dst=dstaddress.path,port=port, recurse=recurse, username=username, yabiusername=yabiusername, creds=creds, priority=priority)

    def copy(self, src, dst, **kwargs):
        """call with 
        src and dst - uris.
        then your credentials as one of:
        yabiusername: just pass this in to have backend gather credentials
        or
        src_key, src_password, src_username, src_cert, dst_key, dst_password, dst_username, dst_cert: If you have the creds pass them in like this
        """
        creds = {}
        yabiusername = None

        KEYSET =    [ "%s_%s"%(part,varname) 
                      for part in ('src','dst') 
                      for varname in ('key','password','username','cert')
                      ]
        
        if 'yabiusername' not in kwargs:
            for keyname in KEYSET:
                assert keyname in kwargs, "credentials not passed in correctly"
                
            # compile any credentials together to pass to backend
            for keyname in KEYSET:
                if keyname in kwargs:
                    if part not in creds:
                        creds[part]={}
                    creds[part][varname] = kwargs[keyname]
        
        else:
            yabiusername = kwargs['yabiusername']
                
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
        
        def copy(channel):
            try:
                writeproto, fifo = dbend.GetWriteFifo(dst_hostname, dst_username, dst_path, dst_port, dst_filename,yabiusername=yabiusername,creds=creds['dst'] if 'dst' in creds else {})
                readproto, fifo2 = sbend.GetReadFifo(src_hostname, src_username, src_path, src_port, src_filename, fifo,yabiusername=yabiusername,creds=creds['src'] if 'src' in creds else {})
                
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
            
            if DEBUG:
                print "READ:",readproto,fifo2
                print "WRITE:",writeproto,fifo
                       
            # wait for one to finish
            while not readproto.isDone() and not writeproto.isDone():
                gevent.sleep()
            
            # if one died and not the other, then kill the non dead one
            if readproto.isDone() and readproto.exitcode!=0 and not writeproto.isDone():
                # readproto failed. write proto is still running. Kill it
                if DEBUG:
                    print "READ FAILED",readproto.exitcode,writeproto.exitcode
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
                if DEBUG:
                    print "Copy finished exit codes 0"
                    print "readproto:"
                    print "ERR:",readproto.err
                    print "OUT:",readproto.out
                    print "writeproto:"
                    print "ERR:",writeproto.err
                    print "OUT:",writeproto.out
                    
                channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "Copy OK\n"))
            else:
                rexit = "Killed" if readproto.exitcode==None else str(readproto.exitcode)
                wexit = "Killed" if writeproto.exitcode==None else str(writeproto.exitcode)
                
                msg = "Copy failed:\n\nRead process: "+rexit+"\n"+readproto.err+"\n\nWrite process: "+wexit+"\n"+writeproto.err+"\n"
                #print "MSG",msg
                channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, msg))
                
        client_channel = defer.Deferred()
        
        tasklet = gevent.spawn(copy,client_channel)
        
        return client_channel

