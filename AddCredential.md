#### Adding Credentials for Users ####

Select Add Credential and fill the page in like this. There are several ways of doing this, in this example we are adding an SSH private key and password.

If you select Encrypt on Login, then the next time the user logs in the password and key will be encrypted using their login password as the key. It will then be stored encrypted in the database and decrypted each time the user logs in.

At the moment the expiry date is required. If the key does not have one just pick a date far in the future.

![http://yabi.googlecode.com/hg/images/admin_credential.png](http://yabi.googlecode.com/hg/images/admin_credential.png)

There are also several actions that can be taken on the credential screen, to encrypt, decrypt etc.

![http://yabi.googlecode.com/hg/images/admin_encryt_actions.png](http://yabi.googlecode.com/hg/images/admin_encryt_actions.png)

It is possible to add credentials already encrypted as long as you check the Encrypted checkbox so that Yabi knows that the credentials are looking at are encrypted. To do this you might do this:


```
cd /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/virtualpython/bin/python 
>>> from crypto import aes_enc_hex
>>> crypttext = aes_enc_hex('mysecrettext', 'mypassword', linelength=80)
>>> print crypttext
81d2f953ca7290e7b213da004273b12d
```


Here you would replace 'mysecrettext' and 'mypassword' with appropriate values. The password '''must''' be the same as the user will login in with.