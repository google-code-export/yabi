import unittest2 as unittest
from mock import MagicMock, patch
import os
import StringIO

from yabibe.conf import url_parser, port_setting_parser, time_parser, email_setting_parser, ConfigError, Configuration
            
def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

class ConfTestSuite(unittest.TestCase):
    """Test yabibe.conf"""
    def _make_conf(self,conf):
        output = []
        for key in conf:
            output.append('[%s]'%key)
            for subkey in conf[key]:
                output.append('%s: %s'%(subkey,conf[key][subkey]))
        return '\n'.join(output)+'\n'

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
        test_conf = self._make_conf( {'backend': { 'path':'test_path'},
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
        test_conf = self._make_conf( {'backend': { 'path':'test_path'},
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
        test_conf = self._make_conf( {'backend': { 'temp': 'somestring' }} )
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
            
