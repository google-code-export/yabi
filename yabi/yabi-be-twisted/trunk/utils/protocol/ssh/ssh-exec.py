#!/usr/bin/python
# -*- coding: utf-8 -*-
### BEGIN COPYRIGHT ###
#
# (C) Copyright 2011, Centre for Comparative Genomics, Murdoch University.
# All rights reserved.
#
# This product includes software developed at the Centre for Comparative Genomics 
# (http://ccg.murdoch.edu.au/).
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, YABI IS PROVIDED TO YOU "AS IS," 
# WITHOUT WARRANTY. THERE IS NO WARRANTY FOR YABI, EITHER EXPRESSED OR IMPLIED, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT OF THIRD PARTY RIGHTS. 
# THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF YABI IS WITH YOU.  SHOULD 
# YABI PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR
# OR CORRECTION.
# 
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, OR AS OTHERWISE AGREED TO IN 
# WRITING NO COPYRIGHT HOLDER IN YABI, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR 
# REDISTRIBUTE YABI AS PERMITTED IN WRITING, BE LIABLE TO YOU FOR DAMAGES, INCLUDING 
# ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE 
# USE OR INABILITY TO USE YABI (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR 
# DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES 
# OR A FAILURE OF YABI TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER 
# OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
# 
### END COPYRIGHT ###

# ssh execution helper. Can deal with passphrased keys and passwords and stuff

import readline
import sys, re, os, time
from optparse import OptionParser
import subprocess
import pexpect
import StringIO

for delkey in ['DISPLAY','SSH_AGENT_PID','SSH_AUTH_SOCK']:
    if delkey in os.environ:
        del os.environ[delkey]

def eprint(text):
    sys.stderr.write(text)
    sys.stderr.write("\n")

SSH = "/usr/bin/ssh"
BLOCK_SIZE = 1024
TIMEOUT = 3

TAKE_STDIN = False                          # if we just close stdin after reading passphrase. or if we read stdin to finish and pipe that through.
STDIN_BLOCKSIZE = 8192                      # 8k chunks

L2R = 1
R2L = 2
direction = None

parser = OptionParser()
parser.add_option( "-i", "--identity", dest="identity", help="RSA keyfile" )
parser.add_option( "-C", "--compress", dest="compress", help="use ssh stream compression", action="store_true", default=False )
parser.add_option( "-P", "--port", dest="port", help="port to connect to ssh on" )
parser.add_option( "-o", "--stdout", dest="stdout", help="filename for standard out", default=None )
parser.add_option( "-e", "--stderr", dest="stderr", help="filename for standard error",default=None )
parser.add_option( "-x", "--execute", dest="execute", help="command to execute", default="hostname" )
parser.add_option( "-w", "--working", dest="working", help="working directory", default=None )
parser.add_option( "-s", "--pipestdin", dest="pipestdin", help="pipe stdin to remote process", action="store_true", default=False )
parser.add_option( "-v", "--verbose", dest="verbose", help="be verbose", action="store_true", default=False )
parser.add_option( "-S", "--pipestdout", dest="pipestdout", help="pipe stdout from remote process to local shell", action="store_true", default=False )
parser.add_option( "-K", "--key",   dest="stdoutkey", 
                                    help="pipe stdout from remote process to local shell after this key string is recieved. This can be used to get the remote shell tasks output but not SSH's output", 
                                    default=None)

(options, args) = parser.parse_args()

#print "options",options
#print "args",args

if len(args)!=1:
    eprint("Error: Must specify user@host on command line")
    sys.exit(2)
    
remote_command = options.execute
stdout = options.stdout
stderr = options.stderr
    
extra_args = []
if options.identity:
    extra_args.extend(["-i",options.identity])
if options.compress:
    extra_args.extend(["-C"])
if options.port:
    extra_args.extend(["-p",options.port])
if options.pipestdin:
    TAKE_STDIN = True
    
password = sys.stdin.readline().rstrip('\n')

user, host = args[0].split('@',1)

# sanity check our command. If there are quotes (that are unescaped) the outermost ones must be doubles
quotes = [X for N,X in enumerate(remote_command) if (X=='"' or X=="'") and N>=1 and remote_command[N-1]!='\\']

#if len(quotes):
    #assert quotes[0]=='"' and quotes[-1]=='"', "Quotes in command must be doublequote outermost"

if stdout or stderr:
    ssh_command = extra_args+["%s@%s"%(user,host),"cd \"%s\" && %s 1>%s 2>%s"%(options.working,remote_command,stdout,stderr)]
else:
    if options.working:
        ssh_command = extra_args+["%s@%s"%(user,host),"cd \"%s\" && %s"%(options.working,remote_command)]
    else:
        ssh_command = extra_args+["%s@%s"%(user,host),remote_command]

#eprint("SSH Command: %s"%(ssh_command))
if options.pipestdout or options.pipestdin:

    child = pexpect.spawn(SSH, args=ssh_command)

    if options.pipestdout:
        child.logfile_read = sys.stdout

    expect_list = ["passphrase for key .+:","password:","Permission denied",pexpect.EOF,"Are you sure you want to continue connecting (yes/no)?",pexpect.TIMEOUT]
    if options.stdoutkey:
        expect_list.append(options.stdoutkey)

    res = 0
    while res!=2:
        res = child.expect(expect_list,timeout=TIMEOUT)
        
        #
        # passphrase or password
        #
        if res<=1:                                         
            # send password
            if options.verbose:
                eprint("sending password: %s"%password)
            child.sendline(password)
            
        #
        # permission denied
        #
        elif res==2:
            # password failure
            eprint("Permission denied")
            sys.exit(1)
        
        #
        # EOF from destination client
        #
        elif res==3:
            child.delaybeforesend=0
            #eprint("sending EOF")
            child.sendeof()
            if child.isalive():
                #eprint("waiting")
                child.wait()
            
            if child.exitstatus==255:
                eprint("SSH transport failed")
            elif child.exitstatus:
                eprint("Child exited unexpectedly with exit status %s"%child.exitstatus)
            sys.exit(child.exitstatus)
        
        #
        # Are you sure you want to connect?
        #
        elif res==4:
            eprint("Error: RSA public key not in known hosts")
            child.sendline("no\n")
        
        #
        # TIMEOUT
        #
        elif res==5:
            if TAKE_STDIN:
                # after sending password, if we have to send stdin data, then send it all through straight after the passphrase/password dialog
                
                #
                # PYTHON BUG affects us here. We do a workaround
                # http://bugs.python.org/issue1633941
                #
                
                while True:
                    chunk = sys.stdin.readline()
                    child.send(chunk)
                    if not chunk:                     # workaround
                        break
                    
                
                # close stdin
                child.sendeof()
            
                # now switch on stdout echo so we can send back our command result
                child.logfile_read = sys.stdout
            
        #
        # match the log trigger key
        #
        elif res==6:
            child.logfile_read = sys.stdout

        else:
            eprint ("Uknown error. Fatal. Blech. Im dead")
            
    sys.exit(0)
        
        
##
## simple command running
##
TIMEOUT = 0.1

child = pexpect.spawn(SSH, args=ssh_command)
child.logfile_read = sys.stdout
res = 0
while res!=2:
    res = child.expect(["passphrase for key .+:","password:", "Permission denied",pexpect.EOF,pexpect.TIMEOUT],timeout=TIMEOUT)
    if res<=1:
        # send password
        #eprint("sending password")
        child.sendline(password)
    elif res==2:
        # password failure
        eprint("Permission denied")
        sys.exit(1)
        
    elif res==3:
        child.delaybeforesend=0
        #eprint("sending EOF")
        child.sendeof()
        if child.isalive():
            #eprint("waiting")
            child.wait()
        
        if child.exitstatus==255:
            eprint("SSH transport failed")
        else:
            eprint("Child exited unexpectedly with exit status %s"%child.exitstatus)
        sys.exit(child.exitstatus)
    
    else:
        # EOF or timeout
        pass