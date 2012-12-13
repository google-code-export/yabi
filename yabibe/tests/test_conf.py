import unittest2 as unittest
from mock import MagicMock, patch
import os
import StringIO

from yabibe.conf import parse_url, port_setting_parser, time_parser, email_setting_parser, ConfigError, Configuration
            
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
        scheme,data = parse_url('http://www.google.com/path/to/file')

        self.assertEquals(scheme, 'http')
        self.assertEquals(data.scheme, '')
        self.assertEquals(data.netloc, 'www.google.com')
        self.assertEquals(data.path, '/path/to/file')
        self.assertEquals(data.params, '')
        self.assertEquals(data.query, '')
        self.assertEquals(data.fragment, '')
        
    def test_parse_url_non_supported_scheme(self):
        """test that parse_url works with wierd schemes"""
        scheme,data = parse_url('hotpockets://bogus.url:9999/path/to/file?bigcheese=12&littlecheese=skinny+mouse')

        self.assertEquals(scheme, 'hotpockets')
        self.assertEquals(data.netloc, 'bogus.url:9999')
        self.assertEquals(data.path, '/path/to/file')
        self.assertEquals(data.query, 'bigcheese=12&littlecheese=skinny+mouse')

    def test_parse_url_params(self):
        scheme,data = parse_url('hotpockets://username@bogus.url:9999/')
        self.assertEquals(data.username, 'username')

        scheme,data = parse_url('hotpockets://username:password@bogus.url:9999/')
        self.assertEquals(data.username, 'username')
        self.assertEquals(data.password, 'password')

    def test_time_parser(self):
        # test integers and floats
        self.assertEquals(time_parser(10), 10)
        self.assertEquals(time_parser("100"), 100)
        self.assertEquals(time_parser(1000.000), 1000)
        self.assertEquals(time_parser("1000.4"), 1000.4)

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

        
