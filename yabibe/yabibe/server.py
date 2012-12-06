import sys, os, pwd
sys.path.append(os.path.dirname(__file__))                  # add our base directory to the pythonpath

from conf import config

#read config
config.read_defaults()

# sanity check that temp directory is set
assert config.config['backend'].has_key('temp'), "[backend] section of yabi.conf is missing 'temp' directory setting"

assert config.config['backend'].has_key('hmackey'), "[backend] section of yabi.conf is missing 'hmackey' setting"
assert config.config['backend']['hmackey'], "[backend] section of yabi.conf has unset 'hmackey' value"

from urlparse import urlparse

import geventreactor
geventreactor.install()

from twistedweb2 import log
from twisted.internet import reactor
from twisted.application import strports, service, internet
from twistedweb2 import server, vhost, channel
from twistedweb2 import resource as web2resource
from twisted.python import util, syslog

# for SSL context
from OpenSSL import SSL

from BaseResource import base

# Twisted Application Framework setup:
application = service.Application('yabibe')

if config.config['backend']['logfile']:
    from twisted.python.log import ILogObserver, FileLogObserver
    from twisted.python.logfile import DailyLogFile
    logfile = DailyLogFile.fromFullPath(config.config['backend']['logfile'])
    application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

if "--syslog" in sys.argv:
    # set up twisted logging
    from twisted.python.log import ILogObserver, FileLogObserver

    SYSLOG_PREFIX = config.config['backend']['syslog_prefix'] % {  'username':pwd.getpwuid(os.getuid()).pw_name,
                                                        'pid':os.getpid()
                                                     }
    SYSLOG_FACILITY = config.config['backend']['syslog_facility']

    # log to syslog
    application.setComponent(ILogObserver, syslog.SyslogObserver(prefix=SYSLOG_PREFIX, facility=SYSLOG_FACILITY).emit)

# Setup default common access logging
res = log.LogWrapperResource(base)

log.DefaultCommonAccessLoggingObserver().start()

# Create the site and application objects
site = server.Site(res)

# for HTTPS, we need a server context factory to build the context for each ssl connection
from ServerContextFactory import ServerContextFactory

if config.config['backend']['start_http']:
    internet.TCPServer(config.config['backend']['port'][1], channel.HTTPFactory(site), interface=config.config['backend']['port'][0]).setServiceParent(application)

if config.config['backend']['start_https']:
    internet.SSLServer(config.config['backend']['sslport'][1], channel.HTTPFactory(site), ServerContextFactory(), interface=config.config['backend']['sslport'][0]).setServiceParent(application)

if config.config['backend']['telnet']:
    # telnet port to python shell
    from twisted.manhole import telnet
    
    shellfactory = telnet.ShellFactory()
    reactor.listenTCP(config.config['backend']['telnetport'][1], shellfactory)
    shellfactory.namespace['app']=application
    shellfactory.namespace['site']=site
    shellfactory.username = ''
    shellfactory.password = ''

def rm_rf(root,contents_only=False):
    """If contents_only is true, containing folder is not removed"""
    for path, dirs, files in os.walk(root, False):
        for fn in files:
            os.unlink(os.path.join(path, fn))
        for dn in dirs:
            os.rmdir(os.path.join(path, dn))
    if not contents_only:
        os.rmdir(root)

def startup():
    # setup yabiadmin server, port and path as global variables
    print "yabi admin server:",config.config["backend"]["admin"]
    
    # cleanup stray old files
    print "cleaning fifo storage:",config.config["backend"]["fifos"]
    rm_rf(config.config["backend"]["fifos"], contents_only=True)
    print "cleaning certificate storage:",config.config["backend"]["certificates"]
    rm_rf(config.config["backend"]["certificates"], contents_only=True)
    print "cleaning temp storage:",config.config["backend"]["temp"]
    rm_rf(config.config["backend"]["temp"], contents_only=True)
       
    print "Loading connectors..."
    base.LoadConnectors()
        
    # setup the TaskManager if we are needed
    if config.config["taskmanager"]["startup"]:
        print "Starting task manager"
        import TaskManager
        reactor.callLater(0.1,TaskManager.startup) 
    else:
        print "NOT starting task manager"
        
    print "Initialising connectors..."
    base.startup()

reactor.addSystemEventTrigger("after", "startup", startup)

def shutdown():
    import TaskManager
    TaskManager.shutdown()
    
    # shutdown our connectors
    base.shutdown()
    
reactor.addSystemEventTrigger("before","shutdown",shutdown)

