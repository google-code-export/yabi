To get things up and running the best idea is to set up a backend that you can connect to via SSH. You should be able to connect via the command line using ssh keys.

In Yabi there are two types of backend - execution and storage. As the names suggest, an execution backend is where tasks will be run, and a storage backend is where files are stored.

##### Setting up a SSH storage backend #####

Click on Backends under Yabi heading and add a backend. Set it up like this (with you own server details of course):

![http://yabi.googlecode.com/hg/images/admin_adding_backend.png](http://yabi.googlecode.com/hg/images/admin_adding_backend.png)

The Lcopy and Link checkboxes come into play if an execution and storage backend have a shared filesystem. You can set this backend up to use local copy and ln if a tool requests that.

#### A note about the Path field ####
Yabi uses the information in the Backend record and the Backend Credential record to construct a URI that it uses to access data or execution resources. In setting up this backend I am adding /export/home/ to the path. This is where all the yabi users on this machine will find their home directories (on this machine, it is a non-standard location). So the backend can construct a partial URI from the scheme, hostname and path fields that will look like this:

```
scp://sooty.localdomain/export/home/
```

In a later step ([wiki:addBackendCredential Adding the link between user, credential and backend]) we will setup a Backend Credential. In that step we will add to the homedir field /tech/macgregor/yabi. This leads to my home directory (tech/macgregor/) and then limits yabi access to a directory with in it (yabi/).

So when Yabi needs to access files on that backend it combines the fields from the Backend and the Backend Credential records to derive a full URI:

```
scp://sooty.localdomain/export/home/tech/macgregor/yabi/
```

'''Please note:''' While Yabi refers to the directory on the Backend Credential record as homedir this can really point to any directory the user has access to.