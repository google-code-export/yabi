There are two Postgresql databases associated with Yabi.  One services the front end application and contains a small amount of information about the users who are allowed to log on and use yabi.  The other is more substantial and holds setup information for backends, encrypted credentials for access to resources and information about workflows that are running or have finished.

The attached database dumps of skeleton databases to get you started running yabi make a few assumptions (all of the below code is entered into the psql Postgresql client to demonstrate, any other method of creating database users and databases will have the same result):

  * You have created a database user for each application and they are called yabiapp and yabifeapp for the yabi database and yabi front end database respectively.
eg.
```
CREATE USER yabiapp WITH PASSWORD 'placeholder';
CREATE USER yabifeapp WITH PASSWORD 'placeholder';
```
  * You have created a database for each application and the database is owned by the appropriate user.
eg.
```
CREATE DATABASE live_yabi WITH OWNER 'yabiapp';
CREATE DATABASE live_yabife WITH OWNER 'yabifeapp';
```
  * You have given access to your database server to your web server.  This is achieved by editing the pg\_hba.conf file for Postgresql (details here http://www.postgresql.org/docs/8.3/interactive/auth-pg-hba-conf.html).  While specific configuration will be site dependent and is out of the scope of this document if you are having trouble with this please contact us at yabi@ccg.murdoch.edu.au and we can help you out.

To install the database dump files simply connect to the correct database and pipe the correct file into it.
Examples (from the command line)
  * If you are running the command from the database server itself while logged in as the Postgresql admin user (using CentOS/Redhat Postgresql RPMS this will be the user postgres)
```
psql live_yabi < skel_yabi.RELEASE_60.sql
<-- Output here, be aware of any errors -->
psql live_yabife < skel_yabife.RELEASE_37.sql 
<-- Output here, be aware of any errors -->
```
  * If you are running the command from the web server logging in with the correct user
```
psql -h databasehostname -U yabiapp live_yabi < skel_yabi.RELEASE_60.sql
<enter password>
<-- Output here, be aware of any errors -->
psql -h databasehostname -U yabifeapp live_yabife < skel_yabife.RELEASE_37.sql
<enter password>
<-- Output here, be aware of any errors -->
```

If you have used different database usernames expect errors here.  If you have any issues please contact us at yabi@ccg.murdoch.edu.au and we will assist.


#### Initial Database schema files and patchs ####
  * http://yabi.googlecode.com/hg/sql/skel_yabi.RELEASE_60.sql
  * http://yabi.googlecode.com/hg/sql/skel_yabife.RELEASE_37.sql
  * http://yabi.googlecode.com/hg/sql/037_alter_file_extensions_to_be_globs.sql
  * http://yabi.googlecode.com/hg/sql/038_alter_file_extension_stardotstar_to_be_star.sql
  * http://code.google.com/p/yabi/source/browse/sql/039_user_profile.sql
  * http://code.google.com/p/yabi/source/browse/sql/040_add_submission_script_fields.sql