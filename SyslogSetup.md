# Introduction #

Recent version of yabi make use of syslog as standard to log messages. The default syslog facility is local4 and this page shows how to configure the Red Hat/Centos 5 default syslogd to handle these messages. Users of syslog-ng or other syslogs should consult their chosen daemon's documentation or contact yabi@ccg.murdoch.edu.au for assistance.


# Details #

To configure syslogd to handle messages sent to the local4 facility configuration should be added to the file /etc/syslog.conf similar to this:

```
local4.*						@192.168.1.99
local4.*						/var/log/ccgdjango.log
```

The first line sends all messages to local4 (for all priorities) to a logging server at 192.168.1.99 and the second logs to a file at /var/log/ccgdjango.log (these should be changed as appropriate for your site).

When logging to a file yabi (especially yabibe) can be quite verbose and quickly fill up your filesystem so it is useful to configure the logrotate jobs to clear up old logs. This can be done (on a Red Hat/CentOS system default install) by changing the file /etc/logrotate.d/syslog so that instead of reading:
```
/var/log/messages /var/log/secure /var/log/maillog /var/log/spooler /var/log/boot.log /var/log/cron  {
    sharedscripts
    postrotate
	/bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
	/bin/kill -HUP `cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
```
It reads:
```
/var/log/messages /var/log/secure /var/log/maillog /var/log/spooler /var/log/boot.log /var/log/cron /var/log/ccgdjango.log {
    sharedscripts
    postrotate
	/bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
	/bin/kill -HUP `cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
```