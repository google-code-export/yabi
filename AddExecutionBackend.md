Next we are going to add an execution backend so we can run some jobs. In this example we are going to use Torque qsub via ssh. In this way we do not need to have torque and qsub set up on the same box as Yabi. Instead we just need to have our ssh credentials set up to access the execution host.

##### Add the execution backend #####

First up we add an execution backend using Torque ssh+qsub. Note that we use port 22 because we are accessing the machine via ssh.

![http://yabi.googlecode.com/hg/images/admin_ssh_qsub.png](http://yabi.googlecode.com/hg/images/admin_ssh_qsub.png)

##### Add the filesystem backend #####

Next we add the same machine as a filesystem backend so we can stage files in and out with scp, again using port 22.

![http://yabi.googlecode.com/hg/images/admin_scp_on_xe.png](http://yabi.googlecode.com/hg/images/admin_scp_on_xe.png)

##### Set up backend credentials for both of the above #####
For each user we add their public key to the machine, then we can set up a ssh credential for them ([Adding a Credential](AddCredential.md)). After that we can set up backend credentials for each of the above backends.

![http://yabi.googlecode.com/hg/images/admin_backend_ssh_qsub.png](http://yabi.googlecode.com/hg/images/admin_backend_ssh_qsub.png)
![http://yabi.googlecode.com/hg/images/admin_backend_scp_xe.png](http://yabi.googlecode.com/hg/images/admin_backend_scp_xe.png)