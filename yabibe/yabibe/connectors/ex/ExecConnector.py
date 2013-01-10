"""Base class for FSConnector"""
from yabibe.exceptions import NotImplemented, ExecutionError
import pickle, os

class ExecConnector(object):
    """Base class for a filesystem connector"""
    
    def __init__(self):
        self.childenv = {}
    
        
        self._running = {}
        
    def add_running(self, rid, details):
        self._running[rid]=details.copy()

    def get_running(self, rid):
        return self._running[rid]
        
    def update_running(self, rid, updatehash):
        self._running[rid].update(updatehash)
        
    def del_running(self, rid):
        del self._running[rid]

    def get_all_running(self):
        return self._running
        
    def save_running(self, filename):
        """save the running job details to a file so we can restore the details we need on startup to resume connections to tasks"""
        with open(filename,'wb') as fh:
            fh.write(pickle.dumps(self._running))
    
    def load_running(self, filename):
        """return the running set details from a file"""
        with open(filename,'rb') as fh:
            self._running = pickle.loads(fh.read())
    
    def shutdown(self, directory):
        print self.__class__.__name__+"::shutdown(",directory,")"
        self.save_running(os.path.join(directory,"exec-"+self.__class__.__name__))        
        
    def startup(self, directory):
        print self.__class__.__name__+"::startup(",directory,")"
        filename = os.path.join(directory,"exec-"+self.__class__.__name__)
        if os.path.exists(filename):
            self.load_running(filename)        
    
    def run(self, *args, **kwargs):
        """Run a job on a backend. extra params can be passed in that are specific to a backend. They should all have defaults if ommitted
        
        command is the command to run
        working is the working directory
        address is the host on which to run the command
        
        callback is a callable that is called with the status changes for the running job
        
        """
        #print "The run method for this backend is not implemented"
        raise NotImplemented("The run method for this backend is not implemented")
    
    def SetEnvironment(self, env):
        """Pass in the environment setup you want any child processes to inherit"""
        self.childenv = env.copy()
        
        