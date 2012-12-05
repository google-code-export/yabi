import hmac

import gevent
from twistedweb2 import http, responsecode, http_headers
from yabibe.conf import config
from yabibe.utils.geventtools import sleep


DEFAULT_FUNCTION_RETRY = 3
DEFAULT_FUNCTION_RETRY_TIME = 600.0

def default_delay_generator():
    delay = 5.0
    while delay<300.:
        yield delay
        delay *= 2.0
    while True:
        yield 300.          # five minutes forever more
    
def retry(num_retries = DEFAULT_FUNCTION_RETRY, redress=[], delay_func = None):
    """num_retries is how often to retry the function.
    ignored is a list of exception classes to ignore (allow to fall through and fail the function so it doesnt retry)
    delay_func is a generator function to produce the delay generator
    """
    def retry_decorator(f):
        def new_func(*args, **kwargs):
            num = num_retries
            if delay_func:
                gen = delay_func()
            else:
                gen = default_delay_generator()
            while num:
                try:
                    return f(*args, **kwargs)               # exits on success
                except Exception, exc:
                    if True in [isinstance(exc,E) for E in redress]:                # is this an exception we should redress?
                        raise                                                       # raise the exception
                    if num-1:
                        delay = gen.next()
                        print "WARNING: retry-function",f,"raised exception",exc,"... waiting",delay,"seconds and retrying",num,"more times..."
                        sleep(delay)
                        num -= 1
                    else:
                        raise                               # out of retries... fail
        return new_func
    return retry_decorator    

def timed_retry(total_time=DEFAULT_FUNCTION_RETRY_TIME,redress=[]):
    def timed_retry_decorator(f):
        def new_func(*args, **kwargs):
            time_waited = 0.
            gen = default_delay_generator()
            while time_waited<total_time:
                try:
                    return f(*args, **kwargs)               # exits on success
                except Exception, exc:
                    if True in [isinstance(exc,E) for E in redress]:                # is this an exception we should ignore
                        raise                                                       # raise the exception
                    
                    delay = gen.next()
                    print "WARNING: retry-function",f,"raised exception",exc,"... waiting",delay,"seconds and retrying..."
                    sleep(delay)
                    time_waited += delay

            # ok. delay has now gone overlimit. run once more and just let exceptions bubble
            return f(*args, **kwargs)               # exits on success
                        
        return new_func
    return timed_retry_decorator    

def conf_retry(redress=[]):
    return timed_retry(config.config["taskmanager"]["retrywindow"], redress)

def lock(maximum):
    def lock_decorator(f):
        f._CONNECTION_COUNT = 0
        def new_func(*args, **kwargs):
            
            # pre lock
            while f._CONNECTION_COUNT >= maximum:
                print "WARNING: max connection count reached for",f,"(%d)"%maximum
                gevent.sleep(1.0)
                
            f._CONNECTION_COUNT += 1
            
            try:
                return f(*args, **kwargs)
            finally:
                # post lock
                f._CONNECTION_COUNT -= 1
                
        return new_func
    return lock_decorator
    
def call_count(f):
    if not hasattr(f,'_CONNECTION_COUNT'):
        f._CONNECTION_COUNT = 0
    def new_func(*args, **kwargs):
        f._CONNECTION_COUNT += 1
        print "function",f,f.__name__,"has",f._CONNECTION_COUNT,"present callees"
        try:
            return f(*args, **kwargs)
        finally:
            # post lock
            f._CONNECTION_COUNT -= 1
    return new_func


#
# for resources that need to be authed via hmac secret
#
def hmac_authenticated(func):
    def newfunc(self, request, *args, **kwargs):
        # check hmac result
        headers = request.headers
        if not headers.hasHeader("hmac-digest"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No hmac-digest header present in http request.\n")
            
        digest_incoming = headers.getRawHeaders("hmac-digest")[0]
        uri = request.uri
        
        hmac_digest = hmac.new(config.config['backend']['hmackey'])
        hmac_digest.update(uri)
        
        if hmac_digest.hexdigest() != digest_incoming:
            return http.Response( responsecode.UNAUTHORIZED, {'content-type': http_headers.MimeType('text', 'plain')}, "hmac-digest header present in http request is incorrect.\n")
        
        return func(self,request, *args, **kwargs)
    return newfunc
    
