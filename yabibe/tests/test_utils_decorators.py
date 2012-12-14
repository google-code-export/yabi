import hmac

import gevent
import unittest2 as unittest
from mock import MagicMock, patch
from twisted.web.http_headers import Headers

from yabibe.conf import config
from yabibe.utils import decorators


def debug(*args, **kwargs):
    import sys
    sys.stderr.write("debug(%s)"%(','.join([str(a) for a in args]+['%s=%r'%tup for tup in kwargs.iteritems()])))

def nothing():
    pass

mock_gevent_sleep = MagicMock(name='mock_nothing')

@patch('gevent.sleep',mock_gevent_sleep)
class DecoratorsTestSuite(unittest.TestCase):
    """Test yabibe.utils.decorators"""
    def setUp(self):
        pass
    
    def tearDown(self):
        config.reset()
        #mock_gevent_sleep.reset_mock()

    def test_delay_generator(self):
        # all values must be above this
        last_delay = 0

        # count our values so we can exit loop when we've had enough
        count = 0
        
        for delay in decorators.default_delay_generator():
            # delay generator should always increase
            # and be infinite (difficult to test! just test its really long)
            self.assertTrue(delay >= last_delay)

            # should be a number
            self.assertTrue(type(delay) is int or type(delay) is float)

            # exit if we're the nth run
            if count > 1000:
                break

            # update loop
            count += 1
            last_delay = delay

    def test_retry_decorator_success(self):
        """test that a successful inner call doesnt trigger a retry"""
        count = [0]

        def inner():
            count[0] += 1

        # call inner
        newfunc = decorators.retry()(inner)
        newfunc()

        self.assertTrue(count[0]==1)

    def test_retry_decorator_failed(self):
        """test that a failing inner function triggers a retry"""
        count = [0]

        class TestException(Exception): pass

        def inner():
            count[0] += 1
            raise TestException

        # call inner
        newfunc = decorators.retry()(inner)

        # call func. make sure the right exception is raised
        self.assertRaises( TestException, newfunc)

        # our count should be DEFAULT_FUNCTION_RETRY
        self.assertEqual( count[0], decorators.DEFAULT_FUNCTION_RETRY )

    def test_retry_decorator_custom_fail(self):
        """test that a decorator behaves with custom retry count"""
        count = [0]

        class TestException(Exception): pass

        def inner():
            count[0] += 1
            raise TestException

        for retrynum in (1,10,100,1000):            
            # reset count
            count[0] = 0

            # call inner
            newfunc = decorators.retry(num_retries=retrynum)(inner)

            # call func. make sure the right exception is raised
            self.assertRaises( TestException, newfunc)

            # our count should be DEFAULT_FUNCTION_RETRY
            self.assertEqual( count[0], retrynum )

    def test_retry_zero_times_never_calls(self):
        """test that a decorator behaves with custom retry count"""
        count = [0]

        def inner():
            count[0] = 1

        # decorate & call
        newfunc = decorators.retry(num_retries=0)(inner)
        newfunc()

        # make sure inner was never called
        self.assertEqual( count[0], 0 )
    
    def test_retry_redress_correct_exceptions(self):
        """test that redress exceptions works on retry"""
        count = [0]

        class NotImportant(Exception): pass
        class Important(Exception): pass

        def inner():
            count[0] += 1
            if count[0]==1:
                # first time raise unimportant exception
                raise NotImportant
            else:
                # later times raise important exception
                raise Important

        # decorate and call
        newfunc = decorators.retry(num_retries=5, redress=[Important])(inner)
        self.assertRaises(Important, newfunc)

        # count should be 2 because inner should have been called twice. Once with ignored exception, once without
        self.assertEquals( count[0], 2 )

    def test_custom_delay_generator_works(self):
        """test that custom delay generator is used"""
        gencount = [0]
        def custom_gen():
            """count how many times weve generated a value. always generate 1.0"""
            while True:
                gencount[0] += 1
                yield 1.0

        count = [0]
        def inner():
            count[0] += 1
            if count[0]<10:
                raise Exception

        # decorate and call
        newfunc = decorators.retry(num_retries=20, delay_func=custom_gen)(inner)
        newfunc()

        # should have been called 10 times
        self.assertEquals( count[0], 10)

        # generator should have been called one less time. retrying 10 times requires being delayed 9.
        self.assertEquals( gencount[0], 9)

    def test_timed_retry(self):
        """test timed retry"""
        mock_gevent_sleep.reset_mock()

        class TestException(Exception): pass

        def inner():
            raise TestException

        # decorate and call
        newfunc = decorators.timed_retry()(inner)
        self.assertRaises(TestException, newfunc)

        # total sleeping time must be more than total wait time
        total_sleep = sum([c[0][0] for c in mock_gevent_sleep.call_args_list])
        self.assertGreaterEqual(total_sleep, decorators.DEFAULT_FUNCTION_RETRY_TIME)

    def test_timed_retry_custom_timeout(self):
        """test custom timed retry"""
        class TestException(Exception): pass

        def inner():
            raise TestException

        for delay in (0,1,10,100,1000,10000):
            # decorate and call
            newfunc = decorators.timed_retry(total_time=delay)(inner)
            self.assertRaises(TestException, newfunc)

            # total sleeping time must be more than total wait time
            total_sleep = sum([c[0][0] for c in mock_gevent_sleep.call_args_list])
            self.assertGreaterEqual(total_sleep, delay)

    def test_timed_retry_redress_exceptions_list(self):
        """test redress exception list in timed retry"""
        count = [0]

        class NotImportant(Exception): pass
        class Important(Exception): pass

        def inner():
            count[0] += 1
            if count[0]==1:
                # first time raise unimportant exception
                raise NotImportant
            else:
                # later times raise important exception
                raise Important

        # decorate and call
        newfunc = decorators.timed_retry(redress=[Important])(inner)
        self.assertRaises(Important, newfunc)

        # count should be 2 because inner should have been called twice. Once with ignored exception, once without
        self.assertEquals( count[0], 2 )

    def test_conf_retry(self):
        # conf_retry requires retrywindow
        config.config['taskmanager'] = {'retrywindow':60}
        
        def inner():
            pass

        # decorate and call
        newfunc = decorators.conf_retry()(inner)
        newfunc()


class SleepyDecoratorsTestSuite(unittest.TestCase):
    """Test yabibe.utils.decorators that require real gevent sleeps"""
    def test_lock(self):
        def inner():
            for i in range(100):
                gevent.sleep(0)

        # decorate and call
        newfunc = decorators.lock(3)(inner)

        # what order the greenlet intereiors should schedule
        # (greenlet_num, lock_num)
        # we check them against this to make sure lock is working
        order_pre = [ (0,0), (1,1), (2,2), (3,3), (4,3), (5,3) ]
        order_post = [ (0,2),              # we come out of task 0 first, and theres one less lock
                       (1,1),
                       (2,0),              # from here on...
                       (4,2),              # its a funny order
                       (5,1),
                       (3,0)
                     ]

        def lock_greenlet(num):
            self.assertEquals( (num,inner._CONNECTION_COUNT), order_pre.pop(0) )
            newfunc()
            self.assertEquals( (num,inner._CONNECTION_COUNT), order_post.pop(0) )

        simultaneous = 6
        gthreads = [gevent.spawn(lock_greenlet,n) for n in range(simultaneous)]
        for thread in gthreads:
            thread.join()

        # make sure the order lists are empty
        self.assertFalse(order_pre)
        self.assertFalse(order_post)
        
    def test_call_count(self):
        def inner():
            for i in range(100):
                gevent.sleep(0)

        # decorate and call
        newfunc = decorators.call_count(inner)

        # order of counts for each task. Just the count numbers
        order_pre = range(5)
        order_post = [I for I in reversed(range(5))]

        def lock_greenlet(num):
            self.assertEquals( inner._CONNECTION_COUNT, order_pre.pop(0) )
            newfunc()
            self.assertEquals( inner._CONNECTION_COUNT, order_post.pop(0) )
            
        simultaneous = 5
        gthreads = [gevent.spawn(lock_greenlet,n) for n in range(simultaneous)]
        for thread in gthreads:
            thread.join()

        # make sure the order lists are empty
        self.assertFalse(order_pre)
        self.assertFalse(order_post)

    def test_hmac_incorrect(self):
        headers = Headers()
        headers.addRawHeader('hmac-digest','bogus_hmac_header')

        class DummyRequest(object):
            pass
        
        request = DummyRequest()
        request.uri = 'http://this'
        request.headers = headers

        def inner(dummy,request):
            print request

        # we pass it our fake request and we should get back a twistedweb2.http.response object
        newfunc = decorators.hmac_authenticated(inner)
        result = newfunc(None,request)

        self.assertEquals(result.code, 401)
        buff = result.stream.read()
        text = str(buff)
        self.assertTrue('hmac-digest' in text and 'incorrect' in text)

    def test_hmac_missing_header(self):
        headers = Headers()

        class DummyRequest(object):
            pass
        
        request = DummyRequest()
        request.uri = 'http://this'
        request.headers = headers

        def inner(dummy,request):
            print request

        # we pass it our fake request and we should get back a twistedweb2.http.response object
        newfunc = decorators.hmac_authenticated(inner)
        result = newfunc(None,request)

        self.assertEquals(result.code, 400)
        buff = result.stream.read()
        text = str(buff)
        self.assertTrue('No hmac-digest header present' in text)            

    def test_hmac_correct_headers(self):
        # setup a hmac key for us
        config.config['backend'] = {'hmackey':'8c618fdf52ac6eded9311f95507ba436'}
        
        for uri in ('http://www.google.com/', 'https://localhost:8312/path/to/resource?get=var+extra&another=1','safswert?#$!&%*^&*' ):
            hmac_digest = hmac.new(config.config['backend']['hmackey']) 
            hmac_digest.update(uri)
            hmac_hex = hmac_digest.hexdigest()

            headers = Headers()
            headers.addRawHeader('hmac-digest',hmac_hex)

            class DummyRequest(object):
                pass

            request = DummyRequest()
            request.uri = uri
            request.headers = headers

            def inner(dummy,request):
                return "RESULT"

            # we pass it our fake request and we should get back a twistedweb2.http.response object
            newfunc = decorators.hmac_authenticated(inner)
            result = newfunc(None,request)

            #make sure we get what inner passed out
            self.assertEquals(result, "RESULT")

        
