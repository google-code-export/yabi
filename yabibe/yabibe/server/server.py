import sys, os, pwd

from twisted.application import service, internet
from twisted.internet import reactor
from twisted.python import syslog
from twistedweb2 import log, channel, server

from yabibe.server.ServerContextFactory import ServerContextFactory
from yabibe.conf import config
from yabibe.server.resources.BaseResource import base
from yabibe.utils import rm_rf

def app():
    #sys.path.append(os.path.dirname(__file__))                  # add our base directory to the pythonpath
    
    #read config
    config.read_defaults()

    # sanity check that temp directory is set
    assert config.config['backend'].has_key('temp'), "[backend] section of yabi.conf is missing 'temp' directory setting"

    assert config.config['backend'].has_key('hmackey'), "[backend] section of yabi.conf is missing 'hmackey' setting"
    assert config.config['backend']['hmackey'], "[backend] section of yabi.conf has unset 'hmackey' value"

    # Twisted Application Framework setup:
    application = service.Application('yabibe')

    # TODO: make this ADD the logger, not replace it.
    # we should be able to log to stdout, multiple files AND syslog
    #if config.config['backend']['logfile']:
    #    from twisted.python.log import ILogObserver, FileLogObserver
    #    from twisted.python.logfile import DailyLogFile
    #    logfile = DailyLogFile.fromFullPath(config.config['backend']['logfile'])
    #    application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

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
    if config.config['backend']['start_http']:
        internet.TCPServer(config.config['backend']['port'][1], channel.HTTPFactory(site), interface=config.config['backend']['port'][0]).setServiceParent(application)

    if config.config['backend']['start_https']:
        internet.SSLServer(config.config['backend']['sslport'][1], channel.HTTPFactory(site), ServerContextFactory(), interface=config.config['backend']['sslport'][0]).setServiceParent(application)

    reactor.addSystemEventTrigger("after", "startup", startup)
    reactor.addSystemEventTrigger("before","shutdown",shutdown)

    return application

def shutdown():
    """We run this before the server shuts down
    """
    # stop TaskManager if its running
    if config.config["taskmanager"]["startup"]:
        from resources import TaskManager
        TaskManager.shutdown()

    # shutdown our connectors
    base.shutdown()

def startup():
    """After startup we run this.
    It cleans the paths up, starts up the taskmanager if its switched on and bolts in the resources
    """
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
        from yabibe.server.resources import TaskManager
        reactor.callLater(0.1,TaskManager.startup) 
    else:
        print "NOT starting task manager"

    print "Initialising connectors..."
    base.startup()

application = app()
