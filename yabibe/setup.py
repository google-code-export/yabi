import setuptools
import os
from setuptools import setup, find_packages

setup(name='yabibe',
    version='0.2',
    description='Yabi Backend',
    long_description='Yabi back end service',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    packages=['yabibe',
              'yabibe.conf',

              ],
    package_data={'yabibe': ['conf/*.conf']},
    zip_safe=False,
    scripts=['scripts/yabibe'],
    install_requires=[
        'pyOpenSSL',
        'pycrypto',
        'paramiko',
        'Mako',
        'MarkupSafe',
        'Twisted',
        'TwistedWeb2==1.0.0',
        'setproctitle',
        'wsgiref',
        'zope.interface',
        'gevent',
        'greenlet',
        'psutil',
        'boto',
        'requests',
    ],
    dependency_links = [
          "http://repo.ccgapps.com.au",
          "https://twisted-web2.googlecode.com/files/TwistedWeb2-1.0.0.tar.gz"
    ],      
)
