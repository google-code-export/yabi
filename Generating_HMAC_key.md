#### 1. Generate a secret key ####

Using ps and piping to md5sum is a quick way to generate a random hex string

` $ ps auxwww | md5sum `

take that hex string and remember it. It's your secret HMAC key.


#### 2. Add the key in admin ####

In the relevant settings file (i.e. /usr/local/etc/ccgapps/appsettings/yabiadmin/prod.py) add HMAC\_KEY setting and set it to this key. eg.

` HMAC_KEY = "hex string here in quotes" `


#### 3. Add the key to yabi.conf (i.e. /etc/yabi/yabi.conf) ####

in the [backend](backend.md) section add:

`hmackey: hex_key_here_unquoted`


#### 4. Change the yabi.conf setting to use https ####

The admin section should be changed to a https:// url

eg.

`admin: https://faramir.localdomain:443/yabiadmin/snapshot/`


#### 5. Restart yabiadmin and backend and test. ####