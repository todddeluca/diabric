
'''
FABRIC UTILITY FUNCTIONS
'''

import os
import shutil
import subprocess


import fabric.api
from fabric.api import env
import fabric.contrib.files
import fabric.operations


###############
# EC2 FUNCTIONS

def print_instances(instances, prefix=''):
    for instance in instances:
        print_instance(instance, prefix=prefix)


def print_instance(instance, prefix=''):
    print '{}Instance id={}, state={}, tags={}, public_dns_name={}'.format(
        prefix, instance.id, instance.state, instance.tags,
        instance.public_dns_name)


def terminate_instances(conn, instances):
    if not instances:
        return
    killed_instances = conn.terminate_instances([i.id for i in instances])
    if len(killed_instances) != len(instances):
        raise Exception('Not all instances terminated.', instances, 
                        killed_instances)
    print 'Terminated instances:'
    print_instances(killed_instances, '\t')


def get_named_instance(conn, name):
    '''
    Return a single non-terminated, non-shutting-down
    boto.ec2.instance.Instance that has a tag 'Name' that
    matches ``name``.

    conn: a boto.ec2.connection.EC2Connection
    name: string. The unique value of the 'Name' tag of a (running) instance
    return: the instance of the current webserver, of None if there is none.
    raise: Exception if there is more than one non-terminated instance.
    '''
    rs = conn.get_all_instances(filters={'tag:Name': name})
    instances = [i for r in rs for i in r.instances if i.state not in ['terminated', 'shutting-down']]
    if len(instances) > 1:
        raise Exception('More than one instance', instances)
    if not instances:
        return None
    return instances[0]




######################################
# DEPLOYMENT ENVIRONMENT CONFIGURATION

# Avoid storing configuration in env.
# Leave env for Fabric-specific configuration.
# Example gotcha: If you want to configure the port a server will listen on
# and so store it in env.port, you might break fabric's sshing.


class AttrDict(dict):
    '''
    A dictionary whose keys can also be accessed as attributes.
    i.e. as obj['key'] or obj.key
    '''
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


# Example of using AttrDict for configuration

# Create a collection of configs for each environment
# config = collections.defaultdict(AttrDict)

# Set configuration values for each environment
# config['dev'].system_python = '/usr/bin/python2.7'
# config['dev'].deploy_dir = '/www/example.com'
# config['dev'].user = 'dev-user'

# config['prod'].system_python = '/usr/bin/python2.7'
# config['prod'].deploy_dir = '/www/dev.example.com'
# config['prod'].user = 'prod-user'

# Set derived config values
# for c in config.values():
#     c.venv = venv_dir(c.deploy_dir)
#     c.log = log_dir(c.deploy_dir)
#     c.conf = conf_dir(c.deploy_dir)
#     c.bin = bin_dir(c.deploy_dir)
#     c.app = app_dir(c.deploy_dir)

# Create a convenience function to retrieve the configuration dict
# for the current environment. Use conf().key instead of env.key.
# def conf():
#     '''
#     Choose a configuration depending on the current role.
#     '''
#     return config[env.roles[0]]



##########################
# PROJ DIRECTORY STRUCTURE

# dir/
#   bin/ # executables
#   app/ # webapp
#   log/ # log files
#   conf/ # configuration
#   venv/ # virtual environment

# YMMV with this structure. Maybe you want your log files under /var/log/APP
# or you have a different name for your app dir.
# The point of dir_config is to create a clean API for getting the
# locations without hardcoding the structure in dependent code,
# so it can vary without breaking the dependent code.

def bin_dir(dir):
    return os.path.join(dir, 'bin')


def app_dir(dir):
    return os.path.join(dir, 'webapp')


def log_dir(dir):
    return os.path.join(dir, 'log')


def conf_dir(dir):
    return os.path.join(dir, 'conf')


def venv_dir(dir):
    '''
    dir: parent directory above the virtual environment dir
    returns: the path to the virtual environment
    '''
    return os.path.join(dir, 'venv')

def dir_config(dir, config):
    config.venv = venv_dir(dir)
    config.log = log_dir(dir)
    config.conf = conf_dir(dir)
    config.bin = bin_dir(dir)
    config.app = app_dir(dir)


######################
# VIRTUAL ENVIRONMENTS

# Use virtual environments and requirements.txt files.

def venv_python(venv):
    return os.path.join(venv, 'bin', 'python')


def venv_pip(venv):
    return os.path.join(venv, 'bin', 'pip')


def venv_clean(venv):
    if exists(venv):
        print 'cleaning', venv
        run('rm -rf {}'.format(venv))


def venv_init(venv, python='python', requirements=None, virtualenv_script=None):
    '''
    venv: virtual environment directory to create.
    python: path or name of python executable to use to create the venv.
    Defaults to 'python'.
    requirements: optional path of requirements.txt file (locally) to be copied
    to the virtual environment and used to install packages.
    virtualenv_script: Optional local path to virtualenv.py.  If given, it will
    be copied to venv and run by python to create venv.  If not given,
    virtualenv.py will be downloaded from the internet, which could be less
    reliable, slower, and does not guarantee a fixed version.
    Create venv on host using python and install requirements.
    '''
    script_path = os.path.join(venv, 'virtualenv.py')
    script_url = 'https://raw.github.com/pypa/virtualenv/master/virtualenv.py'
    requirements_path = os.path.join(venv, 'requirements.txt')

    # create the venv dir.  needed to put virtualenv.py and requirements.txt.
    if not exists(venv):
        run('mkdir -p {}'.format(venv))

    # put virtualenv.py in venv or download it.
    if virtualenv_script:
        put(virtualenv_script, script_path)
    else:
        run('curl -o {} {}'.format(script_path, script_url))

    # create the venv
    run('{} {} --distribute {}'.format(
        python, script_path, venv))

    # install requirements
    if requirements:
        put(requirements, requirements_path)
        run('{} install -r {}'.format(venv_pip(venv), requirements_path))


def venv_freeze(venv, requirements):
    '''
    venv: virtual environment directory to freeze.
    requirements: local path in which to save output of pip freeze.
    '''
    requirements_path = os.path.join(venv, 'requirements.txt')
    run('{} freeze > {}'.format(venv_pip(venv), requirements_path))
    get(requirements_path, requirements)


#############
# SUPERVISORD

def config_supervisord_program(src, dest, context=None, use_sudo=False,
                               mode=None):
    '''
    Upload supervisor config for a program and reload/restart.
    '''
    upload_template(
        os.path.join(conf_dir(HERE), 'heyluca_supervisord.conf'),
        '/etc/supervisor.d/heyluca.conf',
        context={'name': 'heyluca',
                 'venv': conf().venv,
                 'app': conf().app,
                 'entry': 'heyluca:app',
                 'conf': conf().conf,
                 'log': conf().log,
                 'user': conf().user,
                },
        use_sudo=True,
        mode=0770)




#######################
# FILES AND DIRECTORIES


def file_format(infile, outfile, args=None, keywords=None):
    '''
    Consider using upload_template
    infile: a local file path
    outfile: a local file path.
    Read the contents of infile as a string, ''.format() the string using args
    and keywords, and write the formatted string to outfile.  This is useful if
    infile is a "template" and args and keywords contain the concrete values
    for the template.
    '''
    if args is None:
        args = []
    if keywords is None:
        keywords is {}
    with open(infile) as fh:
        text = fh.read()
    new_text = text.format(*args, **keywords)
    with open(outfile, 'w') as fh2:
        fh2.write(new_text)

def rsync(options, src, dest, user=None, host=None, cwd=None):
    '''
    Consider using fabric.contrib.project.rsync_project.
    options: list of rsync options, e.g. ['--delete', '-avz']
    src: source directory (or files).  Note: rsync behavior varies depending on whether or not src dir ends in '/'.
    dest: destination directory.
    cwd: change (using subprocess) to cwd before running rsync.
    This is a helper function for running rsync locally, via subprocess.  Note: shell=False.
    '''
    # if remote user and host specified, copy there instead of locally.
    if user and host:
        destStr = '{}@{}:{}'.format(user, host, dest)
    else:
        destStr = dest

    args = ['rsync'] + options + [src, destStr]
    print args
    subprocess.check_call(args, cwd=cwd)
    

############
# DEPRECATED

# I now recommend running sshd on localhost to maintain the Fabric paradigm.

# http://stackoverflow.com/questions/6725244/running-fabric-script-locally
def setremote():
    '''
    set env.* to the remote versions for run, cd, rsync, and exists
    '''
    env.run = fabric.api.run
    env.cd = fabric.api.cd
    env.rsync = rsync
    env.exists = fabric.contrib.files.exists
    return env

def setlocal():
    '''
    set env.* to the localhost versions for run, cd, rsync, and exists
    '''
    env.run = fabric.api.local
    env.cd = fabric.api.lcd
    env.rsync = lrsync
    env.exists = os.path.exists
    return env


def lrsync(options, src, dest, cwd=None, **kwds):
    '''
    options: list of rsync options, e.g. ['--delete', '-avz']
    src: source directory (or files).  Note: rsync behavior varies depending on whether or not src dir ends in '/'.
    dest: destination directory.
    cwd: change (using subprocess) to cwd before running rsync.
    This is a helper function for using rsync to sync files to localhost.
    It uses subprocess.  Note: shell=False.
    Use rsync() to sync files to a remote host.
    '''
    args = ['rsync'] + options + [src, dest]
    print args
    subprocess.check_call(args, cwd=cwd)
    
    


