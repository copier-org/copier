# -*- coding: utf-8 -*-
from __future__ import print_function

from collections import namedtuple
import re
import shutil
import subprocess
import tempfile


rx_vcs = re.compile(r'^(git|hg)(@|\+[a-z]+://|://)', re.IGNORECASE)


VCS = namedtuple('VCS', 'type url')


def get_vcs_from_url(url):
    """Try to identify the URL as a git or mercurial repo and return a
    namedtuple `(type url)` if have success.
    """
    match = rx_vcs.match(url)
    if match:
        vcs_type = match.group(1)
        vcs_url = normalize_url(url)
    elif url.endswith('.git'):
        vcs_type = 'git'
        vcs_url = url
    else:
        return
    return VCS(vcs_type, vcs_url)


def normalize_url(url):
    if not url.startswith(('git+', 'hg+')):
        return url
    return url[4:]


def clone(vcs, quiet=False):
    """Clone a repo to a temporal folder and return the path.
    """
    location = tempfile.mkdtemp()
    shutil.rmtree(location)  # Path must not exists
    if not quiet:
        print('Cloning from {0}'.format(vcs.url))

    try:
        subprocess.check_call([vcs.type, 'clone', vcs.url, location])
    except:
        return None
    return location
