Next you will need to add users to the Admin at this address (or similar):

https://127.0.0.1/yabiadmin/

You will need to add each user that wants access to Yabi. You should already have added them to the Front End. If you are using the database for authentication you must ensure that the username and password supplied to the Front End and the Admin are '''exactly''' the same. Under the Auth section choose add user and add them in the same way you did in the front end.

Now that you have added a user you should be able to log into the front end (you may not see much yet). The front end authenticates against it's own database (or ldap, etc) then looks up which admin/appliance the user is bound to. It then makes a secure connection to that appliance using the same username and password. This is why you need to set up the user in both places before it is possible to log into the Front End.

Next you should also add a user record under the Yabi User section. Usually you would use the same username here as you did elsewhere.