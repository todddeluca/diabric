

import shutil
import subprocess
import tempfile

from fabric.api import env, run

import diabric


def test_vagrant():

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
        # print output
        if 'base' not in [line.strip() for line in output.splitlines()]:
            cmd = ('vagrant box add base ' +
                   'http://files.vagrantup.com/lucid32.box')
            subprocess.check_call(cmd, cwd=td, shell=True)

        # point vagrant obj to the Vagrantfile.
        v = diabric.Vagrant(td)
        # status
        assert v.status() == v.NOT_CREATED

        # create vagrant instance
        # print 'going up'
        v.up()
        is_up = True
        # status
        assert v.status() == v.RUNNING

        # ssh
        # print 'config ssh'
        v.conf_ssh()
        env.host_string = env.hosts[-1]
        output = run('echo $USER')
        assert output.strip() == 'vagrant'

        # destroy vagrant instance
        # print 'destroying'
        v.destroy()
        is_up = False
        # status
        assert v.status() == v.NOT_CREATED
    finally:
        if is_up:
            # try to
            v.destroy()
        shutil.rmtree(td)


