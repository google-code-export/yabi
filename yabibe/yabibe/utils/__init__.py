import os

def rm_rf(root,contents_only=False):
    """If contents_only is true, containing folder is not removed"""
    for path, dirs, files in os.walk(root, False):
        for fn in files:
            os.unlink(os.path.join(path, fn))
        for dn in dirs:
            os.rmdir(os.path.join(path, dn))
    if not contents_only:
        os.rmdir(root)

