'''Configuration module test'''
import os
from multiplexer.merge import AppSpec, Package
import pytest


def test_package():
    '''Test Packaging'''
    curr_location = os.path.dirname(os.path.realpath(__file__))
    testing_tmp = os.path.join(curr_location, 'tmp')

    pkg = Package('myartifact.zip', testing_tmp)
    assert os.path.isdir(pkg._tmp_workspace)

    pkg.add_file('testfile',
                 source=os.path.join(curr_location, 'testfile'))
    assert os.path.isfile(os.path.join(pkg._tmp_workspace, 'testfile'))

    pkg.add_directory('src')
    assert os.path.isdir(os.path.join(pkg._tmp_workspace, 'src'))

    pkg.add_file('src/testfile2', body='Another test file')
    assert os.path.isfile(os.path.join(pkg._tmp_workspace,
                                       'src/testfile2'))

    pkg.add_directory('scripts', source=os.path.join(curr_location, 'testdir'))
    assert os.path.isdir(os.path.join(pkg._tmp_workspace, 'scripts'))
    assert os.path.isfile(os.path.join(pkg._tmp_workspace,
                                       'scripts/another_testfile'))

    pkg.create()
    assert os.path.isfile(os.path.join(testing_tmp, 'myartifact.zip'))

    pkg.clean_tmp()
    assert not os.path.isdir(pkg._tmp_workspace)


def test_load_appspec():
    '''Test Appspec Load'''

    body = '''---
version: 0.0
os: linux
files:
  - source: Config/config.txt
    destination: /webapps/Config
  - source: source
    destination: /webapps/myApp
hooks:
  BeforeInstall:
    - location: Scripts/UnzipResourceBundle.sh
    - location: Scripts/UnzipDataBundle.sh
  AfterInstall:
    - location: Scripts/RunResourceTests.sh
      timeout: 180
  ApplicationStart:
    - location: Scripts/RunFunctionalTests.sh
      timeout: 3600
  ValidateService:
    - location: Scripts/MonitorService.sh
      timeout: 3600
      runas: codedeployuser
'''

    appspec = AppSpec('myapp')
    appspec.load(body)

    expect_files = [
        {'source': '/myapp/Config/config.txt', 'destination': '/webapps/Config'},
        {'source': '/myapp/source', 'destination': '/webapps/myApp'}
    ]
    assert appspec.files == expect_files

    expected_hooks = {'BeforeInstall': [{'location': 'myapp/Scripts/UnzipResourceBundle.sh'},
                                      {'location': 'myapp/Scripts/UnzipDataBundle.sh'}],
                    'ValidateService': [{'timeout': 3600, 'runas': 'codedeployuser',
                                         'location': 'myapp/Scripts/MonitorService.sh'}],
                    'AfterInstall': [{'timeout': 180, 'location': 'myapp/Scripts/RunResourceTests.sh'}],
                    'ApplicationStart': [{'timeout': 3600, 'location': 'myapp/Scripts/RunFunctionalTests.sh'}]}

    # Validate all keys match
    for hook_name, hooks in expected_hooks.items():
        got_hooks = appspec.hooks.get(hook_name)

        assert got_hooks
        assert len(got_hooks) == len(expected_hooks[hook_name])


def test_merge_appspec():
    '''Test configuration load'''

    appspec1_body = '''---
version: 0.0
os: linux
files:
  - source: Config/config.txt
    destination: /webapps/Config
  - source: source
    destination: /webapps/myApp
hooks:
  BeforeInstall:
    - location: Scripts/UnzipResourceBundle.sh
    - location: Scripts/UnzipDataBundle.sh
'''

    appspec2_body = '''---
version: 0.0
os: linux
files:
  - source: Config/config.txt
    destination: /webapps/Config
  - source: source
    destination: /webapps/myApi
hooks:
  BeforeInstall:
    - location: Scripts/migrate.sh
'''

    appspec = AppSpec('myapp')
    appspec.load(appspec1_body)

    sec_appspec = AppSpec('myapi')
    sec_appspec.load(appspec2_body)

    res_appspec = appspec.merge(sec_appspec)
    expect_before_install = [
        {'location': '/myapp/Scripts/UnzipResourceBundle.sh'},
        {'location': '/myapp/Scripts/UnzipDataBundle.sh'},
        {'location': '/myapi/Scripts/migrate.sh'}
    ]

    assert expect_before_install == res_appspec.hooks['BeforeInstall']
