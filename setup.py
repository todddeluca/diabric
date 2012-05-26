
from setuptools import setup

setup(
    name = 'diabric',
    version = '0.1',
    license = 'MIT',
    description = 'Diabolically atomic Python Fabric fabfile tasks and utilities.',
    long_description = open('README.md').read(),
    keywords = 'fabric fabfile boto ec2 virtualenv python wsgi webapp deployment',
    url = 'https://github.com/todddeluca/diabric',
    author = 'Todd Francis DeLuca',
    author_email = 'todddeluca@yahoo.com',
    classifiers = ['License :: OSI Approved :: MIT License',
                   'Development Status :: 2 - Pre-Alpha',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                  ],
    packages = ['diabric'],
    install_requires = ['setuptools', 'Fabric>=1.4','boto>=2.3'],
    include_package_data = True,
    package_data = {'' : ['README.md', 'LICENSE.txt']},
)

