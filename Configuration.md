### Yabi Front End and Yabi Admin ###

Yabi admin and Yabi front end each have a settings.py:

```
/usr/local/python/ccgapps/yabife/release/yabife/settings.py
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/settings.py
```

Each of these settings.py files, load prod.py where common configuration settings are stored:

```
/usr/local/etc/ccgapps/appsettings/yabife/prod.py
/usr/local/etc/ccgapps/appsettings/yabiadmin/prod.py
```

Edit the prod.py files to set database connection details, admin email addresses.  Ldap information should be set if you wish to use ldap for authentication.

#### Using database Auth instead of LDAP ####

If you don't want to use ldap, you'll need to change the settings files for the frontend and admin:

```
/usr/local/python/ccgapps/yabife/release/yabife/settings.py
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/settings.py
```

Change this:

```
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.LDAPBackend',
    'django.contrib.auth.backends.NoAuthModelBackend',
]
```

to this:

```
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend'
]
```

#### Yabi Admin backend setting ####

You'll need to edit the file located at /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/settings.py and set this line:

```
BACKEND = {
    'live': {
        'BACKEND_IP': '192.168.1.96',
```

to:

```
BACKEND = {
    'live': {
        'BACKEND_IP': '127.0.0.1',
```



### Backend configuration file ###

On startup, the backend will load some default settings, and then go looking for a yabi.conf file of settings to load. The search path it uses is:

```
~/.yabi/yabi.conf
~/.yabi/backend/yabi.conf
~/yabi.conf
~/.yabi
/etc/yabi.conf
/etc/yabi/yabi.conf
```

If it doesn't find one, it just starts up with the defaults.

You can find the default settings template in

```
yabibe/yabibe/conf/yabi_defaults.conf
```

Copy this file to your preferred yabi.conf location and edit it to set the settings.

You can also override this behavior and explicitly set a yabi.conf location by setting the YABICONF environment variable before starting the backend.

(most of the settings here should be set appropriately unless you wish to change locations, the database settings are no longer used by the owner of this config file).

### Gotchas ###
An earlier RPM did not include the necessary logs directory so you should check this directory exists and is owned by apache

```
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/
```

If it is not you should do this:


```
mkdir /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/
chown apache:apache /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/

```

An earlier RPM also did not make a required store directory. Check for this and that it is owned by apache.


```
/usr/local/python/ccgapps/yabiadmin/store/
```


If necessary:

```
mkdir /usr/local/python/ccgapps/yabiadmin/store/
chown apache:apache /usr/local/python/ccgapps/yabiadmin/store/
```