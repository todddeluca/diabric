
'''

With this module you can:

- Create configurations for different contexts.
- Access configurations depending on the context of a task.

Best practices for Fabric configuration:

- Avoid storing configuration in fabric.api.env.  Leave env for Fabric-specific
  configuration.  An example of what happens when you do not.  If you want to
  configure the port a server will listen on, you might store it in env.port,
  overwriting the port fabric uses for ssh.  Chaos and failure ensues.


# Context objects

A Context object is a callable that returns a key representing the current
context.  This key is used by a ContextConfig to get the configuration for the
current context.

An example of a useful Fabric context is host_context() which returns the
current fabric.api.env.host.

# ContextConfig

A ContextConfig object is a callable and a dictionary.  They are
configured with a context object.  When the ContextConfig object is used as a
callable, it calls its context to get a key and then returns the dictionary
value (i.e. the configuration) associated with that key.  When the
ContextConfig object is used as a dictionary it can store configuration values
for each context key.

An implementation of ContextConfig object is `ContextConfig`, which is a subclass of
collections.defaultdict that will return dict objects by default.

Another implementation is NamespaceContextConfig, another collections.defaultdict
subclss that returns Namespace objects by default.  Some people prefer the
terse syntax of attribute-style access more than dict-style access.

Another implementation is AttrDictContextConfig, another collections.defaultdict
subclss that returns AttrDict objects by default.  Some people prefer the
terser syntax of attribute-style access while maintaining most dict
functionality.
'''


import collections

from fabric.api import env


def host_context():
    '''
    Returns the current fabric env.host.  This is useful with
    KeyConfig(host_context) to get the configuration associated with the
    current host in a task.
    '''
    return env.host


def role_context():
    '''
    Return the first role in the current fabric env.roles list, or None if
    there are no roles.  This is useful with KeyConfig(role_context) to get the
    configuration for the current role in a task.
    '''
    if len(env.roles):
        return env.roles[0]
    else:
        return None


class ContextConfig(collections.defaultdict):
    '''
    ContextConfig is a defaultdict of dict objects used to store configuration.
    It is also a callable that returns the dict for the current context.

    Usage example:

        # Create a config collection for each role
        config = ContextConfig(role_context)

        # Set configuration values for each role.
        config['dev']['deploy_dir'] = '/www/example.com'
        config['dev']['user'] = 'dev-user'
        config['prod']['deploy_dir'] = '/www/dev.example.com'
        config['prod']['user'] = 'prod-user'

        # Use the configuration in a task
        @task
        def deploy():
            put('a_file.txt', config()['deploy_dir']

        # Invoke the task with a role
        fab -R prod deploy
    '''

    def __init__(self, context):
        '''
        context: a function that returns a key for whatever the current
        configuration context is.  For example, host_context returns the
        current env.host of a task, which would be useful if configuration
        varied by host.
        '''
        super(ContextConfig, self).__init__(dict)
        self.context = context

    def __call__(self):
        '''
        Choose a configuration depending on the current context key.
        '''
        return self[self.context()]


class NamespaceContextConfig(collections.defaultdict):
    '''
    NamespaceContextConfig is a defaultdict of Namespace objects used to store
    configuration for contexts.  It is also a callable that returns the
    Namespace object for the current context.  Namespace objects allow
    attribute-style access, which has a lighter syntax than dict-style access.

    Usage example:

        # Create a config collection for each role
        config = NamespaceContextConfig(role_context)

        # Set configuration values for each role.
        config['dev'].deploy_dir = '/www/example.com'
        config['dev'].user = 'dev-user'
        config['prod'].deploy_dir = '/www/dev.example.com'
        config['prod'].user = 'prod-user'

        # Use the configuration in a task
        @task
        def deploy():
            put('a_file.txt', config().deploy_dir)

        # Invoke the task with a role
        fab -R prod deploy
    '''
    def __init__(self, context):
        '''
        context: a function that returns a key for whatever the current
        configuration context is.  For example, host_context returns the
        current env.host of a task, which would be useful if configuration
        varied by host.
        '''
        super(NamespaceContextConfig, self).__init__(Namespace)
        self.context = context

    def __call__(self):
        '''
        Choose a configuration depending on the current context key.
        '''
        return self[self.context()]


class AttrDictContextConfig(collections.defaultdict):
    '''
    AttrDictContextConfig is a defaultdict of AttrDict objects used to store
    configuration.  It is also a callable that returns the AttrDict for the
    current context.  An AttrDict is useful when you want attribute-style
    and dict-style access to configuration values.  But why do you want that?

    Usage example:

        # Create a config collection for each role
        config = AttrDictContextConfig(role_context)

        # Set configuration values for each role.
        config['dev'].deploy_dir = '/www/example.com'
        config['dev'].user = 'dev-user'
        config['prod'].deploy_dir = '/www/dev.example.com'
        config['prod'].user = 'prod-user'

        # Use the configuration in a task
        @task
        def deploy():
            put('a_file.txt', config().deploy_dir)

        # Invoke the task with a role
        fab -R prod deploy
    '''

    def __init__(self, context):
        '''
        context: a function that returns a key for whatever the current
        configuration context is.  For example, host_context returns the
        current env.host of a task, which would be useful if configuration
        varied by host.
        '''
        super(AttrDictContextConfig, self).__init__(AttrDict)
        self.context = context

    def __call__(self):
        '''
        Choose a configuration depending on the current context key.
        '''
        return self[self.context()]


class Namespace(object):
    '''
    Use this if you want to instantiate an object to serve as a namespace.

    Example:
        foo = Namespace()
        # assignment
        foo.bar = 1
        # access
        print foo.bar; # prints '1'
        # testing for presence
        'bar' in foo # True
        hasattr(foo, 'bar') # True
        # iteration is a bit awkward
        for attrname in foo:
            value = getattr(foo, attrname)
            setattr(foo, attrname, 'Hi {}'.format(value))

    '''
    def __iter__(self):
        return iter(self.__dict__)


class AttrDict(dict):
    '''
    A dictionary whose keys can also be accessed as items or attributes.
    This provides syntactic sugar to avoid typing lots of brackets and quotes.
    However by conflating attribute and item access semantics it can lead to
    strange behavior.

    Example:

        obj = AttrDict()
        obj['key1'] = 'hi'
        obj.key2 = 'hello'
        print obj['key1']
        print obj.key2

    Example of strange behavior when setting a built-in attribute:

        obj = AttrDict()
        obj.hi = 'hello!'
        print obj.get('hi') # 'hello!'
        obj.get = 'bye' # overwrite dict get function?  No.
        print obj.get # <built-in method get of AttrDict object at ...>
        print obj['get'] # 'bye'
        print obj.get('hi') # 'hello!'.  get() still works.
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



