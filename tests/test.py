

def test_config():
    import diabric.config
    import fabric.api
    conf = diabric.config.ContextConfig(diabric.config.role_context)
    fabric.api.env.roles = ["hi"]
    assert conf["hi"] == {}
    assert conf() == {}
    conf()['foo'] = 2
    assert conf() == {'foo': 2}


def test_fix_shebang():
    '''
    Test replacing a shebang and adding a shebang.
    Test using a malformed shebang and a well-formed shebang.
    '''
    import diabric.files

    add_shebang = '''hi
there
'''
    replace_shebang = '''#!/user/bin/foo
hi
there
'''
    nice_shebang = '#!/usr/bin/env python\n'
    ugly_shebang = '/usr/bin/env python'
    outdata = '''#!/usr/bin/env python
hi
there
'''

    for indata in [add_shebang, replace_shebang]:
        for shebang in [nice_shebang, ugly_shebang]:
            assert ''.join(diabric.files.fix_shebang(shebang, indata.splitlines(True))) == outdata


def test_upload_shebang():
    '''
    Write a file with a shebang to upload and fix.
    Upload and fix the file.
    Read the uploaded file and compare to what should have been uploaded.
    '''
    import diabric.files
    import fabric.api
    import StringIO
    import tempfile
    import os

    replace_shebang = '''#!/user/bin/foo
hi
there
'''
    nice_shebang = '#!/usr/bin/env python\n'
    outdata = '''#!/usr/bin/env python
hi
there
'''
    fd1, name1 = tempfile.mkstemp()
    fd2, name2 = tempfile.mkstemp()
    result = None
    try:
        with open(name1, 'w') as fh:
            fh.write(replace_shebang)

        fabric.api.env.host_string = 'localhost'
        diabric.files.upload_shebang(name1, name2, nice_shebang)
        with open(name2) as fh:
            result = fh.read()
    finally:
        os.unlink(name1)
        os.unlink(name2)
    assert result == outdata



