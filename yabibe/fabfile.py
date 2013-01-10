# -*- coding: utf-8 -*-
### BEGIN COPYRIGHT ###
#
# (C) Copyright 2011, Centre for Comparative Genomics, Murdoch University.
# All rights reserved.
#
# This product includes software developed at the Centre for Comparative Genomics 
# (http://ccg.murdoch.edu.au/).
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, YABI IS PROVIDED TO YOU "AS IS," 
# WITHOUT WARRANTY. THERE IS NO WARRANTY FOR YABI, EITHER EXPRESSED OR IMPLIED, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT OF THIRD PARTY RIGHTS. 
# THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF YABI IS WITH YOU.  SHOULD 
# YABI PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR
# OR CORRECTION.
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, OR AS OTHERWISE AGREED TO IN 
# WRITING NO COPYRIGHT HOLDER IN YABI, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR 
# REDISTRIBUTE YABI AS PERMITTED IN WRITING, BE LIABLE TO YOU FOR DAMAGES, INCLUDING 
# ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE 
# USE OR INABILITY TO USE YABI (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR 
# DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES 
# OR A FAILURE OF YABI TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER 
# OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
# 
### END COPYRIGHT ###
# -*- coding: utf-8 -*-
from fabric.api import env, local
from ccgfab.base import *
import os

env.username = os.environ["USER"]
env.app_root = '/usr/local/python/ccgapps/'
env.app_name = 'yabibe'
env.repo_path = 'yabibe'
env.app_install_names = ['yabibe'] # use app_name or list of names for each install
env.vc = 'mercurial'

env.writeable_dirs.extend([]) # add directories you wish to have created and made writeable
env.content_excludes.extend([]) # add quoted patterns here for extra rsync excludes
env.content_includes.extend([]) # add quoted patterns here for extra rsync includes

env.ccg_pip_options = "--download-cache=/tmp --use-mirrors --no-index --mirrors=http://c.pypi.python.org/ --mirrors=http://d.pypi.python.org/ --mirrors=http://e.pypi.python.org/"

class LocalPaths():

    target = env.username

    def getSettings(self):
        return os.path.join(env.app_root, env.app_install_names[0], self.target, env.app_name, "settings.py")

    def getProjectDir(self):
        return os.path.join(env.app_root, env.app_install_names[0], self.target, env.app_name)

    def getParentDir(self):
        return os.path.join(env.app_root, env.app_install_names[0], self.target)

    def getCeleryd(self):
        return os.path.join(self.getProjectDir(), 'virtualpython/bin/celeryd')

    def getVirtualPython(self):
        return os.path.join(self.getProjectDir(), 'virtualpython/bin/python')


localPaths = LocalPaths()

def backend(bg=False):
    """
    run the twisted backend on the terminal without forking, unless bg=True which runs it in background
    """
    cmd = "nice twistd -noy server.py --logfile=-"
    if bg:
        cmd += " >yabibe.log 2>&1 &"
    print local(cmd, capture=False)

def killbackend():
    """
    kill the twisted backend
    """
    import psutil
    twisted_pss = [p for p in psutil.process_iter() if p.name == 'twistd']
    counter = 0
    for ps in twisted_pss:
        if psutil.pid_exists(ps.pid):
            counter += 1
            ps.terminate()
    print "%i processes terminated" % counter

def start():
    """
    start the twistd server as a daemon
    """
    print local("./init_scripts/centos/yabibe start")

def stop():
    """
    stop the twistd server
    """
    print local("./init_scripts/centos/yabibe stop")

def restart():
    """
    restart the twistd server
    """
    print local("./init_scripts/centos/yabibe restart")

def release(*args, **kwargs):
    """
    Make a release deployment
    """
    requirements = kwargs.get("requirements", "requirements.txt")
    tag = kwargs.get("tag", None)
    env.ccg_requirements = requirements
    env.auto_confirm=False
    _ccg_deploy_release(tag=tag, migration=False, apacheDeployment=False)

def make_live(tag=env.user):
    _make_live_symlinks(tag)

def createdirs():
    """
    Create essential directories in home directory of user running the backend
    """
    local("mkdir -p ~/.yabi/run/backend/fifos/ ~/.yabi/run/backend/tasklets/ ~/.yabi/run/backend/temp/ ~/.yabi/run/backend/certificates/")
