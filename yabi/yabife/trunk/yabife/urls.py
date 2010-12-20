# -*- coding: utf-8 -*-
import os
from django.conf import settings
from django.conf.urls.defaults import *
from yabife import admin

urlpatterns = patterns('yabife.yabifeapp.views',
    (r'^(?P<url>engine/job/.*)$', 'adminproxy'),
    (r'^(?P<url>ws/account/credential.*)$', 'credentialproxy'),
    (r'^(?P<url>ws/fs/put.*)$', 'fileupload'),
    (r'^(?P<url>ws/.*)$', 'adminproxy'),
    (r'^(?P<url>workflows/.*)$', 'adminproxy'),                       
    (r'^preview/metadata[/]*$', 'preview_metadata'),
    (r'^preview[/]*$', 'preview'),
    (r'^[/]*$', 'design'),
    (r'^account/password[/]*$', 'password'),
    (r'^account[/]*$', 'account'),
    (r'^design/reuse/(?P<id>.*)[/]*$', 'design'),
    (r'^design[/]*$', 'design'),
    (r'^jobs[/]*$', 'jobs'),
    (r'^files[/]*$', 'files'),
    (r'^login[/]*$', 'login', {'SSL':True}),
    (r'^logout[/]*$', 'logout'),
    (r'^wslogin[/]*$', 'wslogin', {'SSL':True}),
    (r'^wslogout[/]*$', 'wslogout'),
    (r'^admin/', include(admin.site.urls)),
    (r'^registration/', include('yabife.registration.urls')),
)

# pattern for serving statically
# will be overridden by apache alias under WSGI
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$',
                            'django.views.static.serve', 
                            {'document_root': os.path.join(os.path.dirname(__file__),"static"), 'show_indexes': True}),

    )

urlpatterns += patterns('django.views.generic.simple',
    (r'^favicon\.ico', 'redirect_to', {'url': '/static/images/favicon.ico'}),
)

handler404 = "yabife.yabifeapp.views.error_404"
handler500 = "yabife.yabifeapp.views.error_500"
