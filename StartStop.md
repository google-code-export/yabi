To start the application stack:

```
/etc/init.d/memcached start
/etc/init.d/celeryd start
/usr/local/python/bin/apachectl startssl
cd /usr/local/yabi/src/yabi-be-twisted/release ; ./init_scripts/centos/yabibe start
```

You should now be able to view a login page for both Yabi and Yabiadmin at these urls (or similar):

https://127.0.0.1/yabi

https://127.0.0.1/yabiadmin

If you can't then try and diagnose the problem in the logs see LogLocations.