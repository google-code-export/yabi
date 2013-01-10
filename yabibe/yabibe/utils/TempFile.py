"""A context manager that stores data in a temporary file"""
import tempfile
import os

class TempFile(object):
    def __init__(self, data, path=None):
        self.path = path
        self.data = data

    def __enter__(self):
        """Write the data into a temporary location"""
        self.fh, self.filename = tempfile.mkstemp(dir=self.path)
        self.fh.write(self.data)
        self.fh.close()

    def __exit__(self):
        """Clean up this file"""
        os.unlink(self.filename)


        
