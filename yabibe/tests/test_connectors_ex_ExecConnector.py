import unittest2 as unittest
import os

from yabibe.connectors.ex.ExecConnector import ExecConnector
from yabibe.exceptions import NotImplemented

class ExecConnectorTestSuite(unittest.TestCase):
    """Test yabibe.connectors.ex.ExecConnector"""
    sets = { 10: {1:2, 3:4},
             101: {'test':'blah', 'nested':{ 'blah':'blah' }}
           }

    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def ec(self):
        e = ExecConnector()
        for key in self.sets:
            e.add_running(key, self.sets[key])
        return e
    
    def test_instantiate(self):
        e = ExecConnector()
        self.assertEquals(e._running, {})
        self.assertEquals(e.childenv, {})

    def test_add_running_get_running(self):
        e = ExecConnector()
        e.add_running(10, {1:2, 3:4})
        e.add_running(101, {'test':'blah', 'nested':{ 'blah':'blah' }} )

        a = e.get_running(10)
        b = e.get_running(101)

        self.assertEquals( a, {1:2, 3:4} )
        self.assertEquals( b, {'test':'blah', 'nested':{ 'blah':'blah' }} )

    def test_running_is_copy(self):
        """if we add a hash to the running store, then change that hash, the running store copy shouldnt change"""
        e = ExecConnector()
        inhash = dict(zip(range(20),range(20,40)))
        e.add_running(0,inhash)

        self.assertEquals( e.get_running(0), inhash )

        # change original
        inhash[20] = {'a':'b','c':'d'}

        # should not change running store
        self.assertNotEquals( e.get_running(0), inhash)

    def test_update_running(self):
        e = ExecConnector()

        inhash = dict(zip(range(20),range(20,40)))
        e.add_running(0,inhash)

        inhash[20] = {'a':'b','c':'d'}
        e.update_running(0,{20:{'a':'b','c':'d'}})

        self.assertEquals(e.get_running(0), inhash)
        self.assertEquals(e.get_running(0)[20]['c'], 'd')
        
    def test_del_running(self):
        e = self.ec()

        for key in self.sets:
            self.assertEquals( e.get_running(key), self.sets[key] )
        
        # delete first set
        e.del_running(self.sets.keys()[0])
        self.assertRaises(
            KeyError,
            e.get_running,
            self.sets.keys()[0]
        )

        #rest should still exist
        for key in self.sets.keys()[1:]:
            self.assertEquals( e.get_running(key), self.sets[key] )

    def test_get_all_running(self):
        e = self.ec()
        self.assertEquals(e.get_all_running(), self.sets)

    def test_save_and_load_running(self):
        save_file = "/tmp/.test-exec-save"
        e = self.ec()
        e.save_running(save_file)

        self.assertTrue(os.path.exists(save_file))

        # make a new ec and load this into it
        e2 = ExecConnector()
        e2.load_running(save_file)
        for key in self.sets:
            self.assertEquals( e2.get_running(key), self.sets[key] )

        # delete the file
        os.unlink(save_file)
        
    def test_shutdown_startup(self):
        e = self.ec()
        e.shutdown('/tmp')

        # make a new ec and load this into it
        e2 = ExecConnector()
        e2.startup('/tmp')
        for key in self.sets:
            self.assertEquals( e2.get_running(key), self.sets[key] )

        # delete the file
        os.unlink("/tmp/exec-ExecConnector")

    def test_startup_non_existance(self):
        e2 = ExecConnector()
        e2.startup('/non-existant')

    def test_unimplemented_tun(self):
        e = self.ec()
        self.assertRaises(
            NotImplemented,
            e.run
        )

    def test_set_environ(self):
        ourenv = { 'testvar':'testval' }
        e = self.ec()
        e.SetEnvironment( ourenv )
        self.assertEquals(e.childenv, ourenv)

        e.SetEnvironment( os.environ )
        self.assertEquals(e.childenv, os.environ)
        
