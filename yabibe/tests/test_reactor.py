import unittest2 as unittest
from mock import MagicMock, patch
from twisted.internet.error import ReactorAlreadyInstalledError

from yabibe import reactor
            
def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

class ReactorTestSuite(unittest.TestCase):
    """Test yabibe.reactor"""
    def setUp(self):
        pass

    def tearDown(self):
        pass
        #mock_gevent_sleep.reset_mock()

    def test_delay_generator(self):
        # TODO: why is reactor already installed?
        self.assertRaises(
            ReactorAlreadyInstalledError,
            reactor.GeventReactor.install
        )
