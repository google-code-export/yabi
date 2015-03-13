Before a user will see a tool in the front end you need to set up their access to it using Toolsets and Toolgroups.

##### Toolsets #####

![http://yabi.googlecode.com/hg/images/admin_addtoolset.png](http://yabi.googlecode.com/hg/images/admin_addtoolset.png)

Adding toolsets allows grouping of users to determine which tools they have access to. We typically have an allusers set, a dev set and maybe a testing set. On top of that we might have sets for individual labs etc.


##### Toolgroups #####

![http://yabi.googlecode.com/hg/images/admin_addtoolgroup.png](http://yabi.googlecode.com/hg/images/admin_addtoolgroup.png)

Toolsgroups determine how tools are grouped in the Front End UI. The groups that you add here will be reflected in the menu on the left of the Front End.

So in this image we are:
  * adding a toolgroup called "select data"
  * adding the fileselector tool to that grouping and granting access to the allusers toolset.

NB: If a user has access to a tool more than once through a couple of toolsets, they will only see the tool once in the front end.