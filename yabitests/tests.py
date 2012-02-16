import unittest
import subprocess, os, shutil, glob, time
from collections import namedtuple
import config


CONFIG_SECTION='quickstart_tests'
DEBUG = False

class FirstTest(unittest.TestCase):
    def test_success(self):
        self.assertTrue(True)


class Result(object):
    def __init__(self, status, stdout, stderr, runner):
        self.status = status
        self.stdout = stdout
        self.stderr = stderr
        self.yabi = runner
        self._id = None
        self._workflow_status = None

        if DEBUG:
            print self.status
            print self.stdout
            print self.stderr

    @property
    def id(self):
        if not self._id:
            for line in self.stdout.split("\n"):
                if "Running your job on the server. Id: " in line:
                    rest, id = line.rsplit(' ', 1)
                    self._id = id
                    return self._id
            raise ValueError("Id not found in stdout: %s", self.stdout)
        return self._id

    @property
    def workflow_status(self):
        if not self._workflow_status:
            result = self.yabi.run('status %s' % self.id)
            self._workflow_status = result.stdout
        return self._workflow_status
    @property
    def stageout_dir(self):
        for line in self.workflow_status.split('\n'):
            if 'stageout' in line:
                key, value = line.split(':', 1)
                return "%s/" % value.rsplit('/', 2)[0] # the stageout is for a job, get dir above that
        raise ValueError('No stageout directory found in workflow status\n%s' % self.workflow_status)

    def cleanup(self):
        result = self.yabi.run('rm "%s"' % self.stageout_dir)
        if result.status != 0:
            print result.status
            print result.stdout
            print result.stderr


class Yabi(object):
    def __init__(self, yabish='../yabish/yabish'):
        self.conf = config.Configuration(section=CONFIG_SECTION)

        self.command = yabish + ' '
        if self.conf.yabiurl:
            self.command += '--yabi-url="%s"' % self.conf.yabiurl
        self.setup_data_dir()

    def setup_data_dir(self):

        # use data dir passed in from Hudson etc otherwise the one from conf
        if not os.environ.get('TEST_DATA_DIR'):
            self.test_data_dir = self.conf.test_data_dir
        else:
            self.test_data_dir = os.environ.get('TEST_DATA_DIR')

        if not os.path.exists(self.test_data_dir):
            assert False, "Test data directory does not exist: %s" % self.test_data_dir

    def run(self, args=''):
        command = self.command + ' ' + args
        prefix = '. ../yabish/virt_yabish/bin/activate && '
        cmd = subprocess.Popen(prefix + command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        status = cmd.wait()
        return Result(status, cmd.stdout.read(), cmd.stderr.read(), runner=self)

    def login(self, username=None, password=None):
        if not username:
            username = self.conf.username
        if not password:
            password = self.conf.password
        result = self.run('login %s %s' % (username, password))
        return 'Login unsuccessful' not in result.stderr

    def logout(self):
        result = self.run('logout')

    def purge(self):
        result = self.run('purge')

class YabiTestCase(unittest.TestCase):

    runner = Yabi

    def _setup_admin(self):
        if 'setUpAdmin' in dir(self.__class__):
            prefix = '. ../yabiadmin/yabiadmin/virt_yabiadmin/bin/activate && '
            prefix += ' cd ../yabiadmin/yabiadmin && '
            command = 'python manage.py runscript run_test_setup --pythonpath ../.. --script-args="%s"' % 'yabitests.tests.' + self.__class__.__name__
            cmd = subprocess.Popen(prefix + command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            status = cmd.wait()
            print status
            print cmd.stdout.read()
            print cmd.stderr.read()

    def _teardown_admin(self):
        if 'tearDownAdmin' in dir(self.__class__):
            prefix = '. ../yabiadmin/yabiadmin/virt_yabiadmin/bin/activate && '
            prefix += ' cd ../yabiadmin/yabiadmin && '
            command = 'python manage.py runscript run_test_teardown --pythonpath ../.. --script-args="%s"' % 'yabitests.tests.' + self.__class__.__name__
            cmd = subprocess.Popen(prefix + command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            status = cmd.wait()
            print status
            print cmd.stdout.read()
            print cmd.stderr.read()


    def setUp(self):
        self.yabi = self.runner()
        self.yabi.login()
        self._setup_admin()

    def tearDown(self):
        self.yabi.logout()
        self.yabi.purge()
        self._teardown_admin()


class NotLoggedInTest(YabiTestCase):

    def test_run_yabish_no_args(self):
        result = self.yabi.run()
        self.assertTrue('usage:' in result.stdout)

    def test_unsuccessful_login(self):
        self.assertTrue(not self.yabi.login('tszabo', 'INVALID_PASS'))

    def test_successful_login(self):
        self.assertTrue(self.yabi.login())


class ToolNotSetupTest(YabiTestCase):
    def test_hostname_not_setup(self):
        result = self.yabi.run('hostname')
        self.assertTrue('Unknown tool name "hostname"' in result.stderr)

class HostnameTest(YabiTestCase):
    @classmethod
    def setUpAdmin(self):
        from yabiadmin.yabi import models
        lfs = models.Backend.objects.get(name='Local Filesystem')
        lex = models.Backend.objects.get(name='Local Execution')
        hostname = models.Tool.objects.create(name='hostname', display_name='hostname', path='hostname', backend=lex, fs_backend=lfs)
        tg = models.ToolGroup.objects.get(name='select data')
        alltools = models.ToolSet.objects.get(name='alltools')
        tg.toolgrouping_set.create(tool=hostname, tool_set=alltools)

    @classmethod
    def tearDownAdmin(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='hostname').delete()

    def test_hostname(self):
        result = self.yabi.run('hostname')
        self.assertTrue('ubuntu' in result.stdout)

if __name__ == "__main__":
    unittest.main()