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
"""All these funcs are done in a blocking manner using a stackless aproach. Not your normal funcs"""

import gevent
from twisted.web import client
from twisted.internet import reactor
import time
import json
import os, urllib
from utils.parsers import parse_url
from conf import config

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

DEBUG = False

DEFAULT_TASK_PRIORITY = 100

from utils.geventtools import GET, POST, GETFailure, CloseConnections, RetryGET, RetryPOST

def retry_delay_generator():
    """this is the delay generator for the pausing between retrying failed copy/lcopy/links"""
    delay = 2.*60.          # start with a decent time like 2 minutes
    while True:
        yield delay
        delay *= 2.0        # double it

def Sleep(seconds):
    """sleep tasklet for this many seconds. seconds is a float"""
    gevent.sleep(seconds)

class CopyError(Exception): pass

def Copy(src,dst,retry=COPY_RETRY, log_callback=None, **kwargs):
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

#def Copy(src,dst,retry=COPY_RETRY, log_callback=None, **kwargs):
    #delay_gen = retry_delay_generator()
    #if DEBUG:
        #print "Copying %s to %s"%(src,dst)
    #if 'priority' not in kwargs:
        #kwargs['priority']=str(DEFAULT_TASK_PRIORITY)
    #for num in range(retry):
        #if num and log_callback:
            #log_callback("Retrying copy call. Attempt #%d"%(num+1))
        #try:
            #pass
        
            
            
            #if DEBUG:
                #print "code=",repr(code)
            #if int(code)==200:
                ## success!
                #return True
            #else:
                ##print "FAIL"
                #if log_callback:
                    #log_callback("Copy %s to %s failed with %d:%s"%(src,dst,code,message))
                
        #except GETFailure, err:
            #print "Warning: copy failed with error:",err
            #if log_callback:
                #log_callback("Warning: copy failed with error: %s"%(err))
            
        #Sleep(delay_gen.next())                   
    
    #raise CopyError(data)
    
def RCopy(src, dst, log_callback=None, **kwargs):
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
    from BaseResource import base                               # needs to be imported at runtime to ensure decoupling from import order

    if 'priority' not in kwargs:
        kwargs['priority']=str(DEFAULT_TASK_PRIORITY)

    return base.fs.mkdir(path, **kwargs)
    #return GET(MKDIR_PATH,uri=path, **kwargs)

def Rm(path, recurse=False, **kwargs):
    from BaseResource import base
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
    if DEBUG:
        print "Smart-Copying %s to %s"%(src,dst)
    
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
    
def Exec(backend, command, callbackfunc=None, **kwargs):
    if DEBUG:
        print "EXEC:",backend,"command:",command,"kwargs:",kwargs
   
    kwargs['uri']=backend
    POST(EXEC_PATH, command=command, datacallback=callbackfunc, **kwargs )

def Resume(jobid, backend, command, callbackfunc=None, **kwargs):
    if DEBUG:
        print "RESUME:",backend,"jobid:",jobid,"command:",command,"kwargs:",kwargs
    
    kwargs['uri']=backend
    POST(RESUME_PATH, jobid=jobid, command=command, datacallback=callbackfunc, **kwargs )
    
class NoSuchCredential(Exception): pass
    
def UserCreds(yabiusername, uri, credtype="fs"):
    """Get a users credentials"""
    # see if we can get the credentials
    url = os.path.join(config.yabiadminpath,'ws/credential/%s/%s/?uri=%s'%(credtype,yabiusername,urllib.quote(uri)))
    code, message, data = RetryGET(url, scheme=config.yabiadminscheme, host=config.yabiadminserver, port=config.yabiadminport)
    if code!=200:
        raise NoSuchCredential("GET request for %s returned %d => %s"%(url,code,message))
    if DEBUG:
        print "JSON DATA:",data
    return json.loads(data)
    

            