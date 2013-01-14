#
# read a configuration file that contains settings
# for testing parts of yabibe.
#
# also some helper functions for managing parts of ssh for testing
#

import yaml

class TestConfig(object):
    configfile = "tests/test_config.yml"
    
    def __init__(self, configfile=None):
        self.configfile = configfile or self.configfile

        # test permissions (don't make the file world readable)
        perms = os.stat(self.configfile).st_mode

        assert perms, "File must not be world accessible"

        with open(self.configfile) as fh:
            self.config = yaml.load(fh)

