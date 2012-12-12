import tempfile, os
from yabibe.utils import rm_rf

SSH_KEY_FILE_EXPIRY_TIME = 60               # 60 seconds of validity


class KeyStore(object):
    def __init__(self, path=None, dir=None, expiry=60):
        print "KeyStore::__init__(",path,",",dir,",",expiry,")"
        if path:
            assert dir==None, "Cannot set 'dir' AND 'path'. 'path' overides 'dir'."
            self.directory = path
        else:
            # make a temporary storage directory
            self.directory = tempfile.mkdtemp(suffix=".ssh",prefix="",dir=dir)

        self.keys = {}
        self.files = []
        
    def __del__(self):
        self.clear_keystore()
        
    def clear_keystore(self):
        if self.directory:
            assert os.path.exists(self.directory), "Can't clear keystore that doesn't exist on disk"
            rm_rf(self.directory)
        
    def save_identity(self, identity, tag=None):
        
        # TODO: avoid calling this method when there is no key
        from string import whitespace
        def is_whitespace(st):
            return False not in [X in whitespace for X in st]
            
        if is_whitespace(identity):
            return None
        
        
        filename = tempfile.mktemp(dir=self.directory)
        fh = open( filename, "w" )
        fh.write( identity )
        fh.close()
        
        os.chmod( filename, 0600 )
        
        if tag:
            self.keys[tag] = filename
            
        self.files.append(filename)
        
        # TODO: fix expiry period for cache
        #def del_key_file(fn):
            #print "DELETING",fn
            #os.unlink(fn)
        
        #reactor.callLater(SSH_KEY_FILE_EXPIRY_TIME,del_key_file,filename) 
        
        return filename
        
    def delete_identity(self, tag):
        print "delte_identity",tag
        fname = self.keys[tag]
        os.unlink(fname)
        del self.keys[tag]
        self.files.remove(fname)
        
        
    
       
