"""A context manager that stores data in a temporary file"""
import tempfile
import os

class TempFile(object):
    def __init__(self, data, path=None):
        self.path = path
        self.data = data

    def __enter__(self):
        """Write the data into a temporary location"""
        self.fd, self.filename = tempfile.mkstemp(dir=self.path)

        self.fh = os.fdopen(self.fd,'w')
        self.fh.write(self.data)
        self.fh.close()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up this file"""
        os.unlink(self.filename)


        
