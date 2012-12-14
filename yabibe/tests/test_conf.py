import unittest2 as unittest
from mock import MagicMock, patch
import os
import tempfile
import StringIO

from yabibe.conf import url_parser, port_setting_parser, time_parser, email_setting_parser, ConfigError, Configuration
            
def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

def make_conf(conf):
    output = []
    for key in conf:
        output.append('[%s]'%key)
        for subkey in conf[key]:
            output.append('%s: %s'%(subkey,conf[key][subkey]))
    return '\n'.join(output)+'\n'

class write_config(object):
    def __init__(self, conf):
        self.conf = conf
        
    def __enter__(self):
        self.tempfile = tempfile.NamedTemporaryFile().name
        with open(self.tempfile,'w') as fh:
            fh.write(make_conf(self.conf))
        
        return self.tempfile

    def __exit__(self, exc_type, exc_value, traceback):
        os.unlink(self.tempfile)
        

class ConfTestSuite(unittest.TestCase):
    """Test yabibe.conf"""
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def test_parse_url(self):
        """test that yabi.conf.parse_url works"""
        urls = [
            'http://www.google.com/',
            'https://www.google.com:8000',
            'http://127.0.0.1:70/path/to/resource?get=param'
        ]

        for url in urls:
            print url
            self.assertEquals( url_parser(url), url )

    def test_time_parser(self):
        input_response = [
            # test integers and floats
            (10,10),
            ("100",100),
            (1000.0, 1000.0),
            ("1000.4",1000.4),

            # HH:MM:SS
            ("10:10:10", 10*3600+10*60+10),
            ("0:3:2", 3*60+2),
            ("0:0:10", 10),
            ("100:100:100", 366100),

            # XXhXXmXXs
            ("10h", 36000),
            ("10m", 600),
            ("10s", 10),
            ("10h5s", 36005),
            ("10m5s",605),
            ("10h3m",36180),
            ("100h100m100s", 366100)
        ]

        for inp,resp in input_response:
            # test integers and floats
            self.assertEquals(time_parser(inp), resp)

        # different ways of getting a ValueError
        self.assertRaises(
            ConfigError,
            time_parser,
            object()
        )

        self.assertRaises(
            ConfigError,
            time_parser,
            "Unknown Time String"
        )

        self.assertRaises(
            ConfigError,
            time_parser,
            ""
        )       
        
    def test_port_settings(self):
        self.assertEquals(port_setting_parser('8000'), ('0.0.0.0', 8000))
        self.assertEquals(port_setting_parser('127.0.0.1'), ('127.0.0.1', 8000))
        self.assertEquals(port_setting_parser('10.0.0.1:80'), ('10.0.0.1',80))

        # check malformed port
        self.assertRaises(
            ConfigError,
            port_setting_parser,
            'blah'
        )

    def test_email_setting(self):
        email_conversions = [
            ('Bob Jones <bob@nowhere.com>', 'Bob Jones', 'bob@nowhere.com'),
            ('Terry\t<terry@blah.com>','Terry','terry@blah.com'),
            ('anon@google.com','','anon@google.com'),
            ('<test@test.com>','','test@test.com')
        ]

        for string, name, email in email_conversions:
            cname, cemail = email_setting_parser(string)
            self.assertEquals(name,cname)
            self.assertEquals(email,cemail)

    def test_Configuration_instantiate(self):
        Configuration()

    def test_Configuration_created_blank(self):
        self.assertEquals(Configuration().config, {})

    def test_Configuration_read_defaults(self):
        Configuration().read_defaults()
        
    def test_Configuration_read_from_data(self):
        test_hmac_key = "this is a test hmac key"
        conf_snippet = "[backend]\nhmackey: %s\n"%(test_hmac_key)

        c = Configuration()
        c.read_from_data(conf_snippet)

        self.assertEquals( c.config['backend']['hmackey'], test_hmac_key )

    def test_Configuration_read_from_fp(self):
        test_hmac_key = "this is a test hmac key"
        conf_snippet = "[backend]\nhmackey: %s\n"%(test_hmac_key)

        fp = StringIO.StringIO(conf_snippet)

        c = Configuration()
        c.read_from_fp(fp)

        self.assertEquals( c.config['backend']['hmackey'], test_hmac_key )

    def test_Configuration_read_every_section(self):
        test_conf = make_conf( {'backend': { 'path':'test_path'},
                                      'taskmanager': { 'polldelay': '10'},
                                      'ssh+sge': { 'qstat':'foo'},
                                      'execution':{ 'logcommand': 'true'}
                                     } )

        c = Configuration()
        c.read_from_data(test_conf)

        self.assertEquals( c.config['backend']['path'], 'test_path' )
        self.assertEquals( c.config['taskmanager']['polldelay'], 10  )
        self.assertEquals( c.config['ssh+sge']['qstat'], 'foo' )
        self.assertEquals( c.config['execution']['logcommand'], True )
        
    def test_Configuration_read_sections_missing(self):
        test_conf = make_conf( {'backend': { 'path':'test_path'},
                                      'taskmanager': { 'polldelay': 10 },
                                     } )

        c = Configuration()
        c.read_from_data(test_conf)

        self.assertEquals( c.config['backend']['path'], 'test_path' )
        self.assertEquals( c.config['taskmanager']['polldelay'], 10 )

    def test_Configuration_proc_is_None(self):
        c = Configuration()
        c.converters['backend']['temp'] = None

        # now lets try and read a conf with this setting
        test_conf = make_conf( {'backend': { 'temp': 'somestring' }} )
        c.read_from_data(test_conf)

        self.assertEquals( c.config['backend']['temp'], 'somestring' )

    def test_read_config_with_nonexisting_searchpath(self):
        """test that search path works to find config file"""
        search_path_falsies = ['/notexist','/home/bah','/home','/usr']
        c = Configuration()
        
        self.assertRaises(
            IOError,
            c.read_config,
            search_path_falsies
        )

    def test_read_from_file_thats_missing(self):
        missing = "/bdfb/df/bfd/b/fd/fdbfdb.conf"
        c = Configuration()
        
        self.assertRaises(
            IOError,
            c.read_from_file,
            missing
        )

    def test_read_until_path_exists_and_then_no_further(self):
        with write_config({'backend': { 'path':'test_path'}}) as conf1:
            with write_config({'backend': { 'path':'overwritten'}}) as conf2:
                print conf1, conf2
                c = Configuration()
                c.read_config( ("/missing/file",conf1,conf2,"/another/missing") )

                self.assertEquals(c.config['backend']['path'], 'test_path')

    def test_get_section_conf(self):
        test_conf = make_conf( {'backend': { 'path':'test_path'},
                                      'taskmanager': { 'polldelay': 10 },
                                     } )

        c = Configuration()
        c.read_from_data(test_conf)
        self.assertEquals(c.get_section_conf('backend')['path'], 'test_path')

    def test_sanitise(self):
        # make some config files that exist
        test_conf = make_conf( {'backend': { 'path':__file__}} )
        
        c = Configuration()
        c.read_from_data(test_conf)

        # this shouldn't raise exception because path exists
        c.sanitise()

        # make a config where path is not found
        test_conf_broken = make_conf( {'backend': {'path':'/path/to/non/file'}} )
        c = Configuration()
        c.read_from_data(test_conf_broken)

        self.assertRaises(
            ConfigError,
            c.sanitise
        )

    def test_yabiadmin_property(self):
        for admin_url in ('http://test:1000/path/sub', 'https://127.0.0.1/'):
            c = Configuration()
            c.read_from_data( make_conf( {'backend':{'admin':admin_url}} ))
            self.assertEquals( c.yabiadmin, admin_url )

    def test_yabiadminscheme_property(self):
        for admin_url in ('http://test:1000/path/sub', 'https://127.0.0.1/'):
            c = Configuration()
            c.read_from_data( make_conf( {'backend':{'admin':admin_url}} ))
            self.assertEquals( c.yabiadminscheme, admin_url.split(':')[0] )

    def test_yabiadminserver_property(self):
        for admin_url in ('http://test:1000/path/sub', 'https://127.0.0.1/'):
            c = Configuration()
            c.read_from_data( make_conf( {'backend':{'admin':admin_url}} ))
            self.assertEquals( c.yabiadminserver, admin_url.split('://')[1].split('/')[0].split(':')[0] )

    def test_yabiadminport_property(self):
        for (admin_url, port) in ( ('http://test:1000/path/sub',1000), ('https://127.0.0.1/',None)):
            c = Configuration()
            c.read_from_data( make_conf( {'backend':{'admin':admin_url}} ))
            self.assertEquals( c.yabiadminport, port )

    def test_yabiadminpath_property(self):
        for (admin_url, path) in ( ('http://test:1000/path/sub','/path/sub'), ('https://127.0.0.1/','/')):
            c = Configuration()
            c.read_from_data( make_conf( {'backend':{'admin':admin_url}} ))
            self.assertEquals( c.yabiadminpath, path )

    def test_mktemp(self):
        c = Configuration()
        c.read_from_data( make_conf( {'backend':{'temp':'/unavailable'}} ))
        self.assertRaises(
            OSError,
            c.mktemp,
            ".dat"
        )

        c.read_from_data( make_conf( {'backend':{'temp':'/tmp'}} ))
        fd, filename = c.mktemp('.dat')
        self.assertTrue(filename.startswith('/tmp/tmp'))
        self.assertTrue(filename.endswith('.dat'))
        self.assertTrue(os.path.exists(filename))
        os.unlink(filename)
        
        
                        
    
    
    
