'''Sources for artifact'''

import os
import re
import shutil
import tempfile
import urllib
import zipfile
import github



class Source(object):
    """Source base class"""
    def download(self):
        """Method to download source"""
        raise NotImplementedError

    def filepath(self):
        """return the path to the temporary source directory"""
        raise NotImplementedError

    def archive_type(self):
        """return the path to the temporary source directory"""
        raise NotImplementedError

    def clean(self):
        """Method to clean up path"""
        shutil.rmtree(os.path.dirname(self.filepath()))

    def extract(self, dest):
        """Extract package to file path"""
        if self.archive_type() == 'zip':
            return self._extract_zip(self.filepath(), dest)
        else:
            raise Exception('invalid archive type')


    def _extract_zip(self, archive, dest):
        """Unzip archive to dest"""
        zp = zipfile.ZipFile(archive, 'r')
        zp.extractall(dest)
        zip_dir = zp.namelist()[0]

        zp.close()

        # Return top level zip directory
        res_dir = os.path.join(dest, zip_dir)
        return res_dir


class Github(Source):
    def __init__(self, token, owner, repo, revision):
        self._github = github.Github(token)
        self._owner = owner
        self._repo = repo
        self._revision = revision
        self._tmp_dir = None
        self._file_name = "{}_{}_{}.zip".format(self._owner,
                self._repo, self._revision)

    def download(self):
        """Implement download() method"""
        self._tmp_dir = tempfile.mkdtemp()
        repo = self._github.get_repo(self._owner + '/' + self._repo)
        arch_link = repo.get_archive_link('zipball',
                                          self._revision)
        urllib.request.urlretrieve(arch_link,
                os.path.join(self._tmp_dir, self._file_name))

    def filepath(self):
        """Return file path"""
        return os.path.join(self._tmp_dir, self._file_name)

    def archive_type(self):
        """Return the archive type"""
        return 'zip'
