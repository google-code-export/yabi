# Introduction #

Currently Yabi consists of _Front End_, _Admin_ and _Back End_. _Front End_ and _Admin_ can run under mod\_wsgi on Apache, indeed this is how we typically run the application stack.

This is a sample configuration, for more complete references:
  * https://docs.djangoproject.com/en/1.3/howto/deployment/modwsgi/
  * https://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines
  * https://httpd.apache.org/docs/

# Sample Yabi Front End Configuration #

In file: /etc/httpd/conf.d/wsgi.conf
```
   LoadModule wsgi_module modules/mod_wsgi.so
   WSGISocketPrefix /var/run/httpd
```

In file: /etc/httpd/conf.d/mod\_wsgi\_daemons.conf
```
   <IfModule mod_wsgi.c>

   WSGIDaemonProcess yabife processes=2 threads=15 display-name=%{GROUP}

   </IfModule>
```

These files need to be included from your httpd.conf:

```
Include conf.d/*.conf
```

or

```
Include conf.d/wsgi.conf
Include conf.d/mod_wsgi_daemons.conf
```

A sample virtual hosts configuration for a server that just runs _Yabi Front End_.

```
<VirtualHost *:80>
    ServerAdmin your_email@mailserver.com
    DocumentRoot /var/www/html
    ServerName your_server
    ErrorLog logs/yabife.error_log
    CustomLog logs/yabife.access_log combined
    RewriteLogLevel 3
    RewriteLog logs/yabife.rewrite_log

    <Directory "/var/www/html">
      Options Indexes FollowSymLinks
      AllowOverride All
      Order allow,deny
      Allow from all
    </Directory>

    # mod_wsgi
    Include /etc/httpd/conf.d/mod_wsgi.conf
</VirtualHost>
```

...and ssl:

```
<VirtualHost *:443>

    #   General setup for the virtual host
    DocumentRoot "/var/www/html"
    ServerName your_server:443
    ServerAdmin your_email@mailserver.com
    ErrorLog logs/yabife.ssl_error_log
    TransferLog logs/yabife.ssl_access_log

    SSLEngine on
    SSLCipherSuite ALL:!ADH:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP:+eNULL

    SSLCertificateFile /etc/pki/tls/certs/localhost.crt
    SSLCertificateKeyFile /etc/pki/tls/private/localhost.key

    <Directory "/var/www/html">
        Options Indexes FollowSymLinks
        AllowOverride All
        Order allow,deny
        Allow from all
    </Directory>

    SetEnvIf User-Agent ".*MSIE.*" \
         nokeepalive ssl-unclean-shutdown \
         downgrade-1.0 force-response-1.0

    CustomLog /etc/httpd/logs/ssl_request_log \
          "%t %h %{SSL_PROTOCOL}x %{SSL_CIPHER}x \"%r\" %b"

    # mod_wsgi
    Include /etc/httpd/conf.d/mod_wsgi.conf
</VirtualHost>
```

In file: /etc/httpd/conf.d/mod\_wsgi.conf
```
   <IfModule mod_wsgi.c>

   <Location /yabi>
      WSGIProcessGroup yabife
   </Location>
   WSGIScriptAlias /yabi /usr/local/python/ccgapps/yabife/release/yabife/yabife.wsgi
   Alias /yabife/static /usr/local/python/ccgapps/yabife/release/yabife/static
   Alias /yabife/images /usr/local/python/ccgapps/yabife/release/yabife/static/images

   </IfModule>
```


# Sample Yabi Admin Configuration #

In file: /etc/httpd/conf.d/wsgi.conf
```
   <IfModule mod_wsgi.c>

   LoadModule wsgi_module modules/mod_wsgi.so
   WSGISocketPrefix /var/run/httpd

   </IfModule>
```

In file: /etc/httpd/conf.d/mod\_wsgi\_daemons.conf
```
   <IfModule mod_wsgi.c>

   WSGIDaemonProcess yabiadmin processes=2 threads=15 display-name=%{GROUP}

   </IfModule>
```



These files need to be included from your httpd.conf:

```
Include conf.d/*.conf
```

or

```
Include conf.d/wsgi.conf
Include conf.d/mod_wsgi_daemons.conf
```


A sample virtual hosts configuration for a server that just runs _Yabi Admin_.

```
<VirtualHost *:80>
    ServerAdmin your_email@mailserver.com
    DocumentRoot /var/www/html
    ServerName your_server
    ErrorLog logs/yabiadmin.error_log
    CustomLog logs/yabiadmin.access_log combined
    RewriteLogLevel 3
    RewriteLog logs/yabiadmin.rewrite_log

    <Directory "/var/www/html">
      Options Indexes FollowSymLinks
      AllowOverride All
      Order allow,deny
      Allow from all
    </Directory>

    # mod_wsgi
    Include /etc/httpd/conf.d/mod_wsgi.conf
</VirtualHost>
```

...and ssl:

```
<VirtualHost *:443>

    #   General setup for the virtual host
    DocumentRoot "/var/www/html"
    ServerName your_server:443
    ServerAdmin your_email@mailserver.com
    ErrorLog logs/yabiadmin.ssl_error_log
    TransferLog logs/yabiadmin.ssl_access_log

    SSLEngine on
    SSLCipherSuite ALL:!ADH:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP:+eNULL

    SSLCertificateFile /etc/pki/tls/certs/localhost.crt
    SSLCertificateKeyFile /etc/pki/tls/private/localhost.key

    <Directory "/var/www/html">
        Options Indexes FollowSymLinks
        AllowOverride All
        Order allow,deny
        Allow from all
    </Directory>

    SetEnvIf User-Agent ".*MSIE.*" \
         nokeepalive ssl-unclean-shutdown \
         downgrade-1.0 force-response-1.0

    CustomLog /etc/httpd/logs/ssl_request_log \
          "%t %h %{SSL_PROTOCOL}x %{SSL_CIPHER}x \"%r\" %b"

    # mod_wsgi
    Include /etc/httpd/conf.d/mod_wsgi.conf
</VirtualHost>
```

In file: /etc/httpd/conf.d/mod\_wsgi.conf:

```
   <IfModule mod_wsgi.c>

   <Location /yabiadmin>
     WSGIProcessGroup yabiadmin
   </Location>
   WSGIScriptAlias /yabiadmin /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/yabiadmin.wsgi
   Alias /yabiadmin/static /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/static
   Alias /yabiadmin/images /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/static/images

   </IfModule>
```