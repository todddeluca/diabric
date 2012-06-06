

'''
Python utilities for working with a Vagrant box.  Saves some of the boilerplate
of calling vagrant command lines and parsing the results.

Quick and dirty test:

python -c 'import diabric.vagrant, fabric.api; 
v = diabric.vagrant.Vagrant()
v.up();
print v.status()
print v.get_host_string()
print v.get_user()
print v.get_port()
print v.get_keyfile()
print v.get_hostname()
# v.destroy();
print v.get_conf()
'

For unit tests, see tests/test_vagrant.py
'''


import collections
import os
import subprocess


####################
# VAGRANT FUNCTIIONS


class Vagrant(object):
    '''
    Object to up (launch) and destroy (terminate) vagrant virtual machines,
    to check the status of the machine and to report on the configuration
    of the machine.  machines up (launching) and desand terminating vagrant virtual machines,
    and for configuring fabric tasks and ssh to use a vagrant vm as a host.
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
        subprocess.check_call('vagrant up', shell=True, cwd=self.root)

    def destroy(self):
        '''
        Terminate the running Vagrant box.
        '''
        subprocess.check_call('vagrant destroy -f', shell=True, cwd=self.root)

    def status(self):
        '''
        Returns the status of the Vagrant box:
            'not created' if the box is destroyed
            'running' if the box is up
            'poweroff' if the box is halted
            None if no status is found
        There might be other statuses, but the Vagrant docs were unclear.
        '''
        output = subprocess.check_output('vagrant status', shell=True,
                                         cwd=self.root)
        # example output
        '''
        Current VM states:

        default                  poweroff

        The VM is powered off. To restart the VM, simply run `vagrant up`
        '''
        status = None
        for line in output.splitlines():
            if line.startswith('default'):
                status = line.strip().split(None, 1)[1]

        return status

    def get_conf(self, ssh_config=None):
        '''
        Return a dict containing these keys (and example values): 'User' (e.g.
        'vagrant'), 'HostName' (e.g. 'localhost'), 'Port' (e.g. '2222'),
        'IdentityFile' (the keyfile, e.g. '/home/todd/.ssh/id_dsa'), and
        'HostString' (e.g. 'vagrant@localhost:2222')
        '''
        conf = self._parse_config(ssh_config)
        conf['HostString'] = self.get_host_string(conf)
        return conf

    def ssh_config(self):
        '''
        Return the output of 'vagrant ssh-config' which appears to be a valid
        Host phrase suitable for use in an ssh config file.
        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.

        Example output:
            Host default
                HostName 127.0.0.1
                User vagrant
                Port 2222
                UserKnownHostsFile /dev/null
                StrictHostKeyChecking no
                PasswordAuthentication no
                IdentityFile /Users/todd/.vagrant.d/insecure_private_key
                IdentitiesOnly yes
        '''
        # capture ssh configuration from vagrant
        return subprocess.check_output('vagrant ssh-config', shell=True,
                                       cwd=self.root)

    def get_user(self, conf=None):
        '''
        Return the ssh user of the vagrant box, e.g. 'vagrant'
        or None if there is no user in the ssh_config.

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        '''
        conf = conf if conf is not None else self.get_conf()
        return conf.get('User')

    def get_hostname(self, conf=None):
        '''
        Return the vagrant box hostname, e.g. '127.0.0.1'
        or None if there is no hostname in the ssh_config.

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        '''
        conf = conf if conf is not None else self.get_conf()
        return conf.get('HostName')

    def get_port(self, conf=None):
        '''
        Return the vagrant box ssh port, e.g. '2222'
        or None if there is no port in the ssh_config.

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        '''
        conf = conf if conf is not None else self.get_conf()
        return conf.get('Port')

    def get_conf(self, ssh_config=None):
        '''
        Return a dict containing the keys defined in ssh_config, which
        should include these keys (listed with example values): 'User' (e.g.
        'vagrant'), 'HostName' (e.g. 'localhost'), 'Port' (e.g. '2222'),
        'IdentityFile' (aliased to 'KeyFile', e.g. '/home/todd/.ssh/id_dsa'),
        and 'HostString' (e.g. 'vagrant@localhost:2222')

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        '''
        conf = self._parse_config(ssh_config)
        conf['HostString'] = self.get_host_string(conf)
        # alias IdentityFile to KeyFile
        if 'IdentityFile' in conf:
            conf['KeyFile'] = conf['IdentityFile']
        return conf

    def get_host_string(self, conf=None):
        '''
        Return a Fabric compatible host_string, suitable for use in env.hosts.
        This combines the user, host, and port.  E.g. 'vagrant@127.0.0.1:2222'

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        Raises an Exception if 'HostName' is not defined in ssh_config.  After
        all, what is the point of a host_string without a host?
        '''
        conf = conf if conf is not None else self.get_conf()
        # e.g. vagrant@127.0.0.1:2222
        user = self.get_user(conf)
        hostname = self.get_hostname(conf)
        port = self.get_port(conf)
        user_prefix = user + '@' if user else ''
        port_suffix = ':' + port if port else ''
        host_string = user_prefix + conf['HostName'] + port_suffix
        return host_string

    def get_keyfile(self, conf=None):
        '''
        Return the path to the private key used to log in to the vagrant box
        or None if there is no keyfile (IdentityFile) in the ssh_config.
        E.g. '/Users/todd/.vagrant.d/insecure_private_key'

        Raises an Exception if the Vagrant box has not yet been created or
        has been destroyed.
        '''
        conf = conf if conf is not None else self.get_conf()
        return conf.get('IdentityFile')

    def _parse_config(self, ssh_config=None):
        '''
        This ghetto parser does not parse the full grammar of an
        ssh config file.  It makes assumptions that are (hopefully) correct
        for the output of `vagrant ssh-config`.  Specifically it assumes
        that there is only one Host section.  It assumes that every line
        is of the form 'key  value', where key is a single token without any
        whitespace and value is the remaining part of the line.  All leading
        and trailing whitespace is removed from key and value.  For example,
        '   User vagrant\n'.  Lines with '#' as the first non-whitespace 
        character are considered comments and ignored.  Whitespace-only lines
        are ignored.

        See https://github.com/bitprophet/ssh/blob/master/ssh/config.py for a
        more compliant ssh config file parser.
        '''
        if ssh_config is None:
            ssh_config = self.ssh_config()

        # skip blank lines and comment lines
        conf = dict(line.strip().split(None, 1) for line in 
                    ssh_config.splitlines() if line.strip() and 
                    not line.strip().startswith('#'))

        return conf



