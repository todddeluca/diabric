
'''
Fabric utilities for working with files.
'''

import StringIO
import os
import subprocess

from fabric.api import sudo, run, settings, hide, put
from fabric.contrib.files import exists



################
# FILE FUNCTIONS


def fix_shebang(shebang, handle):
    '''
    shebang: a shebang line, e.g. #!/usr/bin/env python or #!/bin/sh.  If
    shebang does not start with '#!', then '#!' will be prepended to it.  If
    shebang does not end with a newline, a newline will be appended.

    handle: a iterable of lines, presumably the contents of a file that needs a
    shebang line or a new shebang line.

    Yield shebang and then the lines in handle except the first line in handle
    if it is a shebang line.
    '''
    # make sure shebang is starts with '#!' and ends with a newline.
    if not shebang.startswith('#!'):
        shebang = '#!' + shebang

    if not shebang.endswith('\n'):
        shebang += '\n'

    for i, line in enumerate(handle):
        if i == 0:
            yield shebang
            if not line.startswith('#!'):
                yield line
        else:
            yield line


def upload_shebang(filename, destination, shebang, use_sudo=False, backup=True,
                   mirror_local_mode=False, mode=None):
    """
    Upload a text file to a remote host, adding or updating the shebang line.

    ``filename`` should be the path to a text file.

    ``shebang`` should be a string containing a shebang line.  E.g.
    "#!/usr/bin/python\n".  If shebang does not start with '#!' or end with a
    newline, these will be added.

    If the first line in filename starts with '#!' it will be replaced with
    shebang.  If the first line does not start with #!, shebang will be
    prepended to the contents of filename.

    The resulting file will be uploaded to the remote file path
    ``destination``.  If the destination file already exists, it will be
    renamed with a ``.bak`` extension unless ``backup=False`` is specified.

    By default, the file will be copied to ``destination`` as the logged-in
    user; specify ``use_sudo=True`` to use `sudo` instead.

    The ``mirror_local_mode`` and ``mode`` kwargs are passed directly to an
    internal `~fabric.operations.put` call; please see its documentation for
    details on these two options.
    """
    func = use_sudo and sudo or run
    # Normalize destination to be an actual filename, due to using StringIO
    with settings(hide('everything'), warn_only=True):
        if func('test -d %s' % destination).succeeded:
            sep = "" if destination.endswith('/') else "/"
            destination += sep + os.path.basename(filename)

    # Use mode kwarg to implement mirror_local_mode, again due to using
    # StringIO
    if mirror_local_mode and mode is None:
        mode = os.stat(filename).st_mode
        # To prevent put() from trying to do this
        # logic itself
        mirror_local_mode = False

    # process filename
    text = None
    with open(filename) as inputfile:
        text = ''.join(fix_shebang(shebang, inputfile))

    # Back up original file
    if backup and exists(destination):
        func("cp %s{,.bak}" % destination)

    # Upload the file.
    put(
        local_path=StringIO.StringIO(text),
        remote_path=destination,
        use_sudo=use_sudo,
        mirror_local_mode=mirror_local_mode,
        mode=mode
    )


def upload_format(filename, destination, args=None, kws=None,
                  use_sudo=False, backup=True, mirror_local_mode=False,
                  mode=None):
    """
    Read in the contents of filename, format the contents via
    contents.format(*args, **kws), and upload the results to the
    destination on the remote host.

    ``filename`` should be the path to a text file.  The contents of
    ``filename`` will be read in.

    Format the contents, using contents.format(*args, **kws).  If
    args is None, it will not be included in the format() call.
    Likewise for kws.

    The resulting contents will be uploaded to the remote file path
    ``destination``.  If the destination file already exists, it will be
    renamed with a ``.bak`` extension unless ``backup=False`` is specified.

    By default, the file will be copied to ``destination`` as the logged-in
    user; specify ``use_sudo=True`` to use `sudo` instead.

    The ``mirror_local_mode`` and ``mode`` kwargs are passed directly to an
    internal `~fabric.operations.put` call; please see its documentation for
    details on these two options.
    """
    func = use_sudo and sudo or run
    # Normalize destination to be an actual filename, due to using StringIO
    with settings(hide('everything'), warn_only=True):
        if func('test -d %s' % destination).succeeded:
            sep = "" if destination.endswith('/') else "/"
            destination += sep + os.path.basename(filename)

    # Use mode kwarg to implement mirror_local_mode, again due to using
    # StringIO
    if mirror_local_mode and mode is None:
        mode = os.stat(filename).st_mode
        # To prevent put() from trying to do this
        # logic itself
        mirror_local_mode = False

    # process filename
    text = None
    with open(filename) as inputfile:
        if not args:
            args = []
        
        if not kws:
            kws = {}

        text = inputfile.read().format(*args, **kws)

    # Back up original file
    if backup and exists(destination):
        func("cp %s{,.bak}" % destination)

    # Upload the file.
    put(
        local_path=StringIO.StringIO(text),
        remote_path=destination,
        use_sudo=use_sudo,
        mirror_local_mode=mirror_local_mode,
        mode=mode
    )


def file_format(infile, outfile, args=None, kws=None):
    '''
    Consider using fabric.contrib.files.upload_template or upload_format
    infile: a local file path
    outfile: a local file path.
    Read the contents of infile as a string, ''.format() the string using args
    and kws, and write the formatted string to outfile.  This is useful if
    infile is a "template" and args and kws contain the concrete values
    for the template.
    '''
    if args is None:
        args = []
    if kws is None:
        kws is {}
    with open(infile) as fh:
        text = fh.read()
    new_text = text.format(*args, **kws)
    with open(outfile, 'w') as fh2:
        fh2.write(new_text)


def rsync(options, src, dest, user=None, host=None, cwd=None):
    '''
    Consider using fabric.contrib.project.rsync_project.
    options: list of rsync options, e.g. ['--delete', '-avz']
    src: source directory (or files).  Note: rsync behavior varies depending on whether or not src dir ends in '/'.
    dest: destination directory.
    cwd: change (using subprocess) to cwd before running rsync.
    This is a helper function for running rsync locally, via subprocess.  Note: shell=False.
    '''
    # if remote user and host specified, copy there instead of locally.
    if user and host:
        destStr = '{}@{}:{}'.format(user, host, dest)
    else:
        destStr = dest

    args = ['rsync'] + options + [src, destStr]
    print args
    subprocess.check_call(args, cwd=cwd)

