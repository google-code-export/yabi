"""A support webserver to 'fake' responses to admin requests"""

import sys
from gevent import pywsgi

DEBUG = False

if DEBUG:
    def debug(*args, **kwargs):
        sys.stderr.write("debug("+",".join([str(a) for a in args])+",".join(["%s=%s"%(k,kwargs[k]) for k in kwargs])+")\n")
else:
    def debug(*args, **kwargs):
        pass

def application_builder(services):
    def application(environ, start_response):
        PATH_INFO = environ.get('PATH_INFO','/')
        QUERY_STRING = environ.get('QUERY_STRING','')

        if (PATH_INFO, QUERY_STRING) in services:
            mime, data = services[(PATH_INFO, QUERY_STRING)]
            start_response('200 OK', [('Content-Type', mime)])
            return data

        # default response
        start_response('404 Not Found',[('Content-Type', 'text/html')])
        return ''

    return application

def make_server(services={}):
    """Makes a server and serves out things defined in services. services whould be a hash.
    keys of hash are (PATH_INFO,QUERY_STRING) tuple
    values are what you want returned as (mime_type, data)
    """
    server = pywsgi.WSGIServer(('', 8080), application_builder(services) )
    server.start()
    return server

