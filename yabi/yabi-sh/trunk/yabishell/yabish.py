from argparse import ArgumentParser
from collections import namedtuple
import json
import os
import readline
import sys
import uuid

from yaphc import Http, UnauthorizedError, PostRequest, GetRequest
from yabishell import errors
from yabishell import actions

# TODO config file
YABI_DEFAULT_URL = 'https://faramir/yabife/snapshot/'

def main():
    debug = False
    yabi = None
    try:
        argparser = ArgumentParser(description='YABI shell', add_help=False)
        argparser.add_argument("--yabi-debug", action='store_true', help="Run in debug mode")
        argparser.add_argument("--yabi-bg", action='store_true', help="Run in background")
        argparser.add_argument("--yabi-url", help="The URL of the YABI server", default=YABI_DEFAULT_URL)
        options, args = argparser.parse_known_args()        

        args = CommandLineArguments(args)

        if args.no_arguments or args.first_argument in ('-h', '--help'):
            print_usage()
            return

        debug = options.yabi_debug
        yabi = Yabi(url=options.yabi_url, bg=options.yabi_bg, debug=options.yabi_debug)
        stagein = (len(args.local_files) > 0)
        if stagein:
            stageindir_uri, files_uris = yabi.stage_in(args.local_files)
            args.substitute_file_urls(files_uris)
        action = yabi.choose_action(args.first_argument)
        action.process(args.rest_of_arguments)
        if stagein:
            yabi.delete_dir(stageindir_uri)

    except Exception, e:
        print_error(e, debug)
    finally:
        if yabi is not None:
            yabi.session_finished()

def human_readable_size(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

class StageIn(object):
    def __init__(self, yabi, files):
        self.yabi = yabi
        self.files = files
   
    @property
    def debug(self):
        return self.yabi.debug
 
    def do(self):
        files_to_uris = {}
        alldirs, allfiles, total_size = self.collect_files()
        stagein_dir, dir_uris = self.create_stagein_dir(alldirs)
        print "Staging in %s in %i directories and %i files." % (
                human_readable_size(total_size), len(alldirs), len(allfiles))
        files_to_uris.update(dir_uris)
        for f in allfiles:
            rel_path, fname = os.path.split(f.relpath)
            file_uri = self.stagein_file(f, stagein_dir + rel_path)
            files_to_uris[f.relpath] = file_uri
        print "Staging in finished."
        return stagein_dir, files_to_uris

    def collect_files(self):
        allfiles = []
        alldirs = []
        total_size = 0
        RelativeFile = namedtuple('RelativeFile', 'relpath fullpath')
        for f in self.files:
            if os.path.isfile(f):
                allfiles.append(RelativeFile(os.path.basename(f), f))
                total_size += os.path.getsize(f)
            if os.path.isdir(f):
                path, dirname = os.path.split(f)
                alldirs.append(RelativeFile(dirname, f))
                for root, dirs, files in os.walk(f):
                    for adir in dirs:
                        dpath = os.path.join(root, adir)
                        rel_dir = dpath[len(f)-1:] 
                        alldirs.append(RelativeFile(rel_dir, dpath))
                    for afile in files:
                        fpath = os.path.join(root, afile)
                        rpath = fpath[len(f)-1:]
                        allfiles.append(RelativeFile(rpath, fpath))
                        total_size += os.path.getsize(fpath)
        return alldirs, allfiles, total_size

    def create_stagein_dir(self, dir_structure):
        uri = 'ws/yabish/createstageindir'
        params = {'uuid': uuid.uuid1()}
        for i,d in enumerate(dir_structure):
            params['dir_%i' % i] = d.relpath
        resp, json_response = self.yabi.post(uri, params)
        stageindir_uri = json.loads(json_response)['uri']
        dir_uri_mapping = {}
        for d in dir_structure:
            dir_uri = stageindir_uri + d.relpath
            if not dir_uri.endswith('/'):
                dir_uri += '/'
            dir_uri_mapping[d.relpath] = dir_uri
        return stageindir_uri, dir_uri_mapping

    def stagein_file(self, f, stagein_dir):
        uri = 'ws/fs/put'
        fname = os.path.basename(f.relpath)
        finfo = (fname, fname, f.fullpath)
        params = {'uri': stagein_dir}
        print '  Staging in file: %s (%s).' % (
                f.relpath,human_readable_size(os.path.getsize(f.fullpath)))
        resp, json_response = self.yabi.post(uri, params, files=[finfo])
        return json.loads(json_response)['uri']

class Yabi(object):
    def __init__(self, url, bg=False, debug=False):
        self.http = Http(workdir=os.path.expanduser('~/.yabish'), base_url=url)
        self.username = None
        self.run_in_background = bg
        self.debug = debug
        if self.debug:
            import httplib2
            httplib2.debuglevel = 1

    def delete_dir(self, stageindir):
        rmdir = actions.Rm(self)
        rmdir.process([stageindir])

    def stage_in(self, files):
        stagein = StageIn(self, files)
        return stagein.do()

    def login(self):
        import getpass
        system_user = getpass.getuser()
        username = raw_input('Username (%s): ' % system_user)
        if '' == username.strip():
            username = system_user
        password = getpass.getpass()
        login_action = actions.Login(self)
        return login_action.process([username, password])

    def request(self, method, url, params=None, files=None):
        if params is None:
            params = {}
        try:
            if method == 'GET':
                request = GetRequest(url, params)
            elif method == 'POST':
                request = PostRequest(url, params, files=files)
            else:
                assert False, "Method should be GET or POST"
            if self.debug:
                print '=' * 5 + 'Making HTTP request'
            resp, contents = self.http.make_request(request)
            if self.debug:
                print '=' * 5 + 'End of HTTP request'
        except UnauthorizedError:
            if not self.login():
                raise StandardError("Invalid username/password")
            resp, contents = self.http.make_request(request)
        if int(resp.status) >= 400:
            raise errors.CommunicationError(int(resp.status), url, contents)
        return resp, contents

    def get(self, url, params=None):
        return self.request('GET', url, params)

    def post(self, url, params=None, files=None):
        return self.request('POST', url, params=params, files=files)

    def choose_action(self, action_name):
        class_name = action_name.capitalize()
        try:
            cls = getattr(sys.modules['yabishell.actions'], class_name)
        except AttributeError:
            if self.run_in_background:
                cls = actions.BackgroundRemoteAction
            else:
                cls = actions.ForegroundRemoteAction
        return cls(self, name=action_name)

    def session_finished(self):
        self.http.finish_session()

def print_usage():
    print >> sys.stderr, '''
Welcome to Yabish!

Command should be used like BLA BLA BLA
'''

def print_error(error, debug=False):
    print >> sys.stderr, 'An error occured: \n\t%s' % error
    if debug:
        print >> sys.stderr, '-' * 5 + ' DEBUG ' + '-' * 5
        import traceback
        traceback.print_exc()

class CommandLineArguments(object):
    def __init__(self, args):
        self.args = args

    @property
    def no_arguments(self):
        return len(self.args) == 0

    @property
    def first_argument(self):
        return self.args[0]

    @property
    def rest_of_arguments(self):
        return [] if len(self.args) <= 1 else self.args[1:]

    @property
    def local_files(self):
        return filter(lambda arg: os.path.isfile(arg) or os.path.isdir(arg), self.args)

    def substitute_file_urls(self, urls):
        def file_to_url(arg):
            new_arg = arg
            if os.path.isfile(arg) or os.path.isdir(arg):
                new_arg = urls.get(os.path.basename(arg), arg)
            return new_arg 
        self.args = map(file_to_url, self.args)

