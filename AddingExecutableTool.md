We now have an execution backend set up using ssh+qsub so we will add a tool that can run on it. In this case we will just add a tool that allows us to run the unix command "hostname". Add a new tool and set it up like this:

![http://yabi.googlecode.com/hg/images/admin_hostname.png](http://yabi.googlecode.com/hg/images/admin_hostname.png)

NB: I have selected the ssh+qsub backend that I created earlier and the scp backend for the same machine as execution and filesystem backends respectively.

After you follow the steps to make this tool available to the users ([wiki:addingToolsets Adding Toolgroups and Toolsets]) you should be able to log in to the front end and run a workflow with just the hostname tool and get a result.