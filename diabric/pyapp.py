

'''
Fabric functionality for configuring, deploying, and starting python 
applications.

This module provides an API to access directories where an application stores
configuration files, log files, a virtual environment, a binaries, and the
webapp code.

This module encodes a very arbitrary and specific way of organizing an
application and so might not be useful to a wide audience.

'''

import os


class App(object):
    '''
    PROJ DIRECTORY STRUCTURE

    root/
        bin/ # executables
        app/ # app code
        log/ # log files
        conf/ # configuration
        venv/ # virtual environment

    YMMV with this structure. Maybe you want your log files under /var/log/APP
    or you have a different name for your app dir.  The point is to create a
    API for getting the locations without hardcoding the structure in dependent
    code, so the structure can vary without breaking the dependent code.
    '''

    def __init__(self, root):
        '''
        root: the root directory of the application project
        '''
        self.root = root

    def bindir(self):
        return os.path.join(self.root, 'bin')

    def appdir(self):
        return os.path.join(self.root, 'app')

    def logdir(self):
        return os.path.join(self.root, 'log')

    def confdir(self):
        return os.path.join(self.root, 'conf')

    def venvdir(self):
        '''
        returns: the path to the virtual environment
        '''
        return os.path.join(self.root, 'venv')



