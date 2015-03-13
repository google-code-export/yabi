There are a number of useful logs written to by the Yabi stack:

#### Yabi logs ####

```
/usr/local/python/ccgapps/yabife/release/yabife/logs/yabife.log
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/celeryd.log
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/yabiadmin.log
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/yabiengine.log
/usr/local/yabi/log/yabibe.log
```

Yabife - logs coming out of the front end django application

Celeryd - logs that come from Yabi admin during the execution of workflows

Yabiadmin - logs that typically come from tables related to tool setup, tool groups etc

Yabiengine - logs that typically arise during execution of workflows


#### Apache logs ####
```
/usr/local/python/logs/error_log
/usr/local/python/logs/yabi.ssl_error_log
/usr/local/python/logs/yabi.ssl_access_log
/usr/local/python/logs/yabi.error_log
/usr/local/python/logs/yabi.access_log
```

**NB: Check also the admin email address you set here:**

```
/usr/local/etc/ccgapps/appsettings/yabife/prod.py
/usr/local/etc/ccgapps/appsettings/yabiadmin/prod.py
```