import unittest2 as unittest
from mock import MagicMock, patch
import os

from yabibe.utils import rm_rf
            
def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

class UtilsTestSuite(unittest.TestCase):
    """Test yabibe.utils.decorators"""

    path = "/tmp/yabibe-unit-tests"
    
    def setUp(self):
        # make sure self.path is not there
        if os.path.exists(self.path):
            os.system("rm -rf '%s'"%self.path)
            
    def tearDown(self):
        pass
        
    def test_rm_rf(self):
        """test that yabibe.utils.rm_rf deletes directories recursively"""
        # make temp directory
        path = self.path
        extradirs = ('one','two','two/three')
        extrafiles = ('one/test.txt', 'two/three/test.dat')

        os.makedirs(path)

        for d in extradirs:
            os.makedirs(os.path.join(path,d))

        for f in extrafiles:
            with open(os.path.join(path,f),'w') as fh:
                fh.write("test file data\n")

        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.isdir(path))

        # delete the path with rm_rf
        rm_rf(path)

        self.assertFalse(os.path.exists(path))

    def test_rm_rf_with_non_existant_path(self):
        self.assertRaises(
            OSError,
            rm_rf,
            self.path
        )

    def test_rm_rf_contents_only(self):
        # make temp directory
        path = self.path
        extradirs = ('one','two','two/three')
        extrafiles = ('one/test.txt', 'two/three/test.dat')

        os.makedirs(path)

        for d in extradirs:
            os.makedirs(os.path.join(path,d))

        for f in extrafiles:
            with open(os.path.join(path,f),'w') as fh:
                fh.write("test file data\n")

        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.isdir(path))

        # delete the path with rm_rf
        rm_rf(path, contents_only=True)

        self.assertTrue(os.path.exists(path))
        self.assertFalse(len(os.listdir(path)))
                    
        # delete that folder
        os.rmdir(path)

        self.assertFalse(os.path.exists(path))
