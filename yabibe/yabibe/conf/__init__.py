"""
Configuration
=============
follows a path, reading in config files. Overlays their settings on top of a default, on top of each other.
then stores the config in a sanitised form in a hash of hashes, inside the object.

Yabi then asks for various settings when it needs them
"""

import ConfigParser
import os.path
import re

import StringIO

import urlparse
import re
import tempfile
re_url_schema = re.compile(r'\w+')

import syslog
syslog_facilities = {
    'LOG_KERN':syslog.LOG_KERN,
    'LOG_USER':syslog.LOG_USER,
    'LOG_MAIL':syslog.LOG_MAIL,
    'LOG_DAEMON':syslog.LOG_DAEMON,
    'LOG_AUTH':syslog.LOG_AUTH,
    'LOG_LPR':syslog.LOG_LPR,
    'LOG_NEWS':syslog.LOG_NEWS,
    'LOG_UUCP':syslog.LOG_UUCP,
    'LOG_CRON':syslog.LOG_CRON,
    'LOG_SYSLOG':syslog.LOG_SYSLOG,
    'LOG_LOCAL0':syslog.LOG_LOCAL0,
    'LOG_LOCAL1':syslog.LOG_LOCAL1,
    'LOG_LOCAL2':syslog.LOG_LOCAL2,
    'LOG_LOCAL3':syslog.LOG_LOCAL3,
    'LOG_LOCAL4':syslog.LOG_LOCAL4,
    'LOG_LOCAL5':syslog.LOG_LOCAL5,
    'LOG_LOCAL6':syslog.LOG_LOCAL6,
    'LOG_LOCAL7':syslog.LOG_LOCAL7
}

class ConfigError(Exception):
    pass

SEARCH_PATH = ["~/.yabi/yabi.conf","~/.yabi/backend/yabi.conf","~/yabi.conf","~/.yabi","/etc/yabi.conf","/etc/yabi/yabi.conf"]

##
## Support functions that do some text processing
##
def port_setting_parser(port):
    """returns ip,port or raises exception if error"""
    re_port = re.compile(r'^(\d+\.\d+\.\d+\.\d+)(:\d+)?$')
    result = re_port.search(port)
    if result:
        ip = result.group(1)
        port = int(result.group(2)[1:]) if result.group(2) else 8000
        return ip, port
    try:
        return '0.0.0.0',int(port)
    except ValueError, ve:
        raise ConfigError("malformed IP:port setting")

def email_setting_parser(email):
    """process an email of the form "First Last <email@server.com>" into name and email.
    also handle just plain email address with no name
    """
    import rfc822
    return rfc822.parseaddr(email)

def boolean_parser(x):
    return x if type(x) is bool else x.lower()=="true" or x.lower()=="t" or x.lower()=="yes" or x.lower()=="y"

def path_parser(path):
    return os.path.normpath(os.path.expanduser(path))

def string_parser(s):
    return str(s)

def syslog_facility_parser(s):
    return syslog_facilities[s]

def url_parser(url):
    return urlparse.urlunparse(urlparse.urlparse(url))

def time_parser(t):
    "parses time and returns as seconds as a float"
    if type(t) in (int, float):
        return float(t)

    # see if we can just float it
    try:
        return float(t)
    except (TypeError, ValueError), e:
        pass

    import re
    # handle HH:MM:SS
    if type(t) in (str, unicode):
        if re.match('\d+:\d+:\d+',t):
            h,m,s = [int(n) for n in t.split(':')]
            return float(h*3600 + m*60 + s)

        # handle XXhXXmXXs types
        if len(t):
            match = re.match('(\d+h)*(\d+m)*(\d+s)*',t)
            h,m,s = [int(match.group(n+1)[:-1]) if match.group(n+1) else 0 for n in range(3)]

            # the following is zero if the string is something like "bogus time"
            if h+m+s:
                return float(h*3600. + m*60. + s)

    raise ConfigError("The value %r cannot be parsed as time"%t)

##
## The Configuration store.
##
class Configuration(object):
    """Holds the running configuration for the full yabi stack that is running under this twistd"""
    # how to handle the values in the config file.
    converters = {
        'backend': {
            'port': port_setting_parser,
            'start_http' : boolean_parser,
            
            'start_https' : boolean_parser,
            'sslport' : port_setting_parser,

            'path': path_parser,

            'fifos': path_parser,
            'tasklets': path_parser,
            'certificates': path_parser,
            'temp': path_parser,

            'certfile': path_parser,
            'keyfile': path_parser,

            'hmackey': string_parser,

            'admin': url_parser,
            'admin_cert_check': boolean_parser,

            'source': string_parser,
            'runningdir': string_parser,
            'pidfile': string_parser,
            'logfile': string_parser,

            'syslog_facility': syslog_facility_parser,
            'syslog_prefix': string_parser,
            
            'debug': boolean_parser,
        },
        'taskmanager': {
            'polldelay': time_parser,
            'startup': boolean_parser,
            'tasktag': string_parser,
            'retrywindow': time_parser
        },
        'execution': {
            'logcommand': boolean_parser,
            'logscripts': boolean_parser,
        },
        'ssh+sge': {
            'qstat': path_parser,
            'qsub': path_parser,
            'qacct': path_parser
        }
    }
     
    # defaults
    config = {
        'backend':  {
            "port":"0.0.0.0:8000",
            "start_http":"true",
            
            "sslport":"0.0.0.0:8443",
            "start_https":"false",
            
            "path":"/",
            
            "fifos":None,
            "tasklets":None,
            "certificates":None,
            
            "certfile":"~/.yabi/servercert.pem",
            "keyfile":"~/.yabi/servercert.pem",
            
            "hmackey":None,
            
            "admin":None,
            "admin_cert_check":True,
            
            "syslog_facility":syslog.LOG_DAEMON,
            "syslog_prefix":r"YABI [yabibe:%(username)s]",
        },
        'taskmanager':{
            'polldelay':'5',
            'startup':'true',
            "tasktag":None,
            "retrywindow":60,           # default is to retry for 1 minute. This is for dev and testing. production should up this value.
        },
        'ssh+sge':{
            'qstat':'qstat',
            'qsub':'qsub',
            'qacct':'qacct',
        },
        'execution':{
            'logcommand':'true',
            'logscripts':'true'
        },
    }

    def read_defaults(self):
        """read the underlying defaults into the configuration object"""
        self.read_from_file(os.path.join(os.path.dirname(__file__),"yabi_defaults.conf"))
        
    def read_from_data(self,dat):
        self.read_from_fp(StringIO.StringIO(dat))
        
    def read_from_file(self,filename):
        self.read_from_fp(open(filename)) 

    def _conditional_parse_get(self, parser, name, key, proc = None):
        """if the config block has section [name] with key 'key', set it in the config dictionary
        after processing it through proc func if that is set"""
        if parser.has_section(name):
            if parser.has_option(name, key):
                if proc is not None:
                    self.config[name][key] = proc(parser.get(name,key))
                else:
                    self.config[name][key] = parser.get(name,key)
        
    def read_from_fp(self,fp):
        conf_parser = ConfigParser.ConfigParser()
        conf_parser.readfp(fp)
        
        # main sections
        for section in self.converters:
            for key in self.converters[section]:
                self._conditional_parse_get(conf_parser, section, key, self.converters[section][key])
            
    def read_config(self, search=SEARCH_PATH):
        for part in search:
            path = os.path.expanduser(part)
            if os.path.exists(path) and os.path.isfile(path):
                return self.read_from_file(path)

        # config not founf
        raise IOError("config file not found")
            
    def get_section_conf(self,section):
        return self.config[section]
    
    def sanitise(self):
        """Check the settings for sanity"""
        for section in self.SECTIONS:
            self.config[section]['start_http'] = boolean_proc(self.config[section]['start_http'])
            self.config[section]['start_https'] = boolean_proc(self.config[section]['start_https'])
            self.config[section]['port'] = port_setting(self.config[section]['port'])
            self.config[section]['sslport'] = port_setting(self.config[section]['sslport'])
            
            conversions = dict( 
                telnet=boolean_proc,
                telnetport=port_setting,
                debug=boolean_proc
            )
            
            for key, value in conversions.iteritems():
                if key in self.config[section]:
                    self.config[section][key] = value(self.config[section][key])
         
    ##
    ## Methods to gather settings
    ##
    @property
    def yabiadmin(self):
        scheme,rest = parse_url(self.config['backend']['admin'])
        return "%s://%s:%d%s"%(scheme,rest.hostname,rest.port,rest.path)
        
    @property
    def yabiadminscheme(self):
        return parse_url(self.config['backend']['admin'])[0]

    @property
    def yabiadminserver(self):
        return parse_url(self.config['backend']['admin'])[1].hostname
        
    @property
    def yabiadminport(self):
        return parse_url(self.config['backend']['admin'])[1].port
    
    @property
    def yabiadminpath(self):
        return parse_url(self.config['backend']['admin'])[1].path
    
    
    @property
    def yabistore(self):
        return "%s:%d%s"%tuple(self.config['store']['port']+(self.config['store']['path'],))
    
    
    
    ##
    ## classify the settings into a ip/port based classification
    ##
    def classify_ports(self):
        ips = {}
        for section in self.SECTIONS:
            ip, port = self.config[section]['port']
            
            # ip number
            ipstore = ips[ip] if ip in ips else {}
            
            # then port
            portstore = ipstore[port] if port in ipstore else {}
            
            # then path
            path = self.config[section]['path']
            if path in portstore:
                # error. duplicate path
                raise ConfigError, "overlapping application paths"
            
            portstore[path] = section
            
            ipstore[port] = portstore
            ips[ip] = ipstore
            
        return ips
        
    def mktemp(self,suffix,prefix='tmp'):
        """Make a unique filename in the tempfile area and return its filename"""
        tempdir = self.config['backend']['temp']
        return tempfile.mkstemp(suffix,prefix,dir=tempdir)

# singleton
config = Configuration()
