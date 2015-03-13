This is a linking table between a User and a Backend, used simply because a user may have one credential (say an SSH key) that is valid across multiple backend.

  * Add a BackendCredential and select the Backend and Credentials you have made.
  * Add the users home directory or subdirectory
  * Check Visible so the backend will appear to the user.
  * Select Default Stageout to indicate that this user's job results should stageout to this filesystem

![http://yabi.googlecode.com/hg/images/admin_backend_credential.png](http://yabi.googlecode.com/hg/images/admin_backend_credential.png)

At this point if everything has worked the user should be able to log into the Front End and under the Files tab they will be able to see and view files on the SSH backend you have just set up.

  * Further backends can be set up based on this example.
  * Globus backends will require cert as well as key.
  * make sure each user has one Default Stageout only.