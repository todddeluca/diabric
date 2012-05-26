
# Introduction

Diabric is a python package containing utilities for use in Fabric fabfiles.
These tasks, functions, and classes are useful for:

- working with Amazon EC2
- configuring machines
- installing, configuring, and starting services, servers, and daemons, like
  nginx and supervisord.
- deploying python wsgi web applications.
- uploading and formatting files
- creating python virtualenv virtual environments
- installing packages into virtualenvs
- configuring fabfiles

  
This package is still very much _alpha_ and exists to reduce code duplication
across a number of fabfiles I have for different projects.

# Requirements

- Written with Python 2.7 
(http://python.org/download/releases/2.7.3/) in mind.  
- Packaged with distutils2 (http://packages.python.org/Distutils2/)
- Fabric (http://docs.fabfile.org/) for creating fabfile tasks, working with
  remote hosts, ...
- Boto (https://github.com/boto/boto) for interacting with EC2.

# Installation

## Install from pypi.python.org

Download and install diabric.

    pip install diabric

## Install from github.com

Install distutils2 if you do not yet have it installed.

    pip install distutils2

Download and install diabric.

    cd ~
    git clone git@github.com:todddeluca/diabric.git
    cd diabric
    pysetup install

