
'''
Fabric-based functions working with python virtual environments:

- creating a new virtual environment
- remving an existing virtual environment
- installing requirements in a virtual environment
- "freezing" requirements from a virtual environment
- getting paths of executables, etc., within a virtual environment.
'''



import os

from fabric.api import run, put, get
from fabric.contrib.files import exists
from fabric.tasks import Task


def bin(venv):
    '''
    return: path to the venv bin dir.
    '''
    return os.path.join(venv, 'bin')


def python(venv):
    '''
    return: path to the venv python executable.
    '''
    return os.path.join(venv, 'bin', 'python')


def pip(venv):
    '''
    return: path to the venv pip executable.
    '''
    return os.path.join(venv, 'bin', 'pip')


def remove(venv):
    '''
    Remove the virtual environment completely
    '''
    if exists(venv):
        print 'cleaning', venv
        run('rm -rf {}'.format(venv))


def create(venv, python='python', virtualenv_script=None):
    '''
    venv: virtual environment directory to create.  venv MUST NOT already exist.
    python: path or name of python executable to use to create the venv.
    Defaults to 'python'.
    virtualenv_script: Optional local path to virtualenv.py.  If given, it will
    be copied to venv and run by python to create venv.  If not given,
    virtualenv.py will be downloaded from the internet, which could be less
    reliable, slower, and does not guarantee a fixed version.  

    Create a virtual environment located at venv on the remote host.  Raise an exception if venv already exists.
    '''
    script_path = os.path.join(venv, 'virtualenv.py')
    script_url = 'https://raw.github.com/pypa/virtualenv/master/virtualenv.py'

    # require that the venv does not yet exist.
    if exists(venv):
        raise Exception('Path already exists. Abort creation. venv={}'.format(venv))

    # create the venv dir for virtualenv.py
    run('mkdir -p {}'.format(venv))

    # put virtualenv.py in venv or download it.
    if virtualenv_script:
        put(virtualenv_script, script_path)
    else:
        run('curl -o {} {}'.format(script_path, script_url))

    # create the venv
    run('{} {} --distribute {}'.format(python, script_path, venv))


def install(venv, requirements):
    '''
    venv: virtual environment directory to create.
    requirements: local path of requirements.txt file to be copied to venv dir
    to the virtual environment and used to install packages.
    Use the venv pip to install the requirements file.
    '''
    remote_path = os.path.join(venv, 'requirements.txt')
    put(requirements, remote_path)
    run('{} install -r {}'.format(pip(venv), remote_path))



def freeze(venv, requirements):
    '''
    venv: virtual environment directory to freeze.
    requirements: local path in which to save output of pip freeze.
    '''
    remote_path = os.path.join(venv, 'requirements.txt')
    run('{} freeze > {}'.format(pip(venv), remote_path))
    get(remote_path, requirements)



class CreateVenv(Task):
    def __init__(self, venv, python):
        self.venv = venv
        self.python = python

    def run(self, *args, **kwargs):
        create(self.venv, python=self.python)


class InstallVenv(Task):
    def __init__(self, venv, requirements):
        self.venv = venv
        self.requirements = requirements

    def run(self, *args, **kwargs):
        install(self.venv, self.requirements)


class RemoveVenv(Task):
    def __init__(self, venv):
        self.venv = venv

    def run(self, *args, **kwargs):
        remove(self.venv)


class FreezeVenv(Task):
    def __init__(self, venv, requirements):
        self.venv = venv
        self.requirements = requirements

    def run(self, *args, **kwargs):
        freeze(self.venv, self.requirements)



