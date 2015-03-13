# Introduction #

Work is currently underway to remove stackless python as a dependency for the Yabi backend by moving the coroutine implementation to greenlet. Until this work is completed stackless python is needed for running the backend.

This is a quick guide for setting up a working stackless python for running the yabi backend.

# Download #

**Stackless python 2.7.2** can be downloaded from the home page at

http://www.stackless.com/download

# Dependencies #

In order to complete a successful build of stackless python you will need to have certain libraries and their development header packages installed on your system.

## Ubuntu ##

Make sure to run

```
$ sudo apt-get install libbz2-dev libncurses5-dev libsqlite3-dev libssl-dev libreadline6-dev zlib1g-dev libtk-img-dev tk-dev libgdbm-dev
```

# Building Stackless #

  1. Uncompress the stackless tarball and change into the directory

```
$ tar xjvf stackless-272-export.tar.bz2
$ cd stackless-272-export
```

> 2. Configure the source tree

```
$ ./configure
```

> 3. run the make command to build the stackless python binary

```
$ make
```

If it has completed the build successfully the final part of the output will look like the following:

```
Python build finished, but the necessary bits to build these modules were not found:
bsddb185           dl                 imageop         
sunaudiodev                                           
```

These modules are not necessary for running yabi backend.

> 4. Run 'make install' as root to install stackless

```
$ sudo make install
```

# Prevent Python Version Conflicts #

The configure script by default places the stackless python install in /usr/local, so the path to the binary is /usr/local/bin/python. If you have your system path setup so that /usr/local/bin is searched before /usr/bin, then installing stackless here will mean that every time you run something under 'python' you will be using stackless, rather than the system python.

The [Stackless FAQ](http://www.stackless.com/wiki/FAQ) recommends on unix systems that you rename the stackless python executable to spython to prevent accidental confusion

```
$ sudo mv /usr/local/bin/python /usr/local/bin/spython
```

Once this is done check your python commands launch the right python.

For example, the standard python....

```
$ python
Python 2.6.6 (r266:84292, Dec 26 2010, 22:31:48) 
[GCC 4.4.5] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> [ctrl+D]
```

and stackless python...

```
$ spython
Python 2.7.2 Stackless 3.1b3 060516 (default, Jan 12 2012, 16:08:26) 
[GCC 4.4.5] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> [ctrl+D]
```

This is the setup of stackless that is assumed in the Quickstart guide.