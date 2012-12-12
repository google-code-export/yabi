import os

def rm_rf(root,contents_only=False):
    """If contents_only is true, containing folder is not removed"""
    # DONT REMOVE THE FOLLOWING IMPORT EVEN THOUGH IT LOOKS REDUNDANT
    # we need to reimport os here... which is wierd... but...
    # we call this rm_rf from __del__ object destroctors
    # that are called during garbage collection when python interpreter itself is shutting down
    # and os may have been already GCed.
    import os
    
    for path, dirs, files in os.walk(root, False):
        for fn in files:
            os.unlink(os.path.join(path, fn))
        for dn in dirs:
            os.rmdir(os.path.join(path, dn))
    if not contents_only:
        os.rmdir(root)
    
import decorators
