"""Encapsulation of globus Authentication proxies as a mixin"""

from yabibe.utils.geventtools import RetryGET, GETFailure, sleep
import json, os
from yabibe.exceptions import CredentialNotFound, AuthException
from yabibe.conf import config
import urllib

DEBUG = False

class S3Auth(object):
    
    def AuthProxyUser(self, yabiusername, scheme, username, hostname, path, *args):
        """Auth a user via getting the credentials from the json yabiadmin backend. When the credentials are gathered, successcallback is called with the deferred.
        The deferred should be the result channel your result will go back down"""
        useragent = "YabiFS/0.1"
        
        try:
            # remove prefixed '/'s from path
            while len(path) and path[0]=='/':
                path = path[1:]
                
            # get credential for uri...
            from TaskManager.TaskTools import UserCreds
            uri = "%s://%s@%s/%s"%(scheme,username,hostname,urllib.quote(path))
            credentials = UserCreds(yabiusername, uri, credtype="fs")
            
            assert 'key' in credentials and 'cert' in credentials and 'password' in credentials, "Malformed credential JSON received from admin. I received: %s"%(str(credentials))
            
            return credentials
        
        except GETFailure, gf:
            gf_message = gf.args[0]
            if gf_message[0]==-1 and "404" in gf_message[1]:
                # connection problems
                raise CredentialNotFound( "User: %s does not have credentials for this user: %s backend: %s on host: %s\n"%(yabiusername,username,scheme,hostname) )
            
            raise AuthException( "Tried to get credentials from %s:%d and failed: %s"%(config.yabiadminserver,config.yabiadminport,gf_message[1]) )
            
        
