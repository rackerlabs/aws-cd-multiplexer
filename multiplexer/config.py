# -*- coding: utf-8 -*-
'''
Multiplexer Configuration

{
    "artifacts": [
        {
            "name": "production/allapps"
            "sources": [
                {"name": "app1", "revision": "prod"},
                {"name": "app2", "revision": "master"},
                {"name": "app3", "revision": "production"}
            ]
        },
        {
            "name": "staging/allapps"
            "sources": [
                {"name": "app1", "revision": "prod"}
                {"name": "app3", "revision": "staging"}
            ]
        }
    ],
    "github": {
        "token": "mytoken"
    },
"sources": {
    "app1": {
        "owner": "myorg",
        "repository": "app1",
        "type": "github"
    },
    "app2": {
        "type": "github"
        "revision": "production",
        "owner": "myorg"
        "repository": "app2"
    },
    "app3": {
        "type": "github",
        "owner": "myorg",
        "repo": app3"
    }
}
'''

import time

from collections import OrderedDict

import boto3
import json
import re


TYPES = {'github': {'token': None}}
S3_REGEX = r'^s3:\/\/([a-zA-Z0-9\_\-]+)\/?([a-zA-Z0-9\_\/\.]+)?'

def load(conf):
    '''Attempts to load the config after checking for S3 or local'''
    s3_info = re.search(S3_REGEX, conf)

    if s3_info:
        bucket = s3_info.group(1)
        key = s3_info.group(2)
        return load_s3(bucket, key)

    return load_file(conf)


def load_s3(s3_bucket, s3_object):
    """Load Configuration file from an S3 Bucket"""
    client = boto3.client('s3')
    resp = client.get_object(
            Bucket=s3_bucket,
            Key=s3_object,
    )

    conf_body = resp['Body'].read()
    if isinstance(conf_body, (bytes, bytearray)):
        conf_body = conf_body.decode('utf-8')
    return Configuration(conf_body)


def load_file(pth):
    """Load configuration from local file"""
    fil = open(pth, 'r')
    return Configuration(fil.read())


class Configuration(object):
    def __init__(self, body):
        self._raw = {}
        self.artifacts = []

        self._load(body)
        self._validate()

    def _load(self, raw_body):
        """Load JSON file"""
        body = json.loads(raw_body)
        self._raw = body

        # Populate self.artifacts
        for artifact in self._raw.get('artifacts', []):
            art_obj = {'name': artifact['name'], 'sources': OrderedDict()}

            for repo in artifact.get('sources', []):
                r_info = self._raw['sources'].get(repo['name'])
                if not r_info:
                    raise Exception(
                        'source {} defined in artifact {} but not listed in sources'.format(
                            repo['name'], artifact['name']))

                r = r_info.copy()
                r.update(repo)
                art_obj['sources'][repo['name']] = r
            self.artifacts.append(art_obj)

    def _validate(self):
        """Validate Configuration structure"""
        req = {'artifacts': list, 'sources': dict}
        for key, typ in req.items():
            val = self._raw.get(key)
            if not val:
                raise Exception('configuration missing required key ' + key)

            if not isinstance(val, typ):
                raise Exception('key {} invalid type, expect {}'.format(
                    key, typ))

            # TODO: Validate attributes are set per the type in sources
            for name, repo in self._raw['sources'].items():
                typ = repo.get('type')
                if not repo.get('type'):
                    raise Exception('source {} missing type'.format(
                        name))

                if not TYPES.get(typ):
                    raise ValueError('invalid type ' + typ)

                # If type configuration is not set then set the, defaults
                if not self._raw.get(typ):
                    self._raw[typ] = TYPES[typ]

    def lookup_artifacts(self, source, revision, source_type='github'):
        """Return a list of artifacts to build based on a source and revision"""
        if not source_type == 'github':
            raise Exception('github only supported source at this time')

        owner, repo = source.split('/')
        res_artifacts = []
        for artifact in self.artifacts:
            for name, info in artifact['sources'].items():
                if info['owner'] == owner and info['repository'] == repo and info['revision'] == revision:
                    res_artifacts.append(artifact)

        return res_artifacts

    def artifact(self, name):
        """Return the artifact object given a name"""
        for artifact in self.artifacts:
            if artifact['name'] == name:
                return artifact

        raise Exception('artifact {} does not exist'.format(name))

    def __getattr__(self, key):
        """Override getattr"""
        if key in self._raw:
            return self._raw[key]

        return object.__getattribute__(self, key)
