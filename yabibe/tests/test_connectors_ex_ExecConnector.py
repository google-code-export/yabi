import unittest2 as unittest

from yabibe.connectors.ex.ExecConnector import ExecConnector

class ExecConnectorTestSuite(unittest.TestCase):
    """Test yabibe.connectors.ex.ExecConnector"""
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_instantiate(self):
        e = ExecConnector()
        self.assertEquals(e._running, {})
        self.assertEquals(e.childenv, {})
