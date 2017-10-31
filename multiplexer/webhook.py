'''Lambda related functions'''

import hmac
import json
import logging
import os

from os import path
from multiplexer import config

import boto3

LOG = logging.getLogger()
LOG.setLevel(logging.getLevelName(
    os.getenv('WEBHOOK_LOGLEVEL') or 'WARNING'))


def server_response(code, body):
    return {'statusCode': code, 'body': body}


def server_error(body='unexpected server error'):
    return server_response(500, body)


def validate_signature(body, github_signature):
    '''Validate Github signature'''
    if not github_signature:
        return server_response(400, 'missing Github signature')

    webhook_secret = os.getenv('WEBHOOK_SECRET')
    if not webhook_secret:
        LOG.info("Missing environment variable WEBHOOK_SECRET")
        return server_error()

    sha, signature = github_signature.split('=')
    if sha != 'sha1':
        return server_error()

    mac = hmac.new(webhook_secret.encode(), msg=body.encode(), digestmod='sha1')
    if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
        return server_response(401, 'invalid github signature')

    return False


def github_handler(event, context):
    '''Parses Github events and kicks off CodeBuild'''
    headers = event.get('headers', {})
    config_bucket = os.getenv('MULTIPLEXER_CONFIG_BUCKET')
    config_name = os.getenv('MULTIPLEXER_CONFIG_NAME')

    github_action_header = headers.get('X-GitHub-Event')
    if not github_action_header:
        return server_response(400, 'malformed request')
    if not github_action_header == 'push':
        LOG.info("Unsupported Github action %s ... ignoring" % github_action_header)
        return server_response(200, 'unsupported Github action recieved ... ignoring')

    github_signature = headers.get('X-Hub-Signature')
    valid_sig = validate_signature(event['body'], github_signature)
    if valid_sig:
        return valid_sig

    LOG.info("Github signature validated")

    github_body = json.loads(event['body'])
    ref = github_body['ref']
    revision = path.basename(ref)
    source = github_body['repository']['full_name']

    conf = config.load_s3(config_bucket, config_name)
    affected_artifacts = conf.lookup_artifacts(source, revision)

    artifact_names = []
    for artifact in affected_artifacts:
        artifact_names.append(artifact['name'])

    project_name = os.getenv('MULTIPLEXER_CODEBUILD_PROJECT')
    codebuild = boto3.client('codebuild')
    codebuild.start_build(
        projectName=project_name,
        environmentVariablesOverride=[
            {
                'name': 'ARTIFACTS',
                'value': ' '.join(artifact_names),
            }
        ]
    )

    body = 'Recieved push to branch ' + revision + ' for ' + source
    return server_response(201, body)
