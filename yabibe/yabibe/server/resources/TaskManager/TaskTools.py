"""All these funcs are done in a blocking manner using a stackless aproach. Not your normal funcs"""
import json
import os, urllib
import sys

import gevent
import signal

from yabibe.conf import config
from yabibe.utils.geventtools import GET, POST, GETFailure, RetryGET, RetryPOST
from yabibe.utils.parsers import parse_url
from yabibe.exceptions import CredentialNotFound, BlockingException

COPY_RETRY = LINK_RETRY = LCOPY_RETRY = 5

COPY_PATH = "/fs/copy"
RCOPY_PATH = "/fs/rcopy"
LCOPY_PATH = "/fs/lcopy"
LIST_PATH = "/fs/ls"
LINK_PATH = "/fs/ln"
EXEC_PATH = "/exec/run"
RESUME_PATH = "/exec/resume"
MKDIR_PATH = "/fs/mkdir"
RM_PATH = "/fs/rm"

USER_AGENT = "YabiStackless/0.1"

DEFAULT_TASK_PRIORITY = 100

DEBUG = True

def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)\n"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

def retry_delay_generator():
    """this is the delay generator for the pausing between retrying failed copy/lcopy/links"""
    delay = 2.*60.          # start with a decent time like 2 minutes
    while True:
        yield delay
        delay *= 2.0        # double it

def debug(*args, **kwargs):
    sys.stderr.write("debug("+",".join([str(a) for a in args])+",".join(["%s=%s"%(k,kwargs[k]) for k in kwargs])+")\n")

def Sleep(seconds):
    """sleep tasklet for this many seconds. seconds is a float"""
    gevent.sleep(seconds)

class CopyError(Exception): pass

def Copy(src, dst, retry=COPY_RETRY, log_callback=None, **kwargs):
    """Copy src (url) to dst (url) using the fileservice"""
    def log(msg):
        if log_callback:
            return log_callback(msg)
        
    delay_gen = retry_delay_generator()
    if DEBUG:
        print "Copying %s to %s"%(src,dst)
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)
    for num in range(retry):
        if num:
            log("Retrying copy call. Attempt #%d"%(num+1))

        result, message, blocked = do_streaming_copy( src, dst, yabiusername=kwargs['yabiusername'] )

        debug("result is",result)

        if result:
            # success
            log(message)
            debug("log",message)
            return

        # fails
        log(message)

        # todo: handle blocked
        dly = delay_gen.next()
        debug("sleeping",dly)
        Sleep(dly)                   
    
    raise CopyError(message)

def do_streaming_copy(src, dst, **kwargs):
    """call with 
        src and dst - uris.
        then your credentials as one of:
        yabiusername: just pass this in to have backend gather credentials
        or
        src_key, src_password, src_username, src_cert, dst_key, dst_password, dst_username, dst_cert: If you have the creds pass them in like this

        returns:
        success_bool, message, blocked
        """
    creds = {}
    yabiusername = None

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
    from yabibe.server.resources.BaseResource import base
    sbend = base.fs.GetBackend(src_scheme)
    dbend = base.fs.GetBackend(dst_scheme)

    # create our delay generator in case things go pear shape
    # TODO: actually use these things
    src_fail_delays = sbend.NonFatalRetryGenerator()
    dst_fail_delays = dbend.NonFatalRetryGenerator()

    src_retry_kws = sbend.NonFatalKeywords
    dst_retry_kws = dbend.NonFatalKeywords

    # if no dest filename is provided, use the src_filename
    dst_filename = src_filename if not len(dst_filename) else dst_filename

    fifo = None
    try:
        writeproto, fifo = dbend.GetWriteFifo(dst_hostname, dst_username, dst_path, dst_port, dst_filename,yabiusername=yabiusername,creds=creds['dst'] if 'dst' in creds else {})
        readproto, fifo2 = sbend.GetReadFifo(src_hostname, src_username, src_path, src_port, src_filename, fifo,yabiusername=yabiusername,creds=creds['src'] if 'src' in creds else {})

        # some debug information
        debug("readproto=",readproto,"readfifo=",fifo2)
        debug("writeproto=",writeproto,"writefifo=",fifo)

        # wait for one to finish
        while not readproto.isDone() and not writeproto.isDone():
            gevent.sleep()

        # if one died and not the other, then kill the non dead one
        if readproto.isDone() and readproto.exitcode!=0 and not writeproto.isDone():
            # readproto failed. write proto is still running. Kill it
            debug('read failed',readproto.exitcode,writeproto.exitcode)

            # wait for task to get pid (startup) so we can kill it
            while writeproto.transport.pid==None:
                gevent.sleep()

            # kill the other side
            debug("!")
            os.kill(writeproto.transport.pid, signal.SIGKILL)
            debug('killed')
        else:
            # wait for write to finish
            debug('write... ready for write',readproto.exitcode,writeproto.exitcode)
            while writeproto.exitcode == None:
                gevent.sleep()

            # did write succeed?
            if writeproto.exitcode == 0:
                debug("write... ready for read",readproto.exitcode,writeproto.exitcode)
                while readproto.exitcode == None:
                    gevent.sleep()

        debug(readproto.exitcode,writeproto.exitcode)

        # did they both exit success?
        if readproto.exitcode==0 and writeproto.exitcode==0:
            debug('Copy finished exit codes 0')
            debug('readproto err:',readproto.err,'out:',readproto.out)
            debug('writeproto err:',writeproto.err,'out:',writeproto.out)

            # call the callback for the outcome
            return (True, "Copy OK", False)
        else:
            rexit = "Killed" if readproto.exitcode==None else str(readproto.exitcode)
            wexit = "Killed" if writeproto.exitcode==None else str(writeproto.exitcode)

            msg = "Copy failed:\n\nRead process: "+rexit+"\n"+readproto.err+"\n\nWrite process: "+wexit+"\n"+writeproto.err+"\n"

            debug(msg)

            return (False, msg, False)

    except BlockingException, be:
        return (False, "Copy Process Blocked", True)

    finally:
        # delete fifo
        if fifo:
            os.unlink(fifo)


def OldCopy(src,dst,retry=COPY_RETRY, log_callback=None, **kwargs):
    """Copy src (url) to dst (url) using the fileservice"""
    delay_gen = retry_delay_generator()
    if DEBUG:
        print "Copying %s to %s"%(src,dst)
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)
    for num in range(retry):
        if num and log_callback:
            log_callback("Retrying copy call. Attempt #%d"%(num+1))
        try:
            code,message,data = GET(COPY_PATH,src=src,dst=dst, **kwargs)
            if DEBUG:
                print "code=",repr(code)
            if int(code)==200:
                # success!
                return True
            else:
                #print "FAIL"
                if log_callback:
                    log_callback("Copy %s to %s failed with %d:%s"%(src,dst,code,message))
                
        except GETFailure, err:
            print "Warning: copy failed with error:",err
            if log_callback:
                log_callback("Warning: copy failed with error: %s"%(err))
            
        Sleep(delay_gen.next())                   
    
    raise CopyError(data)

def RCopy(src, dst, yabiusername,  copy_contents=False, log_callback=None, **kwargs):
    """
    if 'copy_contents' is set, then copy the contents of the source directory, not the directory itself (like going cp -r src/* dst/)
    """
    if not dst.endswith('/'):
        dst += '/'
            
    # parse the source and dest uris
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

    #backends
    from yabibe.server.resources.BaseResource import base
    sbend = base.fs.GetBackend(src_scheme)
    dbend = base.fs.GetBackend(dst_scheme)
            
    try:
        writeproto, fifo = dbend.GetCompressedWriteFifo( dst_hostname, dst_username, dst_path, dst_port, dst_filename,yabiusername=yabiusername)
        readproto, fifo2 = sbend.GetCompressedReadFifo(src_hostname, src_username, src_path, src_port, src_filename, fifo,yabiusername=yabiusername)

        debug("FROM",src_path,"TO",dst_path)
        os.system("ls -alF '%s' > /tmp/files.txt"%src_path)

        # TODO: put following in finally clause
            ## def fifo_cleanup(response):
            ##     os.unlink(fifo)
            ##     return response
            ## result_channel.addCallback(fifo_cleanup)

        ## except BlockingException, be:
        ##     #sbend.unlock(locks[0])
        ##     #if locks[1]:
        ##         #dbend.unlock(locks[1])
        ##     print traceback.format_exc()
        ##     result_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)))
        ##     return
        
        debug("READ:",readproto,fifo2)
        debug("WRITE:",writeproto,fifo)

        # wait for one to finish
        while not readproto.isDone() and not writeproto.isDone():
            gevent.sleep()

        # if one died and not the other, then kill the non dead one
        if readproto.isDone() and readproto.exitcode!=0 and not writeproto.isDone():
            # readproto failed. write proto is still running. Kill it
            debug("READ FAILED",readproto.exitcode,writeproto.exitcode)
            debug("read failed. attempting os.kill(",writeproto.transport.pid,",",signal.SIGKILL,")",type(writeproto.transport.pid),type(signal.SIGKILL)) # TODO: use log?
            while writeproto.transport.pid==None:
                #print "writeproto transport pid not set. waiting for setting..."
                gevent.sleep()
            os.kill(writeproto.transport.pid, signal.SIGKILL)
        else:
            # wait for write to finish
            debug("WFW",readproto.exitcode,writeproto.exitcode)
            while writeproto.exitcode == None:
                gevent.sleep()

            # did write succeed?
            if writeproto.exitcode == 0:
                debug("WFR",readproto.exitcode,writeproto.exitcode)
                while readproto.exitcode == None:
                    gevent.sleep()

        if readproto.exitcode==0 and writeproto.exitcode==0:
            debug("Copy finished exit codes 0")
            debug("readproto:")
            debug("ERR:",readproto.err)
            debug("OUT:",readproto.out)
            debug("writeproto:")
            debug("ERR:",writeproto.err)
            debug("OUT:",writeproto.out)

            return True, "OK"
        else:
            rexit = "Killed" if readproto.exitcode==None else str(readproto.exitcode)
            wexit = "Killed" if writeproto.exitcode==None else str(writeproto.exitcode)

            msg = "Copy failed:\n\nRead process: "+rexit+"\n"+readproto.err+"\n\nWrite process: "+wexit+"\n"+writeproto.err+"\n"
            return False, msg

    except NotImplemented, ni:    
        ##
        ## Fallback to old manual rcopy
        ##
        print "NO FALLBACK", ni
        return

        # get a recursive listing of the source
        try:
            fsystem = List(path=src,recurse=True,yabiusername=yabiusername)
        except BlockingException, be:
            print traceback.format_exc()
            result_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)) )

        # lets split the source path on separator
        destination_dir_name = "" if copy_contents else ([X for X in src.split("/") if len(X)][-1]+'/')

        # remember the directories we make so we only make them once
        created=[]

        # count the files we copy
        file_count = 0
        folder_count = 0

        for directory in sorted(fsystem.keys()):
            # make directory
            destpath = directory[len(src_path)+1:]              # the subpath part
            if len(destpath) and destpath[-1]!='/':
                destpath += '/'
            #print "D:",dst,":",destpath,";",src_path
            if dst+destination_dir_name+destpath not in created:
                #print dst+destination_dir_name+destpath,"not in",created
                try:
                    Mkdir(dst+destination_dir_name+destpath,yabiusername=yabiusername)
                    folder_count += 1
                except BlockingException, be:
                    print traceback.format_exc()
                    result_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)) )    
                except GETFailure, gf:
                    # ignore. directory probably already exists
                    pass
                created.append(dst+destination_dir_name+destpath)

            for file,size,date,link in fsystem[directory]['files']:
                if DEBUG:
                    print "COPY",file,size,date
                    print "EXTRA",">",destpath,">",directory
                src_uri = src+destpath+file
                dst_uri = dst+destination_dir_name+destpath+file

                if DEBUG:
                    print "Copy(",src_uri,",",dst_uri,")"
                #print "Copy(",sbend+directory+"/"+file,",",dst+destpath+'/'+file,")"
                try:
                    Copy(src_uri,dst_uri,yabiusername=yabiusername,priority=priority)
                    file_count += 1
                except CopyError, ce:
                    print "RCOPY: Continuing after failed copy %s => %s : %s"%(src_uri,dst_uri,str(ce))
                Sleep(0.1)

        result_channel.callback(
                                        http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, 
                                        "%d files %d folders copied successfuly\n"%(file_count, folder_count) )
                    )
    except BlockingException, be:
        print traceback.format_exc()
        result_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)) )
    except GETFailure, gf:
        print traceback.format_exc()
        if "503" in gf.message[1]:
            result_channel.callback(http.Response( responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(gf)) )
        else:
            result_channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, str(gf)) )
    except Exception, e:
        print traceback.format_exc()
        result_channel.callback(
                                        http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, str(e))
                    )
        return


def OldRCopy(src, dst, log_callback=None, **kwargs):
    #print "RCopying %s to %s"%(src,dst)
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)

    try:
        #print "POSTING",RCOPY_PATH,src,dst,DEFAULT_TASK_PRIORITY,"kwargs:",kwargs
        code, message, data = POST(RCOPY_PATH,src=src,dst=dst, **kwargs)
        # success!
        # the returned data line should contain a summary of the copying
        assert code==200, "Success part of RCopy got non 200 return code"        
                
        # log the response if we've been asked to        
        if log_callback:
            log_callback( data )       
        
        return True
    except GETFailure, err:
        print "Warning: Copy failed with error:",err
        raise
    
def List(path,recurse=False, **kwargs):
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)

    if recurse:
        kwargs['recurse']='true'
    code, message, data = GET(LIST_PATH,uri=path, **kwargs)
    #print "RESPONSE",code,message,data
    assert code==200
    #print "LIST:",data
    return json.loads(data)

def Mkdir(path, **kwargs):
    from yabibe.server.resources.BaseResource import base                               # needs to be imported at runtime to ensure decoupling from import order

    debug("Mkdir(",path,kwargs,")")

    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)

    return base.fs.mkdir(path, **kwargs)
    #return GET(MKDIR_PATH,uri=path, **kwargs)

def Rm(path, recurse=False, **kwargs):
    from yabibe.server.resources.BaseResource import base
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)

    return base.fs.rm(uri=path,recurse=recurse, **kwargs)
    
class LinkError(Exception): pass
    
def Ln(target,link,retry=LINK_RETRY, log_callback=None, **kwargs):
    """Copy src (url) to dst (url) using the fileservice"""
    from BaseResource import base
    delay_gen = retry_delay_generator()
    if DEBUG:
        print "linking %s from %s"%(target,link)
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)
    for num in range(retry):
        if num and log_callback:
            log_callback("Retrying Ln call. Attempt #%d"%(num+1))
        try:
            return base.fs.link(target=target,link=link, **kwargs)
            
        except Exception, err:
            print "Warning: Post failed with error:",err
            if log_callback:
                log_callback("Ln %s to %s failed with error: %s"%(link,target,err))
    
        Sleep(delay_gen.next())
        
    raise LinkError(data)

def LCopy(src,dst,retry=LCOPY_RETRY, log_callback=None, **kwargs):
    """Copy src (url) to dst (url) using the fileservice"""
    from BaseResource import base
    delay_gen = retry_delay_generator()
    if DEBUG:
        print "Local-Copying %s to %s"%(src,dst)
    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)
    for num in range(retry):
        if num and log_callback:
            log_callback("Retrying Lcopy call. Attempt #%d"%(num+1))
        try:
            return base.fs.lcopy(src=src,dst=dst, **kwargs)
        except Exception, err:
            print "Warning: Post failed with error:",err
            if log_callback:
                log_callback("Lcopy %s to %s failed with error: %s"%(src,dst,err)) 
    
        Sleep(delay_gen.next())
        
    raise CopyError(data)

def SmartCopy(preferred,src,dst,retry=LCOPY_RETRY, log_callback=None, **kwargs):
    debug("Smart-Copying",src,"to",dst)
    
    srcscheme, srcaddress = parse_url(src)
    dstscheme, dstaddress = parse_url(dst)
    
    if srcaddress.hostname != dstaddress.hostname or srcaddress.username != dstaddress.username or preferred == 'copy':
        return Copy(src,dst,retry=retry,log_callback=log_callback,**kwargs)
    else:
        return LCopy(src,dst,retry=retry,log_callback=log_callback,**kwargs)
                    
def Log(logpath,message):
    """Report an error to the webservice"""
    #print "Reporting error to %s"%(logpath)
    #print "Logging to %s"%(logpath)
    if DEBUG:
        print "logpath=",logpath
        print "log=",message
    
    if "://" in logpath:
        from urlparse import urlparse
        parsed = urlparse(logpath)
        #print "LOG:",parsed.path, message,parsed.hostname,parsed.port
        code,msg,data = RetryPOST(parsed.path, message=message,host=parsed.hostname,port=parsed.port)              # error exception should bubble up and be caught
    else:
        code,msg,data = RetryPOST(logpath, scheme=config.yabiadminscheme, host=config.yabiadminserver,port=config.yabiadminport, message=message)              # error exception should bubble up and be caught
    assert code==200

    
def Status(statuspath, message):
    """Report some status to the webservice"""
    #print('Reporting status %s to statuspath %s' % (message, statuspath))
    if DEBUG:
        print "status=",message
    
    if "://" in statuspath:
        from urlparse import urlparse
        parsed = urlparse(statuspath)
        
        code,msg,data = RetryPOST(parsed.path, status=message,host=parsed.hostname,port=parsed.port)              # error exception should bubble up and be caught
    else:
        code,msg,data = RetryPOST(statuspath, scheme=config.yabiadminscheme, host=config.yabiadminserver,port=config.yabiadminport, status=message)              # error exception should bubble up and be caught
    assert code==200

def RemoteInfo(statuspath, message):
    """Report some status to the webservice"""
    #print "Reporting status to %s"%(statuspath)
    if DEBUG:
        print "remote_info=",message
    
    if "://" in statuspath:
        from urlparse import urlparse
        parsed = urlparse(statuspath)
        
        code,msg,data = RetryPOST(parsed.path, remote_info=message,host=parsed.hostname,port=parsed.port)              # error exception should bubble up and be caught
    else:
        code,msg,data = RetryPOST(statuspath, scheme=config.yabiadminscheme, host=config.yabiadminserver,port=config.yabiadminport, remote_info=message)              # error exception should bubble up and be caught
    assert code==200

def Exec( uri, yabiusername, working, submission, submission_data, state_cb, jobid_cb, info_cb, log_cb):
    #uri, submission_script, submission_vars, yabiusername, working, status, taskid):
    """execute a job on a backend"""
    scheme, address = parse_url(uri)
    username = address.username
    path = address.path
    hostname = address.hostname
    basepath, filename = os.path.split(path)

    # find which backend
    from yabibe.server.resources.BaseResource import base
    bend = base.ex.GetBackend(scheme)

    debug( "Backend:", bend )

    debug(submission_data)

    result = bend.run( yabiusername, working, submission, submission_data, state_cb, jobid_cb, info_cb, log_cb )
    debug("bend.run result:",result)
    
def ExecOld(backend, command, callbackfunc=None, **kwargs):
    if DEBUG:
        print "EXEC:",backend,"command:",command,"kwargs:",kwargs
   
    kwargs['uri']=backend
    POST(EXEC_PATH, command=command, datacallback=callbackfunc, **kwargs )

def Resume(jobid, backend, command, callbackfunc=None, **kwargs):
    if DEBUG:
        print "RESUME:",backend,"jobid:",jobid,"command:",command,"kwargs:",kwargs
    
    kwargs['uri']=backend
    POST(RESUME_PATH, jobid=jobid, command=command, datacallback=callbackfunc, **kwargs )
    
def UserCreds(yabiusername, uri, credtype="fs"):
    """Get a users credentials"""
    # see if we can get the credentials
    url = os.path.join(config.yabiadminpath,'ws/credential/%s/%s/?uri=%s'%(credtype,yabiusername,urllib.quote(uri)))
    code, message, data = RetryGET(url, scheme=config.yabiadminscheme, host=config.yabiadminserver, port=config.yabiadminport)
    if code!=200:
        raise CredentialNotFound("GET request for %s returned %d => %s"%(url,code,message))
    return json.loads(data)

def uriify(scheme,username,hostname,port=None,path=None):
    uri = "%s://%s@%s"%(scheme,username,hostname)
    path = path or '/'
    if port:
        uri = "%s:%d"%(uri,port)
    uri = "%s%s"%(uri,path)
    return uri
