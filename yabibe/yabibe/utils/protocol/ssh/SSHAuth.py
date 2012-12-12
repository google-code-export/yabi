"""Encapsulation of globus Authentication proxies as a mixin"""
import urllib

from yabibe.Exceptions import NoCredentials, AuthException
from yabibe.conf import config
from yabibe.utils.geventtools import GETFailure


DEBUG = False

class SSHAuth(object):
    def AuthProxyUser(self, yabiusername, scheme, username, hostname, path, credtype="fs"):
        """Auth a user via getting the credentials from the json yabiadmin backend. When the credentials are gathered, successcallback is called with the deferred.
        The deferred should be the result channel your result will go back down"""
        useragent = "YabiFS/0.1"
        
        try:
            # get credential for uri...
            from TaskManager.TaskTools import UserCreds
            credentials = UserCreds(yabiusername, "%s://%s@%s%s"%(scheme,username,hostname,urllib.quote(path)), credtype=credtype)
            
            assert 'key' in credentials and 'cert' in credentials and 'password' in credentials, "Malformed credential JSON received from admin. I received: %s"%(str(credentials))
            
            return credentials
        
        except GETFailure, gf:
            gf_message = gf.args[0]
            if gf_message[0]==-1 and "404" in gf_message[1]:
                # connection problems
                raise NoCredentials( "User: %s does not have credentials for this user: %s backend: %s on host: %s\n"%(yabiusername,username,scheme,hostname) )
            
            raise AuthException( "Tried to get credentials from %s:%d and failed: %s"%(config.yabiadminserver,config.yabiadminport,gf_message[1]) )
            
        
