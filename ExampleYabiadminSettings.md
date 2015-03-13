
```
# -*- coding: utf-8 -*-
# set your own database here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.set_this',
        'USER': 'set_this',
        'NAME': 'set_this',
        'PASSWORD': 'set_this', 
        'HOST': 'set_this',                    
        'PORT': '',
    }
}

# if you are using ldap you can set all ldap settings at this level
# you'll also need to make sure you are using the AUTHENTICATION_BACKENDS below
AUTH_LDAP_SERVER = ['set_this']
AUTH_LDAP_USER_BASE = 'set_this'
AUTH_LDAP_GROUP_BASE = 'set_this'
AUTH_LDAP_GROUP = 'yabi'
AUTH_LDAP_DEFAULT_GROUP = 'baseuser'
AUTH_LDAP_GROUPOC = 'groupofuniquenames'
AUTH_LDAP_USEROC = 'inetorgperson'
AUTH_LDAP_MEMBERATTR = 'uniqueMember'
AUTH_LDAP_USERDN = 'ou=People'

# these determine which authentication method to use
# yabi uses modelbackend by default, but can be overridden here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
 'django.contrib.auth.backends.LDAPBackend',
 'django.contrib.auth.backends.NoAuthModelBackend',
]

# code used for additional user related operations
# see: https://docs.djangoproject.com/en/dev/ref/settings/#auth-profile-module
AUTH_PROFILE_MODULE = 'yabifeapp.LDAPBackendUser'

# Make this unique, and don't share it with anybody.
# see: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = 'set_this'

# memcache server list
# add a list of your memcache servers
MEMCACHE_SERVERS = ['set_this']
MEMCACHE_KEYSPACE = "yabiadmin"

# uncomment to use memcache for sessions, be sure to have uncommented memcache settings above
# see: https://docs.djangoproject.com/en/dev/ref/settings/#session-engine
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
CACHE_BACKEND = 'memcached://'+(';'.join(MEMCACHE_SERVERS))+"/"
MEMCACHE_KEYSPACE = "yabiadmin"

# email settings so yabi can send email error alerts etc
# see https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = 'set_this'
EMAIL_APP_NAME = "Yabi Admin "
SERVER_EMAIL = "apache@set_this"                      # from address
EMAIL_SUBJECT_PREFIX = ""

# admins to email error reports to
# see: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ( 'alert', 'set_this' )
]

# see: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# Make this unique, and don't share it with anybody.
HMAC_KEY = 'set_this'

# backend address
BACKEND_IP = '0.0.0.0'
BACKEND_PORT = '20000'
BACKEND_BASE = '/'
TASKTAG = 'set_this' # this must be the same in the yabi.conf for the backend that will consume tasks from this admin
YABIBACKEND_SERVER = BACKEND_IP + ':' +  BACKEND_PORT
YABISTORE_HOME = 'set_this'
BACKEND_UPLOAD = 'http://'+BACKEND_IP+':'+BACKEND_PORT+BACKEND_BASE+"fs/ticket"
```