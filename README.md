
# Introduction

Diabric is a python package containing utilities (fabric tasks, functions, etc.) for using fabric to:

- work with Amazon EC2
- configure machines
- install, configure, and start services, servers, and daemons.
- deploy web applications.
- create virtual environments and install packages into them.

This package is still very much _alpha_ and exists to reduce code duplication
across a number of fabfiles I have for different projects.  Please copy and/or
use this code freely.

# Requirements

- Written with Python 2.7 
(http://python.org/download/releases/2.7.3/) in mind.  
- Packaged with distutils2 (http://packages.python.org/Distutils2/)
- Fabric (http://docs.fabfile.org/) for creating fabfile tasks, working on remote hosts, ...
- Boto (https://github.com/boto/boto) for interacting with EC2.

# Installation

## Install from source using distutils2.

Install distutils2 if you do not yet have it installed.

    pip install distutils2

Download and install diabric.

    cd ~
    git clone git@github.com:todddeluca/diabric.git
    cd diabric
    pysetup install

