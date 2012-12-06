import unittest2 as unittest
from mock import MagicMock, patch
import os

from yabibe.conf import parse_url, port_setting
            
def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

class ConfTestSuite(unittest.TestCase):
    """Test yabibe.conf"""

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

    def test_port_settings(self):
        data = port_setting('8000')
        self.assertEquals(data, ('0.0.0.0', 8000))

        #data = port_setting('bah')

        #print data
        #self.assertTrue(False)
