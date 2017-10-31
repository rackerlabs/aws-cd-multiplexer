'''Configuration module test'''
from multiplexer.config import Configuration, load_s3
import pytest
import boto3
from moto import mock_s3


@mock_s3
def test_load_s3_config():
    '''Test configuration load'''

    conn = boto3.resource('s3', region_name='us-east-1')
    bucket_name = 'testconfig'
    bucket_object = 'myconfig.json'

    body = '''{"sources":{"app1":{"type":"github","owner":"myorg","repository":"app1"},"app2":{"type":"github","owner":"myorg","repository":"app2"},"app3":{"type":"github","owner":"myorg","repository":"app3"}},"artifacts":[{"name":"production/allapps","sources":[{"name":"app1","revision":"prod"},{"name":"app2","revision":"master"},{"name":"app3","revision":"production"}]},{"name":"staging/allapps","sources":[{"name":"app1","revision":"prod"},{"name":"app3","revision":"staging"}]}]}'''

    conn.create_bucket(Bucket=bucket_name)
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.put_object(Bucket=bucket_name, Key=bucket_object, Body=body)

    config = load_s3(bucket_name, bucket_object)

    expect_repositories = ['app1', 'app2', 'app3']
    for res_repo in config._raw['sources'].keys():
        assert res_repo in expect_repositories


def test_lookup_artifacts():
    '''Test configuration load'''

    body = '''{"sources":{"app1":{"type":"github","owner":"myorg","repository":"app1"},"app2":{"type":"github","owner":"myorg","repository":"app2"},"app3":{"type":"github","owner":"myorg","repository":"app3"}},"artifacts":[{"name":"production/allapps","sources":[{"name":"app1","revision":"prod"},{"name":"app2","revision":"master"},{"name":"app3","revision":"production"}]},{"name":"staging/allapps","sources":[{"name":"app1","revision":"prod"},{"name":"app3","revision":"staging"}]}]}'''

    config = Configuration(body)

    # Validate both artifacts are returned
    exp_artifacts = {'production/allapps', 'staging/allapps'}
    artifacts = config.lookup_artifacts('myorg/app1', 'prod')
    artifact_names = set([a['name'] for a in artifacts])

    assert len(exp_artifacts.difference(artifact_names)) == 0
