Yabi comes "out-of-the-box" with many settings set to development levels. For instance DEBUG is turned on and SSL\_ENABLED is turned off.

If you are rolling Yabi out on to production servers **you must take care to change your settings to appropriate values**.

Your primary guide should be the Django documentation, in particular the settings reference, where many best practice guidelines are provided.

https://docs.djangoproject.com/en/dev/ref/settings/

In particular you should also focus on these specific settings for each component. If these are not set correctly the Frontend Login page will display a warning message.

#### Yabi Frontend ####
```
SSL_ENABLED = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
DEBUG = False
SECRET_KEY - set to your own unique value
YABIADMIN_SERVER - using https not http
```