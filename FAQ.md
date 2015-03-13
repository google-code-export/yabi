## Frequently Asked Questions ##

#### I'm getting errors about not being able to access the logs directory, why? ####
An earlier RPM did not include the necessary logs directory so you should check this directory exists and is owned by apache

```
/usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/
```

If it is not you should do this:

```
mkdir /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/
chown apache:apache /usr/local/python/ccgapps/yabiadmin/release/yabiadmin/logs/

```


---


#### Why am I getting an error about accessing a "store" directory? ####
An earlier RPM did not make a required store directory. Check for this and that it is owned by apache.

```
/usr/local/python/ccgapps/yabiadmin/store/
```

If necessary:

```
mkdir /usr/local/python/ccgapps/yabiadmin/store/
chown apache:apache /usr/local/python/ccgapps/yabiadmin/store/
```


---


#### Updating seems to have removed my changes to the Frontend and Admin settings.py files. Where have they gone? ####
New releases are placed in parallel directories. You'll need to copy across any changes you've made to settings.py files. See [Updating Yabi](Updating.md) for details.


---


#### How does Yabi handle the URI construction with the Backend and Backend Credential records? ####
See this note  [the Path field on Backends](AddBackend#AnoteaboutthePathfield.md) for details.


---

#### I get an error when uploading a file and the logs indicate a key error with 'Cookie' - what's happening? ####
At the moment you must have a / at the end of the appliance name in the front end admin, or this error will occur. See: [Associating a User with an Appliance in the Front End](AddAppliance.md)

---


#### I'm trying to add a tool that takes an input directory which it will use as a working directory, how do I do this? ####

It helps in setting up these tools to know that Yabi always behaves in the same way when executing jobs.

1. It creates a temp directory with a unique name
2. In that directory it creates an input and an output directory
3. It stages all input files into the input directory
4. It cds to the output directory and runs the command
5. It stages out whatever is in the output directory

So in Yabi we don't have an option to pass in dir names as the command always runs in the output dir with inputs from the inputs dir.

In the case of such tools you could write a  wrapper (in python etc) to move the input files to the output direrctory. Then you specify the inputdir to be . The other option is to use this in the command field:

cp ../input/**. ; command\_to\_be\_run**

We would typically then set the tool up so the parameter specifying . as the working directory was hidden to the user.