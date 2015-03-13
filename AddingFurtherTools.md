From the examples given in this wiki you should be able to get most tools up and running. It is possible also to import/export tools in json format.

#### Exporting tools in JSON ####
In the tool listing under Yabi --> Tools you'll see the link called "View". This will give you and overview of the tool including a link to View JSON. Clicking on View JSON will present a window with a plain text JSON representation of the tool.

![http://yabi.googlecode.com/hg/images/admin_viewtool.png](http://yabi.googlecode.com/hg/images/admin_viewtool.png)

#### Importing tools in JSON ####

If you have the JSON for a tool (see attached JSON files on this page) you can use the Add Tool page to add in the tool.

Go to: https://127.0.0.1/yabiadmin/admin/addtool/ and paste in your JSON.

![http://yabi.googlecode.com/hg/images/admin_addtool.png](http://yabi.googlecode.com/hg/images/admin_addtool.png)

Once you have done this the tool will be added and you'll be shown the tool edit page. You will need to check all the details, usually you will need to change the backends and check things like the module settings. You will have to add the new tool to the appropriate Tool Group etc.

![http://yabi.googlecode.com/hg/images/admin_new_blast.png](http://yabi.googlecode.com/hg/images/admin_new_blast.png)

### Tool Json for importing using Add Tool ###
[Blast JSON](http://yabi.googlecode.com/hg/json/blast.json)