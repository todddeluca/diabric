
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
from fabric.api import (env, task, sudo, run, cd, local, lcd, execute, get,
                        put, settings)
from fabric.contrib.files import exists, upload_template
from fabric.contrib.project import rsync_project


####################
# VAGRANT FUNCTIIONS


class Vagrant(object):
    '''
    Object for launching and terminating vagrant virtual machines,
    and for configuring fabric to SSH into a VM.
    '''

    # statuses
    RUNNING = 'running' # vagrant up
    NOT_CREATED = 'not created' # vagrant destroy
    POWEROFF = 'poweroff' # vagrant halt

    def __init__(self, root='.'):
        '''
        root: a directory containing a Vagrantfile.  Defaults to '.'.
        '''
        self.root = root

    def up(self):
        '''
        Launch the Vagrant box.
        '''
        with lcd(self.root):
            local('vagrant up')

    def destroy(self):
        '''
        Terminate the running Vagrant box.
        '''
        with lcd(self.root):
            local('vagrant destroy -f')

    def status(self):
        '''
        Returns the status of the Vagrant box:
            'not created' if the box is destroyed
            'running' if the box is up
            'poweroff' if the box is halted
            None if no status is found
        There might be other statuses, but the Vagrant docs were unclear.
        '''
        with lcd(self.root):
            out = local('vagrant status', capture=True)

        # example out
        '''
        Current VM states:

        default                  poweroff

        The VM is powered off. To restart the VM, simply run `vagrant up`
        '''
        status = None
        for line in out.splitlines():
            if line.startswith('default'):
                status = line.strip().split(None, 1)[1]

        return status

    def conf_ssh(self, append=True):
        '''
        Configure Fabric env for sshing to the Vagrant box.  This changes
        fabric.api.env to use the right user, host, port, and identity file
        to ssh into the Vagrant vm.

        append: if True, the vagrant host and key_filename will be appended
        to env.hosts and env.key_filename.  If False, env.hosts and
        env.key_filename will only contain the vagrant values.
        '''


        # capture ssh configuration from vagrant
        with lcd(self.root):
            out = local('vagrant ssh-config', capture=True)
            # Example output.  This is a the contents of a SSH config file.
            '''
            Host default
                HostName 127.0.0.1
                User vagrant
                Port 2222
                UserKnownHostsFile /dev/null
                StrictHostKeyChecking no
                PasswordAuthentication no
                IdentityFile /Users/td23/.vagrant.d/insecure_private_key
                IdentitiesOnly yes
            '''

        print out
        # parse vagrant ssh config.
        conf = dict(line.strip().split(None, 1) for line in out.splitlines())
        print conf

        # translate ssh config into Fabric env variables.
        # if (conf.get('StrictHostKeyChecking') == 'no' and
        #     conf.get('UserKnownHostsFile') == '/dev/null'):
        #     env.disable_known_hosts = True

        # if conf.get('IdentitiesOnly') == 'yes':
        #     env.no_agent = True 
        #     env.no_keys = True

        # env.key_filename can be None, a string or a list of strings.
        key_filename = conf['IdentityFile']
        if not append or not env.key_filename:
            # replace
            env.key_filename = key_filename
        elif (isinstance(env.key_filename, basestring) and
              env.key_filename != key_filename):
            # turn string into list
            env.key_filename = [env.key_filename, key_filename]
        elif key_filename not in env.key_filename:
            # append the new key_filename
            env.key_filename.append(key_filename)

        # e.g. vagrant@127.0.0.1:2222
        host_string = (conf['User'] + '@' + conf['HostName'] + ':' +
                       conf['Port'])
        if not append or not env.hosts:
            env.hosts = [host_string]
        elif host_string not in env.hosts:
            env.hosts.append(host_string)

        # if conf.get('HostName'):
        #     if append:
        #         env.hosts.append(conf['HostName'])
        #     else:
        #         env.hosts = [conf['HostName']]

        # if conf.get('User'):
        #     env.user = conf['User']

        # if conf.get('Port'):
        #     env.port = conf['Port']

        # print env.disable_known_hosts
        # print env.key_filename
        # print env.no_agent
        # print env.no_keys



###############
# EC2 FUNCTIONS

def print_instances(instances, prefix=''):
    for instance in instances:
        print_instance(instance, prefix=prefix)


def print_instance(instance, prefix=''):
    print ('{}Instance id={}, state={}, tags={}, public_dns_name={}' +
           ' launch_time={}').format(
        prefix, instance.id, instance.state, instance.tags,
        instance.public_dns_name, instance.launch_time)


def terminate_instances(conn, instances):
    if not instances:
        return
    killed_instances = conn.terminate_instances([i.id for i in instances])
    if len(killed_instances) != len(instances):
        raise Exception('Not all instances terminated.', instances, 
                        killed_instances)
    print 'Terminated instances:'
    print_instances(killed_instances, '\t')


def get_tagged_instances(conn, key, value):
    '''
    conn: a boto.ec2.connection.EC2Connection
    key: a string representing the tag key.
    value: a string representing the tag value.
    Return a list of boto.ec2.instance.Instance objects where value of the
    tag named `tag` matches `value`.

    name: string. The unique value of the 'Name' tag of a (running) instance
    return: the instance of the current webserver, of None if there is none.
    raise: Exception if there is more than one non-terminated instance.
    '''
    rs = conn.get_all_instances(filters={'tag:{}'.format(key): value})
    return [i for r in rs for i in r.instances]


def on_instances(instances):
    '''
    Filter out instances that are 'terminated' or 'shutting-down'.
    Return a list of the remaining instances.
    '''
    bad_states = ['terminated', 'shutting-down']
    return [i for i in instances if i.state not in bad_states]


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


