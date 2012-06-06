
import boto


###########
# INSTANCES


def get_latest_on_instance(conn=None, instance_ids=None, filters=None,
                           tags=None):
    '''
    conn: an boto.ec2.connection.Connection object.  Defaults to
    the connection from boto.connect_ec2().

    Return: the "on" instance matching TAGS with the most recent launch time,
    or None if there are no instances matching the criteria.
    Return: the instance of the current server, of None if there is none.
    Raise: Exception if there is more than one non-terminated instance.
    '''
    instances = get_on_instances(conn=conn, instance_ids=instance_ids,
                                 filters=filters, tags=tags)
    instances = sort_by_launch(instances)
    if not instances:
        return None
    else:
        return instances[-1]


def get_on_instances(conn=None, instance_ids=None, filters=None, tags=None):
    '''
    conn: an boto.ec2.connection.Connection object.  Defaults to
    the connection from boto.connect_ec2().

    Return all the "on" instances matching the default TAGS.
    '''
    instances = get_instances(conn=conn, instance_ids=instance_ids,
                              filters=filters, tags=tags)
    instances = filter_by_on(instances)
    return instances


def get_latest_on_host(conn=None, instance_ids=None, filters=None, tags=None):
    '''
    Return the hostname/public dns name of the latest on instance or None if
    there is no such instance.
    '''
    instance = get_latest_on_instance(conn=conn, instance_ids=instance_ids,
                                      filters=filters, tags=tags)
    if instance:
        return instance.public_dns_name
    else:
        return None


def get_on_hosts(conn=None, instance_ids=None, filters=None, tags=None):
    '''
    Return a list of hostnames/public dns names, one for each on instance
    matching the search criteria (instance_ids, filters, tags).
    '''
    return [i.public_dns_name for i in 
            get_on_instances(conn=conn, instance_ids=instance_ids,
                             filters=filters, tags=tags)]


def filter_by_on(instances):
    '''
    instances: a list of boto.ec2.instance.Instance objects
    Filter out instances that are 'terminated' or 'shutting-down'.
    Return a list of the remaining instances.
    '''
    bad_states = ['terminated', 'shutting-down']
    return [i for i in instances if i.state not in bad_states]


def sort_by_launch(instances, desc=False):
    '''
    instances: a list of boto.ec2.instance.Instance objects
    desc: False.  If True, sort in descending order.

    Return a list containing the instances in `instances` sorted by the
    launch_time attribute
    '''
    return sorted(instances, key=lambda i: i.launch_time)


def terminate_instances(instances, conn=None):
    '''
    Terminate instances.  Raise an exeption if not all instances are 
    terminated.

    instances: a list of boto.ec2.instance.Instance objects.
    conn: an boto.ec2.connection.Connection object.  Defaults to
    the connection from boto.connect_ec2().
    '''
    conn = conn or boto.connect_ec2()
    if not instances:
        return
    killed_instances = conn.terminate_instances([i.id for i in instances])
    if len(killed_instances) != len(instances):
        raise Exception('Not all instances terminated.', instances, 
                        killed_instances)


def get_instances(conn=None, instance_ids=None, filters=None, tags=None):
    '''
    Find all instances matching the given instance ids, filters and tags.  
    Return a list of boto.ec2.instance.Instance objects

    conn: an boto.ec2.connection.Connection object.  Defaults to
    the connection from boto.connect_ec2().
    instance_ids: a list of strings.  Retrict returned instances to only these
    instance ids.
    filters: a dict of key, value pairs used to filter the returned
    instances.  For example, to filter for all the instances with an
    'Name' tag of 'webserver', one would use {'tag:Name': 'webserver'}.
    See
    http://docs.amazonwebservices.com/AWSEC2/latest/UserGuide/Using_Filtering.html#filtering-resources
    and
    http://docs.amazonwebservices.com/AWSEC2/latest/UserGuide/Using_Tags.html
    for more details.
    tags: a dict of key, value pairs used to filter the returned instances.
    Keys in `tags` are tag names and values are tag values.  E.g. {'Name':
    'webserver'}.  All tag keys are converted into filter tag keys and
    merged with `filters`.  Therefore 'Name' becomes 'tag:Name'.
    '''
    conn = conn or boto.connect_ec2()
    if not (filters or tags):
        all_filters = None
    else:
        filters = filters or {}
        tags = tags or {}
        # merge filters and tags
        all_filters = filters.copy()
        all_filters.update(('tag:' + key, tags[key]) for key in tags)

    rs = conn.get_all_instances(instance_ids=None, filters=filters)
    return [i for r in rs for i in r.instances]


def print_instances(instances, use_repr=False):
    '''
    instances: a list of boto.ec2.instance.Instance objects
    Print some information about the instances to stdout.
    '''
    for instance in instances:
        print_instance(instance, use_repr)


def print_instance(instance, use_repr=False):
    '''
    use_repr: if True, attribute values are printed using repr, not str
    Print to stdout all the attributes of the instance, one attribute per line.
    '''
    print 'Instance'
    func = repr if use_repr else str
    for key in sorted(instance.__dict__):
        print '{}={}'.format(key, func(instance.__dict__[key]))


#################
# OTHER FUNCTIONS


def make_webserver_security_group():
    '''
    '''
    # this still needs to be tested and debugged.
    raise Exception('not implemented')
    # http://docs.pythonboto.org/en/latest/security_groups.html
    conn = boto.connect_ec2()
    sgs = conn.get_all_security_groups()
    print 'Existing security groups'
    for sg in sgs:
        print sg.name, sg.description, sg.rules

    if config.sec_group not in [sg.name for sg in sgs]:
        print 'Making security group: {}'.format(config.sec_group)
        sg = conn.create_security_group(config.sec_group, 'Home Web Server')
        # protocol, start port, end port, CIDR IP
        print sg.authorize('tcp', 80, 80, '0.0.0.0/0')
        print sg.authorize('tcp', 22, 22, '0.0.0.0/0')
    else:
        print 'Skipping existing security group: {}'.format(config.sec_group)


def make_key_pair():
    raise Exception('Not implemented')


