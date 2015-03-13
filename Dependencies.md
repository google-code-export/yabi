Yabi is developed using Python, Stackless Python with components deployed on Apache and uses Postgresql as a database.

At the CCG we install our own Python and Apache in /usr/local and don’t use default or system versions of this software. We use Centos 5.4 x86\_64 (or better). The minimum requirements in terms of RAM or CPU are dictated by intended use. Several Gigabytes of RAM (say 4) would typically be more than enough.
The high-level requirements for running Yabi are the following:

  * Python
    * Python >= 2.6.4
    * Installed in /usr/local/python-xxx
    * Symbolic link /usr/local/python
    * Install Fabric >= 0.9.1 under python

  * Stackless Python
    * Stackless Python >= 2.6.4
    * Installed in /usr/local/stackless-xxx
    * Symbolic link /usr/local/stackless
    * Install Twisted Twisted >= 8.2.0 under stackless python
    * Install Twisted.web2 extra pack under stackless python

  * Web server
    * Apache http://www.apache.org/
    * Apache >= 2.0.63
    * mod\_ssl >= 2.0.63
    * OpenSSL >= 0.9.8e
    * mod\_wsgi >= 3.3
    * Mod\_wsgi (http://code.google.com/p/modwsgi/), configured in daemon mode


```
aahunter:~ ahunter$ curl --HEAD http://ccg5python/
HTTP/1.1 200 OK
Date: Thu, 06 Apr 2011 05:56:32 GMT
Server: Apache/2.0.63 (Unix) mod_ssl/2.0.63 OpenSSL/0.9.8e-fips-rhel5 mod_wsgi/3.3 Python/2.6.4
Content-Location: index.html.en
Vary: negotiate,accept-language,accept-charset
TCN: choice
Last-Modified: Sun, 21 Nov 2004 14:35:21 GMT
Accept-Ranges: bytes
Content-Length: 1456
Content-Type: text/html
Content-Language: en
```


  * Database
    * Postgresql 8.3.7

  * Memory cache
    * Memcached http://memcached.org/
    * Memcache is used to cache data used by the application, an allocation of 200MB of memory to memcache should suffice