

import shutil
import subprocess
import tempfile

from fabric.api import env, run

import diabric.vagrant


def test_vagrant():
    '''
    Test bringing a vagrant box up, configuring fabric to ssh into it, 
    sshing into the box and running a command, and destroying the box.
    This test can take a few minutes to run, because of brining up the box.
    Also, if it fails to destroy the box, you might be left with a stray
    VirtualBox vm process, that you have kill.
    '''

    # create temp dir
    td = tempfile.mkdtemp()
    print td
    is_up = False
    try:
        # create Vagrantfile
        subprocess.check_call('vagrant init', cwd=td, shell=True)

        # create base box if it does not exist
        output = subprocess.check_output('vagrant box list', cwd=td, 
                                         shell=True)
        print output
        if 'base' not in [line.strip() for line in output.splitlines()]:
            cmd = ('vagrant box add base ' +
                   'http://files.vagrantup.com/lucid32.box')
            subprocess.check_call(cmd, cwd=td, shell=True)

        # point vagrant obj to the Vagrantfile.
        v = diabric.vagrant.Vagrant(td)
        # status
        assert v.status() == v.NOT_CREATED

        # create vagrant instance
        print 'going up'
        v.up()
        is_up = True
        # status
        assert v.status() == v.RUNNING

        # ssh
        print 'config ssh'
        # explicitly set host string b/c not running a fabric task
        env.host_string = v.get_host_string()
        env.key_filename = v.get_keyfile()
        output = run('echo $USER')
        assert output.strip() == 'vagrant'

        # destroy vagrant instance
        print 'destroying'
        v.destroy()
        is_up = False
        # status
        assert v.status() == v.NOT_CREATED
    finally:
        if is_up:
            # try to clean up an up box.
            v.destroy()
        shutil.rmtree(td)


