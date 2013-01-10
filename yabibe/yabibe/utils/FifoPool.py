import os
import tempfile
import weakref

from yabibe.conf import config


FIFO_MOD = 0666

class FifoPool(object):
    """FifoPool is a pool of fifo objects. This allows us to quickly ascertain how many transfers are going on.
    This is where fifo's are created and allocated, and also where they are cleaned up."""
    
    def __init__(self, storage=None):
        if storage:
            assert os.path.exists(storage) and os.path.isdir(storage), "Storage directory %s does not exist"%storage
            self.storage = storage
        else:
            self.storage = None
            
        self._fifos={}
        
    def make_fifo_storage(self):
        """makes a directory for storing the fifos in"""
        directory = config.config['backend']['fifos']
        if not directory:
            self.storage = tempfile.mkdtemp(prefix="yabi-fifo-")
        else:
            self.storage = directory
        #print "=================> FifoPool created in",self.storage
    
    def make_fifo(self, prefix="fifo_",suffix=""):
        """make a fifo on the filesystem and return its path"""
        filename = tempfile.mktemp(suffix=suffix, prefix=prefix, dir=self.storage)                # insecure, but we dont care
        os.umask(0)
        os.mkfifo(filename, FIFO_MOD)
        return filename
    
    def get(self):
        """return a new fifo path"""
        fifo = self._make_fifo()
        self._fifos[fifo]=[]
        return fifo
        
    def weak_link(self, fifo, *procs):
        """Link the running proccesses to our fifo. Weak refs are used. When all the weakrefs for a fifo expire, the fifo is deleted. AUTOMAGICAL power of weakrefs"""
        
        # a closure to remove the fifo if the list is empty
        def remove_ref( weak ):
            self._fifos[fifo].remove(weak)
            if not self._fifos[fifo]:
                # empty. delete us
                os.unlink(fifo)
                del self._fifos[fifo]
        
        for proc in procs:
            ref = weakref.ref( proc, remove_ref )
            self._fifos[fifo].append(ref)
            
    def make_url_for_fifo(self,filename):
        return "file://"+os.path.normpath(filename)

Fifos = FifoPool()