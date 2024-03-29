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

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from ccg.http import HttpResponseUnauthorized
from django.conf import settings

import hmac

import logging
logger = logging.getLogger(__name__)

import pickle

HTTP_HMAC_KEY = 'HTTP_HMAC_DIGEST'

def authentication_required(f):
    """
    This decorator is used instead of the django login_required decorator
    because we return HttpResponseUnauthorized while Django's redirects to
    the login page.
    """
    def new_function(*args, **kwargs):
        request = args[0]
        if not request.user.is_authenticated():
            return HttpResponseUnauthorized()
        return f(*args, **kwargs)
    return new_function


def profile_required(func):
    from yabi.models import User
    def newfunc(request,*args,**kwargs):
        # Check if the user has a profile; if not, nothing's going to work anyway,
        # so we might as well fail more spectacularly.
        try:
            request.user.get_profile()
        except ObjectDoesNotExist:
            User.objects.create(user=request.user)

        return func(request, *args, **kwargs)    
            
    return newfunc

#
# for views to be used only by the yabi backend, use this decorator to lock it down
# also use authentication_required
#
def hmac_authenticated(func):
    """Ensure that the user viewing this view is the backend system user"""
    def newfunc(request, *args, **kwargs):

        # check hmac result
        hmac_digest = hmac.new(settings.HMAC_KEY)
        hmac_digest.update(request.get_full_path())
        
        if HTTP_HMAC_KEY not in request.META:
            logger.critical("Hmac-digest header not present in incoming request. Denying.")
            return HttpResponseBadRequest("Hmac-digest header not present in request\n")
            
        # check HMAC matches
        if request.META[HTTP_HMAC_KEY] != hmac_digest.hexdigest():
            logger.critical("Hmac-digest header does not match expected. Authentication denied.")
            return HttpResponseUnauthorized("Hmac-digest authentication failed\n")
            
        return func(request, *args, **kwargs)
    return newfunc

    
# Number of times to indent output
# A list is used to force access by reference
__report_indent = [0]

def report(fn):
    """Decorator to print information about a function
    call for use while debugging.
    Prints function name, arguments, and call number
    when the function is called. Prints this information
    again along with the return value when the function
    returns.
    """

    def wrap(*params,**kwargs):
        call = wrap.callcount = wrap.callcount + 1

        indent = ' ' * __report_indent[0]
        fc = "%s(%s)" % (fn.__name__, ', '.join(
            [a.__repr__() for a in params] +
            ["%s = %s" % (a, repr(b)) for a,b in kwargs.items()]
        ))

        logger.debug("CALL: %s%s [#%s]" % (indent, fc, call))
        __report_indent[0] += 1
        ret = fn(*params,**kwargs)
        __report_indent[0] -= 1
        logger.debug("RETURN: %s%s %s [#%s]" % (indent, fc, repr(ret), call))

        return ret
    wrap.callcount = 0
    return wrap    



