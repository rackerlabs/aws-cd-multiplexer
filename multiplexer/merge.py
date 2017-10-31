'''Main functionality for artifact creation'''

import copy
import os
import logging
import random
import re
import shutil
import string
import tempfile
import zipfile

from os import path
from multiplexer.source import Github

import boto3
import yaml

LOG = logging.getLogger(__name__)
S3_REGEX = r'^s3:\/\/([a-zA-Z0-9\_\-]+)\/?([a-zA-Z0-9\_\/]+)?'


def random_string(length):
    return ''.join(random.choice(
        string.ascii_letters + string.digits) for _ in range(length))


class Package(object):
    """Handles packaging the resulting artifact"""
    def __init__(self, name, root):
        if re.search(r'.zip$', name):
            self.name = name
        else:
            self.name = name + '.zip'
        self.root = path.abspath(root)
        self.package_path = path.join(self.root, self.name)

        tmp_dir_name = '.aws_cd_multiplex-' + random_string(10)
        self._tmp_workspace = path.join(self.root, tmp_dir_name)
        os.makedirs(self._tmp_workspace)

    def add_file(self, name, source=None, body=None):
        """
        Add a single file to package, must either provide
        a source file to copy or a body of a new file to write.

        Arguments:
        name -- name of file in package

        Keyword arguments:
        source -- Source of new file to write into package.
                  Mutually exclusive with body arg.
        body -- Body of new file to write into package.
                Mutually exclusive with source arg.
        """

        dest = path.join(self._tmp_workspace, name)
        if not source and not body:
            raise TypeError('must set either source or body')

        if source:
            shutil.copyfile(source, dest)
        if body:
            with open(dest, 'w+') as fil:
                fil.write(body)


    def add_directory(self, name, source=None):
        """
        Add directory to package, if no source is provided
        an empty directory is created.

        Arguments:
        source -- path to source directory
        """
        dest = path.join(self._tmp_workspace, name)
        if source:
            shutil.copytree(source, dest)
        else:
            os.mkdir(dest)

    def create(self):
        """
        Create the package zipfile

        Returns Full Path to package
        """
        zf = zipfile.ZipFile(self.package_path, 'w', zipfile.ZIP_DEFLATED)
        abs_src = self._tmp_workspace
        for root, _, files in os.walk(self._tmp_workspace):
            for filename in files:
                absname = path.abspath(path.join(root, filename))
                arcname = absname[len(abs_src) + 1:]
                LOG.debug('Zipping %s as %s'
                        % (path.join(root, filename), arcname))
                zf.write(absname, arcname)
        zf.close()
        LOG.info("Zipfile %s created" % self.package_path)
        return self.package_path

    def clean_tmp(self):
        """clean up tmp"""
        shutil.rmtree(self._tmp_workspace)


class AppSpec(object):
    """Appspec file"""
    def __init__(self, package_name):
        self.package_name = package_name
        self.version = None
        self.os = None
        self.files = []
        self.hooks = {}
        self._raw = None

    def load(self, yml_str):
        """Load an AppSpec file from the filesystem"""
        self._raw = yaml.load(yml_str)
        self.version = self._raw['version']
        self.os = self._raw['os']
        self._rewrite_paths()

    def _rewrite_paths(self):
        """Rewrite appspec paths with package name"""
        for fil in self._raw.get('files', []):
            prev_pth = fil['source']
            # path.join('name', '/') results in '/' so ensure
            # we have the correct source.
            if prev_pth == '/':
                fil['source'] = '/' + self.package_name + '/'
            else:
                fil['source'] = path.join(
                        '/',
                        self.package_name,
                        prev_pth)
            self.files.append(fil)

        for hook, items in self._raw.get('hooks', {}).items():
            self.hooks[hook] = []
            for item in items:
                prev_loc = item['location']
                item['location'] = path.join(
                        '/',
                        self.package_name,
                        prev_loc)
                self.hooks[hook].append(item)

    def merge(self, appspec):
        """
        Return self and appspec file provided as a new
        appspec file merged.
        """
        # Validate version, if not set then take new appspec version
        if self.version and self.version != appspec.version:
            raise Exception('appspec version mismatch')
        else:
            self.version = appspec.version

        # Validate OS, if not set then take new appspec OS
        if self.os and self.os != appspec.os:
            raise Exception('appspec version mismatch')
        else:
            self.os = appspec.os

        # Start with copy of self
        new_spec = copy.deepcopy(self)
        new_spec.files.extend(appspec.files)

        for hook, items in appspec.hooks.items():
            exist_hook = new_spec.hooks.get(hook)
            if exist_hook:
                new_spec.hooks[hook].extend(items)
            else:
                new_spec.hooks[hook] = items
        return new_spec

    def serialize(self):
        """Return YAML string representation of object"""
        obj = { 'version': self.version,
                'os': self.os,
                'files': self.files,
                'hooks': self.hooks }
        return yaml.dump(obj, default_flow_style=False)


def upload_to_s3(source, destination):
    """Given a source file, upload it to S3"""
    s3_info = re.search(S3_REGEX, destination)
    bucket = s3_info.group(1)
    key = s3_info.group(2)

    s3 = boto3.resource('s3')
    full_key = path.basename(source)
    if key:
        full_key = path.join(key, path.basename(source))
    LOG.info("Uploading %s to bucket %s as %s"
            % (source, bucket, full_key))
    s3.meta.client.upload_file(source, bucket, full_key)


def build_artifact(name, config, destination, clean=True):
    """Given an artifact name and config build a complete artifact"""
    workspace = tempfile.mkdtemp()
    artifact = config.artifact(name)
    pkg_destination = destination

    # If using S3 then set temporary worspace as destination
    store_s3 = re.search(S3_REGEX, destination)
    LOG.debug("Package destination %s is S3" % destination)
    if store_s3:
        pkg_destination = workspace

    pkg = Package(name, pkg_destination)

    global_appspec = AppSpec('global')
    for src_name, src_info in artifact['sources'].items():
        LOG.info("Fetching source %s for %s" % (src_name, name))
        src = Github(config.github['token'], src_info['owner'],
                     src_info['repository'], src_info['revision'])
        src.download()
        LOG.info("Source %s downloaded" % src_name)
        pth = src.extract(workspace)
        pkg.add_directory(src_info['repository'], source=pth)
        src.clean()

        # If source has an appspec file listed, then merge it to global
        src_appspec_file = path.join(pth, 'appspec.yml')
        if path.isfile(src_appspec_file):
            src_appspec = AppSpec(src_info['repository'])

            with open(src_appspec_file, 'r') as a_fil:
                src_appspec.load(a_fil.read())
            global_appspec = global_appspec.merge(src_appspec)

    pkg.add_file('appspec.yml', body=global_appspec.serialize())
    final_pkg = pkg.create()

    if store_s3:
        upload_to_s3(final_pkg, destination)

    if clean:
        LOG.debug("removing workspace files: " + workspace)
        pkg.clean_tmp()
        shutil.rmtree(workspace)
