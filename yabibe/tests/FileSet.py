"""A context manager that creates a hierarchy of files.
You pass in a dictionary that describes the files and their hierarchy.
The manager builds that hierarchy with the data on entry,
and deletes the files on exit.

To assist in testing
"""

import tempfile
import os

class FileSet(object):
    def __init__(self, files):
        self.files = files

    def __enter__(self):
        """Makes a a bunch of files.
        pass in the files as a dictionary, names as keys, contents as values.
        Directories are automatically created. eg

        files = { 'test.dat':'line1\nline2\n',
                  'dir/file.txt':'test' }
        """
        self.path = tempfile.mktemp()
        os.makedirs(self.path)
        os.chmod(self.path, 0755)
        
        for filename in self.files:
            if os.path.sep in filename:
                # make the directories
                parts = filename.split(os.path.sep)
                # ['1','2','3','4'] => ['1','1/2','1/2/3']
                for dirs in [ os.path.sep.join(parts[:X+1]) for X in range(len(parts)-1) ]:
                    p = os.path.join( self.path,dirs )
                    os.makedirs(p)
                    os.chmod(p, 0755 )

                # now place the file
                fullpath = os.path.join( self.path, *parts )

                with open(fullpath, 'w') as fh:
                    fh.write( self.files[filename] )

            else:
                # just a file
                with open( os.path.join( self.path, filename ), 'w' ) as fh:
                    fh.write( self.files[filename] )

            # make it world readable
            os.chmod( os.path.join( self.path, filename ), 0755 )

        # filesystem is created. return us
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        assert not os.system("rm -rf '%s'"%(self.path))


# Save data to a file temporarily
class TempFile(object):
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        """write the data to a temporary file and remember its path"""
        self.filename = tempfile.mktemp()
        with open(self.filename, 'wb') as fh:
            fh.write(self.data)
        return self

    def __exit__(self):
        """delete the file"""
        os.unlink(self.filename)
        

        
