import setuptools
import os
from setuptools import setup, find_packages

def main():
    requires = all_requires('yabibe/requirements.txt')
    requires.remove('==TwistedWeb2-10.2.0')
    requires.append('TwistedWeb2==10.2.0')
    print requires

    setup(name='yabibe',
        version='0.1',
        description='Yabi Backend',
        long_description='Yabi back end service',
        author='Centre for Comparative Genomics',
        author_email='web@ccg.murdoch.edu.au',
        packages=['yabibe']+[
            'yabibe.%s'%x for x in "conf ex FifoPool fs TaskManager utils log".split()
        ]+'yabibe.ex.connector yabibe.fs.connector yabibe.utils.protocol yabibe.utils.protocol.globus yabibe.utils.protocol.s3 yabibe.utils.protocol.ssh'.split(),
        package_data={},
        zip_safe=False,
        install_requires=requires,
        scripts=['yabibe/scripts/yabibe'],
    )
    
#
# Functional helpers to turn requirements.txt into package names and version strings
# What is this? LISP?
#

flatten = lambda listoflists: [ inner for outer in listoflists for inner in outer ]             # flatten a list of lists

# take a list of .txt pip dependency filenames and flatten them into only the package dependency lines as a list.
# take out comments and -r's
build_requires = lambda *files: flatten(
    [
        [ 
            line.strip() for line in open(file).readlines() 
                if  line and 
                not line.startswith('#') and 
                not line.startswith('-r ')
        ]
        for file in files
    ]
)

# lines that are urls or not
urls = lambda lines: [ line for line in lines if line.startswith('http') ]
noturls = lambda lines: [ line for line in lines if not line.startswith('http') ]
filenames = lambda urls: [ url.rsplit('/',1)[-1] for url in urls ]              # munge into just package filenames

# truncate package name
basefilename = lambda filename: [ 
    item for item in 
    [ 
        filename[:-len(ext)] if filename.endswith(ext) else None 
        for ext in ['.tgz','.tar.gz'] 
    ] 
    if item is not None 
]

basefilenames = lambda filenames: flatten( [ basefilename(files) for files in filenames ] )
parts = lambda filename: filename.split('-')                                # parts of a filename
has_number = lambda string: True in [a in string for a in '0123456789']     # string has a number somewhere in it
split_point = lambda parts: [ has_number(part) for part in parts ].index(True)          # the index of the earliest part with a number in it
number_split = lambda parts: (parts[:split_point(parts)],parts[split_point(parts):])    # split a list of strings into two lists. the first part with a number becomes the list split point.
make_package_version = lambda nameparts, versionparts: ('-'.join(nameparts),'-'.join(versionparts))         # package name, version part
make_egg_versions = lambda filenames: [ make_package_version( *number_split(parts(name)) ) for name in filenames ]
egg_versions = lambda *files: [ "%s==%s"%parts for parts in make_egg_versions(basefilenames(filenames(urls(build_requires(*files))))) ]
pypy_eggs = lambda *files: noturls(build_requires(*files))
all_requires = lambda *files: egg_versions(*files)+pypy_eggs(*files)

if __name__ == "__main__":
    main()
