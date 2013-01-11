
'''
FABRIC UTILITY FUNCTIONS
'''


import collections
import os
import shutil
import subprocess

import boto
import fabric.api
import fabric.contrib.files
import fabric.operations
from fabric.api import (env, task, sudo, run, cd, local, lcd, execute, get,
                        put, settings)
from fabric.contrib.files import exists, upload_template
from fabric.contrib.project import rsync_project


def add_keyfile(keyfile):
    '''
    Add a keyfile to fabric.api.env.key_filename.  This helper function handles
    the cases where env.key_filename is None, a string (path to keyfile) or a
    list of strings.

    keyfile: a path to a key file used by fabric for ssh.
    '''
    # env.key_filename can be None, a string or a list of strings.
    if not env.key_filename:
        env.key_filename = keyfile
    elif (isinstance(env.key_filename, basestring) and
            env.key_filename != keyfile):
        # turn string into list
        env.key_filename = [env.key_filename, keyfile]
    elif keyfile not in env.key_filename:
        # append the new keyfile
        env.key_filename.append(keyfile)


def fix_group_perms(path, group=None, remote=True):
    '''
    Normalize the permissions of all files and directories within (and
    including) 'path'.  Specifically it:

    - adds group write permissions to every file and dir that has user write permissions
    - sets the setgid bit on every dir
    - changes the group owner of every file and dir to `group` if `group` is not None

    This is useful in a multi-user environment to avoid situations where one
    user can not change or remove files because another user owns them and the
    permissions are wrong, even though both users belong to the same group
    and are working on a shared project.

    Warning: adding group write permissions to ssh keys or a .ssh dir can cause
    ssh to complain and fail, since these keys are meant to be user specific.

    path: A directory.  The permissions of this directory and all dirs and 
    files within it will be normalized.
    group: the name or gid which should own each file and dir in path
    (including path.)
    remote: if True, path is assumed to be on a remote host.  Otherwise, path
    is assumed to be on localhost.
    '''
    doit = run if remote else local

    if group:
        # all dirs and files should be owned by group 'genehawk'
        doit(r'find {path} -type d -not -group {group} -ls -exec chgrp {group} {{}} \;'.format(path=path, group=group))
    # all dirs should have setgid perms
    doit(r'find {path} -type d -not -perm -g+s -ls -exec chmod g+s {{}} \;'.format(path=path))
    # all dirs and files should have group write perms if the user has write perms
    doit(r'find {path} -perm -u+w -not -perm -g+w -ls -exec chmod g+w {{}} \;'.format(path=path))



#########
# UPSTART
# event-based init daemon
# http://upstart.ubuntu.com/


class Upstart(object):


    def __init__(self, conf_dir='/etc/init'):
        '''
        conf_dir: the location where modular upstart program configuration
        files go.
        '''
        self.conf_dir = conf_dir

    def conf_program(self, conf_file, dest_name=None, mode=None):
        '''
        conf_file: local upstart configuration file for the program.  If the
        program is named 'program', the basename of conf should be
        'program.conf'.
        dest_name: the base filename of the destination file.  Defaults to the
        basename of include_file.  E.g. myapp.conf.
        '''
        if not dest_name:
            dest_name = os.path.basename(conf_file)

        dest = os.path.join(self.conf_dir, dest_name)
        put(conf_file, dest, use_sudo=True, mode=mode)

    def reload_program(self, program):
        '''
        program: the name of the program to use in initctl commands.

        Reload configuration, stop program if it is running, and start program
        using the new configuration.
        '''
        # reload upstart config
        sudo('initctl reload-configuration')

        with settings(warn_only=True):
            # fyi: it is an error to stop an already stopped program
            sudo('initctl stop {}'.format(program))

        # fyi: it is an error to start a running program
        sudo('initctl start {}'.format(program))


#############
# SUPERVISORD
# http://supervisord.org/index.html


class Supervisord(object):
    '''
    Try to put a pretty interface on uploading configuration files for
    Supervisor, and reloading and restarting supervisor and supervised
    programs.

    It is recommended that supervisord be started under
    initd/upstart/monit/etc.  This class does not handle configuring and
    managing programs under those daemons.
    '''

    def __init__(self, conf_file='/etc/supervisord.conf', include_dir='/etc/supervisor.d'):
        '''
        conf_file: the remote path to the main configuration file.
        include_dir: the remote path the the directory containing modular
        configuration files for supervisor programs, etc.
        '''
        self.conf_file = conf_file
        self.include_dir = include_dir

    def install(self):
        '''
        Install the supervisor python package.  Currently this tries to install 
        distribute and pip into python2.7 and then install supervisor with pip.
        '''
        # Install distribute, a pip dependency
        sudo('curl http://python-distribute.org/distribute_setup.py | python2.7')
        # install pip in system python
        sudo('curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python2.7')
        # install supervisord to supervise nginx, gunicorn.
        sudo('pip-2.7 install supervisor')

        # make a dir for modular supervisor config files
        if self.include_dir:
            sudo('mkdir -p {}'.format(self.include_dir))

    def conf(self, conf_file, mode=None):
        '''
        conf_file: local configuration file to be uploaded.
        Upload supervisord's main configuration file.
        For sanity's sake make sure the [include] section includes
        self.include_dir if you planning on using conf_include.
        '''
        # FYI: how to generate a conf file.
        # sudo('echo_supervisord_conf > supervisord.conf')
        put(conf_file, self.conf_file, use_sudo=True, mode=mode)

    def conf_include(self, include_file, dest_name=None, mode=None):
        '''
        include_file: the local file path of a modular configuration. E.g. the
        configuration of a specific program, like /path/to/myapp.conf.
        dest_name: the base filename of the destination file.  Defaults to the
        basename of include_file.  E.g. myapp.conf.

        Upload configuration to the include_dir.  Raise an exception if
        self.include_dir is falsy.
        '''
        if not self.include_dir:
            raise Exception('No self.include_dir.  Can not upload program configuration without a defining a configuration dir.')

        if not dest_name:
            dest_name = os.path.basename(include_file)

        dest = os.path.join(self.include_dir, dest_name)
        put(include_file, dest, use_sudo=True, mode=mode)

    def reload(self):
        '''
        Stop the main supervisor daemon (and I assume all its supervised
        programs), reread the configuration, and restart the daemon and all
        programs (according to the configuration)

        Use this when changing the configuration of the main supervisor daemon.
        It is overkill if you are just changing the configuration of a program.
        '''
        sudo('supervisorctl reload')

    def reload_program(self, program):
        '''
        program: the name of a supervisor 'program' section.

        Reread supervisor's configuration and restart the program using the
        new configuration (if any).  Use this function to restart a program if
        its configuration has changed.
        '''

        # supervisor docs are somewhat lacking for supervisorctl.
        # this is helpful
        # http://comments.gmane.org/gmane.comp.sysutils.supervisor.general/858

        # reread configuration files
        sudo('supervisorctl reread') 
        # stop the program if it is running.
        sudo('supervisorctl stop {}'.format(program)) 
        # remove the old program configuration
        sudo('supervisorctl remove {}'.format(program))
        # add the new program configuration
        sudo('supervisorctl add {}'.format(program))
        # start the program
        sudo('supervisorctl start {}'.format(program))


#######
# NGINX


class Nginx(object):
    '''
    Try to put a pretty interface on uploading configuration files for
    Nginx, and reloading it.
    '''

    def __init__(self, include_dir='/etc/nginx/conf.d'):
        '''
        include_dir: the remote path the the directory containing modular
        configuration files for nginx.  By default these files live in
        /etc/nginx/conf.d and are named *.conf.
        '''
        self.include_dir = include_dir

    def install(self):
        sudo('yum -y install nginx')

    def start(self):
        sudo('service nginx start')

    def conf_include(self, include_file, dest_name=None, mode=None):
        '''
        include_file: the local file path of a modular configuration. E.g. the
        configuration of a specific program, like /path/to/myapp.conf.
        dest_name: the base filename of the destination file.  Defaults to the
        basename of include_file.  E.g. myapp.conf.

        Upload configuration to the include_dir.  Raise an exception if
        self.include_dir is falsy.
        '''
        if not self.include_dir:
            raise Exception('No self.include_dir.  Can not upload configuration without a defining a configuration dir.')

        if not dest_name:
            dest_name = os.path.basename(include_file)

        dest = os.path.join(self.include_dir, dest_name)
        put(include_file, dest, use_sudo=True, mode=mode)

    def reload(self):
        '''
        Tell nginx to reload its configuration and restart itself gracefully
        with the new configuration.  This should be done to make configuration
        changes take effect.
        '''
        sudo('service nginx reload')


##############
# UNUSED TASKS

@task
def install_mysql():
    # install mysql
    sudo('yum -y install mysql')
    sudo('yum -y install mysql-server')
    sudo('yum -y install mysql-devel')


@task
def install_apache():
    # install apache
    sudo('yum -y install httpd')
    sudo('yum -y install httpd-devel')


@task
def install_monit():
    # install monit to monitor apache
    sudo('yum -y install monit')
    sudo('initctl start monit')


@task
def install_others():
    # install monit to monitor apache
    # sudo('yum -y install monit')

    # install cpu monitoring tool
    # http://www.cyberciti.biz/tips/how-do-i-find-out-linux-cpu-utilization.html
    sudo('yum -y install sysstat')



