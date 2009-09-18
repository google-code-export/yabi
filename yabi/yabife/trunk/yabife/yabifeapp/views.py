# Create your views here.
import httplib
from urllib import urlencode
from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponse
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, render_mako
from django.core.exceptions import ObjectDoesNotExist
from django.utils import webhelpers
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as django_login, logout as django_logout, authenticate
from django import forms

import logging
import yabilogging
logger = logging.getLogger('yabife')


# proxy view to pass through all requests set up in urls.py
def proxy(request, url, server, base):
    logger.debug('')
    
    if not url.startswith("/"):
        url = "/" + url
    
    if request.method == "GET":

        resource = "%s%s?%s" % (base, url, urlencode(request.GET))
        logger.debug('Resource: %s' % resource)
        conn = httplib.HTTPConnection(server)
        logger.debug('Server: %s' % server)        
        conn.request(request.method, resource)
        r = conn.getresponse()

    elif request.method == "POST":

        resource = "%s%s" % (base, url)
        logger.debug('Resource: %s' % resource)
        data = urlencode(request.POST)
        logger.debug('Data: %s' % data)
        headers = {"Content-type":"application/x-www-form-urlencoded","Accept":"text/plain"}
        conn = httplib.HTTPConnection(server)
        logger.debug('Server: %s' % server)
        conn.request(request.method, resource, data, headers)
        r = conn.getresponse()

    return HttpResponse(r.read(),status=int(r.status))


def adminproxy(request, url):
    logger.debug('')
    return proxy(request, url, settings.YABIADMIN_SERVER, settings.YABIADMIN_BASE)
    

def storeproxy(request, url):
    logger.debug('')
    return proxy(request, url, settings.YABISTORE_SERVER, settings.YABISTORE_BASE)


# forms
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput(render_value=False))

# views
@login_required
def files(request):
    return render_to_response('files.html', {'h':webhelpers, 'request':request})

@login_required
def design(request):
    return render_to_response('design.html', {'h':webhelpers, 'request':request})
    
@login_required
def jobs(request):
    return render_to_response('jobs.html', {'h':webhelpers, 'request':request})

def login(request):


    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # authenticate
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:
                    django_login(request, user)
                    return HttpResponseRedirect(webhelpers.url("/"))

            else:
                form = LoginForm()
                return render_to_response('login.html', {'h':webhelpers, 'form':form, 'error':"Invalid login credentials"})

        else:
            return render_to_response('login.html', {'h':webhelpers, 'form':form, 'error':"Invalid login credentials"})

    else:
        form = LoginForm()
        return render_to_response('login.html', {'h':webhelpers, 'form':form})


def logout(request):
    django_logout(request)
    return HttpResponseRedirect(webhelpers.url("/"))


