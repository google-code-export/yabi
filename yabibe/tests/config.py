#
# read a configuration file that contains settings
# for testing parts of yabibe.
#
# also some helper functions for managing parts of ssh for testing
#

import os
import stat
import ConfigParser

class TestConfig(object):
    configfile = os.path.join( os.path.dirname( __file__ ), "test_config.ini" )

    # defaults
    config = {
        'username':'localusername',
        'password':'userspassword',
        'testdir':'/tmp',
        'passwordlesskey':'key data',
        'key':'key data',
        'passphrase':'key passphrase'
    }
    
    def __init__(self, configfile=None):
        self.configfile = configfile or self.configfile

        # test permissions (don't make the file world readable)
        perms = os.stat(self.configfile).st_mode

        assert perms & stat.S_IROTH == 0, "File must not be world readable"

        config = ConfigParser.ConfigParser()
        config.read(self.configfile)

        for key in self.config:
            if config.has_option('localhost', key):
                self.config[key] = config.get( 'localhost', key )

    def __getitem__(self, item):
        return self.config[item]
        
    def write_config(self):
        print yaml.dump(self.config)
    
