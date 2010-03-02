# -*- coding: utf-8 -*-

# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.


"""Simplistic HTTP proxy support.

This comes in two main variants - the Proxy and the ReverseProxy.

When a Proxy is in use, a browser trying to connect to a server (say,
www.yahoo.com) will be intercepted by the Proxy, and the proxy will covertly
connect to the server, and return the result.

When a ReverseProxy is in use, the client connects directly to the ReverseProxy
(say, www.yahoo.com) which farms off the request to one of a pool of servers,
and returns the result.

Normally, a Proxy is used on the client end of an Internet connection, while a
ReverseProxy is used on the server end.
"""

# twisted imports
from twisted.web2 import client, http, responsecode, http_headers
from twisted.web2.client.http import HTTPClientProtocol
from twisted.internet import reactor, protocol
from twisted.web2 import resource, server
from zope.interface import implements, Interface
from twisted.web2.channel.http import HTTPChannel
from twisted.web2.iweb import IResource
from twisted.internet import defer

# system imports
import urlparse

# web1 imports
from twisted.web.client import HTTPPageGetter

CHUNKSIZE = 8192

class ProxyClient(HTTPClientProtocol,HTTPPageGetter):
    """Used by ProxyClientFactory to implement a simple web proxy."""

    def __init__(self, command, rest, version, headers, data, father):
        HTTPClientProtocol.__init__(self)
        self.father = father
        self.command = command
        self.rest = rest
        if headers.hasHeader("proxy-connection"):
            headers.removeHeader("proxy-connection")
        headers.setHeader("connection", "close")
        self.headers = headers
        self.data = data

    def connectionMade(self):
        print "CONNECTION MADE"
        print self.command
        print self.rest
        
        self.sendCommand(self.command, self.rest)
        for header, value in self.headers.getAllRawHeaders():
            self.sendHeader(header, value)
        self.endHeaders()
        
        # pump the stream
        def pump():
            dat = self.data.read(CHUNKSIZE)
            self.transport.write(dat)
            if dat:
                reactor.callLater(0,pump)
        #self.transport.write(self.data)

    def handleStatus(self, version, code, message):
        self.father.transport.write("%s %s %s\r\n" % (version, code, message))

    def handleHeader(self, key, value):
        self.father.transport.write("%s: %s\r\n" % (key, value))

    def handleEndHeaders(self):
        self.father.transport.write("\r\n")
    
    def handleResponsePart(self, buffer):
        self.father.transport.write(buffer)

    def handleResponseEnd(self):
        self.transport.loseConnection()
        self.father.channel.transport.loseConnection()


class ProxyClientFactory(protocol.ClientFactory):
    """Used by ProxyRequest to implement a simple web proxy."""

    def __init__(self, command, rest, version, headers, stream, backchannel):
        self.backchannel = backchannel
        self.command = command
        self.rest = rest
        self.headers = headers
        self.stream = stream
        self.version = version


    def buildProtocol(self, addr):
        return ProxyClient(self.command, self.rest, self.version,
                           self.headers, self.stream, self.backchannel)


    def clientConnectionFailed(self, connector, reason):
        err = "<H1>Could not connect</H1>"
        self.backchannel.callback(http.Response( responsecode.BAD_GATEWAY,  {'content-type': http_headers.MimeType('text', 'html')}, err ))



class ProxyRequest(http.Request):
    """Used by Proxy to implement a simple web proxy."""

    protocols = {'http': ProxyClientFactory}
    ports = {'http': 80}

    def process(self):
        parsed = urlparse.urlparse(self.uri)
        protocol = parsed[0]
        host = parsed[1]
        port = self.ports[protocol]
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        rest = urlparse.urlunparse(('','')+parsed[2:])
        if not rest:
            rest = rest+'/'
        class_ = self.protocols[protocol]
        headers = self.getAllHeaders().copy()
        if not headers.has_key('host'):
            headers['host'] = host
        self.content.seek(0, 0)
        s = self.content.read()
        clientFactory = class_(self.method, rest, self.clientproto, headers,
                               s, self)
        reactor.connectTCP(host, port, clientFactory)


class Proxy(HTTPChannel):
    """This class implements a simple web proxy.

    Since it inherits from twisted.protocols.http.HTTPChannel, to use it you
    should do something like this::

        from twisted.web2 import http
        f = http.HTTPFactory()
        f.protocol = Proxy

    Make the HTTPFactory a listener on a port as per usual, and you have
    a fully-functioning web proxy!
    """

    requestFactory = ProxyRequest


class ReverseProxyRequest(http.Request):
    """Used by ReverseProxy to implement a simple reverse proxy."""

    def process(self):
        self.received_headers['host'] = self.factory.host
        clientFactory = ProxyClientFactory(self.method, self.uri,
                                            self.clientproto,
                                            self.getAllHeaders(), 
                                            self.content.read(), self)
        reactor.connectTCP(self.factory.host, self.factory.port,
                           clientFactory)

class ReverseProxy(HTTPChannel):
    """Implements a simple reverse proxy.

    For details of usage, see the file examples/proxy.py"""

    requestFactory = ReverseProxyRequest

class IConnector(Interface):
    """attribute name"""
    def connect(factory):
        """connect ClientFactory"""

class TCPConnector:
    implements(IConnector)
    def __init__(self, host, port):
        self.host = host
        self.name = host
        self.port = port
    def connect(self, factory):
        reactor.connectTCP(self.host, self.port, factory)


class UNIXConnector:
    implements(IConnector)
    name = 'n/a'
    def __init__(self, socket):
        self.socket = socket
    def connect(self, factory):
        reactor.connectUNIX(self.socket, factory)


def ReverseProxyResource(host, port, path):
    return ReverseProxyResourceConnector(TCPConnector(host, port), path)

class ReverseProxyResourceConnector(object):
    """Resource that renders the results gotten from another server

    Put this resource in the tree to cause everything below it to be relayed
    to a different server.
    """
    isLeaf = True
    implements(IResource)

    def __init__(self, connector, path):
        self.connector = connector
        self.path = path

    def locateChild(self,request,segments):
        return self,segments[1:]

    def renderHTTP(self,request):
        print "request:",dir(request)
        for a in dir(request):
            print a,"=>",getattr(request,a)
        print "CONN:",self.connector.name
        
        request.headers.setHeader('host',self.connector.name)
        
        qs = urlparse.urlparse(request.uri)[4]
        path = self.path+'/'.join(request.postpath)
        if qs:
            rest = path + '?' + qs
        else:
            rest = path
            
        print "path=",path
        print "rest=",rest
        
        backchannel = defer.Deferred()
        
        clientFactory = ProxyClientFactory(request.method, rest, 
                                     request.clientproto, 
                                     request.headers,
                                     request.stream,
                                     backchannel)
        self.connector.connect(clientFactory)
        
        return backchannel

    def prender(self, request):
        print "RPRC::render()"
        request.received_headers['host'] = self.connector.name
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        path = self.path+'/'.join(request.postpath)
        if qs:
            rest = path + '?' + qs
        else:
            rest = path
        clientFactory = ProxyClientFactory(request.method, rest, 
                                     request.clientproto, 
                                     request.getAllHeaders(),
                                     request.content.read(),
                                     request)
        self.connector.connect(clientFactory)
        return server.NOT_DONE_YET
