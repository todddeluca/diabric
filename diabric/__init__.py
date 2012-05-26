
'''
FABRIC UTILITY FUNCTIONS
'''


import collections
import os
import shutil
import subprocess

import fabric.api
import fabric.contrib.files
import fabric.operations
from fabric.api import env, task, sudo, run, cd, local, lcd, execute, get, put
from fabric.contrib.files import exists, upload_template
from fabric.contrib.project import rsync_project


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





##########################
# PROJ DIRECTORY STRUCTURE

# dir/
#   bin/ # executables
#   app/ # app
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
    return os.path.join(dir, 'app')


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




    

############
# DEPRECATED

# I now recommend running sshd on localhost to maintain the Fabric paradigm.

# This is bad advice:
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
    
    


