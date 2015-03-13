The diagram below is an overview of the Yabi architecture. There are four main components:
  1. The client (typically a web browser)
  1. The front end application
  1. The middleware appliance
  1. The Resource manager

Theses are explained below in more detail.

![http://yabi.googlecode.com/hg/images/yabi-arch.png](http://yabi.googlecode.com/hg/images/yabi-arch.png)

## Client ##

The client is typically a web browser, although a command line client also exists. The command line client interacts with the front end application in the same way as a web browser, that is:
  * cookies are used to maintain a user session
  * all traffic is via HTTPS
  * users are required to log in to activate a session

## Front end application ##

The front end application is a Python web application running under Apache 2 via mod\_wsgi. HTTP and HTTPS are required, although the application will insist on HTTPS and redirect any HTTP requests to HTTPS.

The front end application is intended to be run on an Internet facing server as it serves the HTML/CSS/Javascript application that users typically interact with as well as a REST style interface for the command line client. Naturally, it can be deployed on an internal network if access over the Internet is not desired.

The application runs under Apache using mod\_wsgi so does not require any additional accounts, privileges or ports to be created/opened.

## Middleware appliance ##

The middleware appliance is a Python web application running under Apache 2 via mod\_wsgi. HTTP and HTTPS are required, although the application will insist on HTTPS and redirect any HTTP requests to HTTPS.

The middleware appliance is intended to be run on an internal network that is not exposed to the Internet. This is not an absolute requirement and can be run on the same host as the front end appliance if required to do so. It has a web based application to allow system administrators to manage the appliance and also exposes a REST style HTTP interface to the front end application. For this reason the front end application must be able to make HTTP (strictly speaking HTTPS) calls to the middleware appliance.

The application runs under Apache using mod\_wsgi so does not require any additional accounts, privileges or ports to be created/opened.

## Resource manager ##

The resource manager is a backend server daemon written in Stackless Python and makes use of the Twisted  Python networking stack. It runs as a dedicated non-root user and is '''not''' intended to be network accessible by users.

The resource manager is responsible for the communication with individual data and compute resources.