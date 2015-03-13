Fabric is a Python (2.5 or higher) library and command-line tool for streamlining the use of SSH for application deployment or systems administration tasks. (http://fabfile.org). Fabric is how we typically deploy at the CCG using Centos and Apache/mod\_wsgi.

### Prerequisites ###
**NB:** You might need to change to the right postgres devel version
```
sudo yum install python-setuptools python-devel gcc openssl-devel.x86_64 postgresql84-devel
sudo easy_install Mercurial pip virtualenv
```

### Check Mercurial is installed ###
```
hg --version
```

### Add new directories as needed ###
# mkdir for wsgi conf file
```
sudo mkdir /usr/local/python/conf/ccg-wsgi/ -p
```

### Set up a clean python for WSGI to use ###
```
sudo virtualenv -p /usr/local/python/bin/python --no-site-packages /usr/local/python/cleanpython/
sudo /usr/local/python/cleanpython/bin/pip install virtualenv
```

# check clean python is installed and is Python 2.6.5
```
/usr/local/python/cleanpython/bin/python --version
```

### Change wsgi conf ###
#change WSGIPythonHome in http.conf to be
```
WSGIPythonHome     /usr/local/python/cleanpython
```

#add the include line to mod\_wsgi.conf

```
Include /usr/local/python/conf/ccg-wsgi/
```

### Clone the repo ###
```
hg clone https://code.google.com/p/yabi/ 
```

### Deploy YABIFE ###
```
cd yabi/yabife/yabife/
sh ../../bootstrap.sh -p /usr/local/python/bin/python
source virt_yabife/bin/activate
fab release
```

# make a symlink to point at the newly released yabife i.e. for yabife-release-5.10
```
cd /usr/local/python/ccgapps/yabife/
ln -s yabife-release-5.10 release
```

### Deploy YABIADMIN ###
# change back into the directory where you cloned yabi earlier
```
cd yabi/yabiadmin/yabiadmin/
sh ../../bootstrap.sh -p /usr/local/python/bin/python
source virt_yabiadmin/bin/activate
fab release
```

# make a symlink to point at the newly released yabiadmin i.e. for yabiadmin-release-5.14
```
cd /usr/local/python/ccgapps/yabiadmin/
ln -s yabiadmin-release-5.14 release
```

### Deploy YABIBE ###
# change back into the directory where you cloned yabi earlier
```
cd yabi/yabibe/yabibe/
sh ../../bootstrap.sh -p /usr/local/python/bin/python
fab release
```

# start run the init script in the newly released directory ie for yabibe-release-5.10

# you'll need to stop any running backend before this step
```
cd /usr/local/python/ccgapps/yabibe/yabibe-release-5.10/yabibe/
sudo ./init_scripts/centos/yabibe start
```

### Start CELERYD ###
You just need to start celeryd as it operates from yabiadmin/release
```
/etc/init.d/celeryd start
```

An example of our celeryd init script can be found here:
http://code.google.com/p/yabi/source/browse/yabiadmin/admin_scripts/celeryd

### Restart apache. ###
For changes to take effect restart apache.

