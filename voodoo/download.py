# -*- coding: utf-8 -*-
from __future__ import print_function

import shutil
import tempfile

from pip.vcs import vcs as pip_vcs
from voodoo._compat import urlparse


VCS = ('git', 'hg')


def get_vcs_from_url(url):
    if not url.startswith(VCS):
        return
    link = urlparse.urlparse(normalize_url(url))
    for backend in pip_vcs.backends:
        if link.scheme in backend.schemes:
            vcs = backend(url)
            return vcs


def normalize_url(url):
    if url.startswith('git+git@'):
        url = url.replace('git+git@', 'git+git://')
    return url


def download(vcs, quiet=False):
    location = tempfile.mkdtemp()
    shutil.rmtree(location)  # Path must not exists
    if not quiet:
        print(u'Downloading from: {0}'.format(vcs.url))
    vcs.obtain(location)
    return location
