Now that you have set up Users, Backends and Credentials you'll be able to add tools. The first tool you tackle should be the file select tool as that will be needed for most workflows. It is also slightly different from other tools in that it does not "execute".

From the Yabi section click to Add a tool. Fill in the tool like this.

![http://yabi.googlecode.com/hg/images/admin_addtool1.png](http://yabi.googlecode.com/hg/images/admin_addtool1.png)

Normally when configuring a tool you select the appropriate execution and filesystem backends. In the case of the file select tool we use the Null Backends we made earlier.


![http://yabi.googlecode.com/hg/images/admin_addtools2.png](http://yabi.googlecode.com/hg/images/admin_addtools2.png)

In this image we show the parameters for this tool. This is an example of a positional parameter we have named "files". It is positional because we have chosen valueOnly as a switchUse. You'll have to follow your nose a little on description of parameters.