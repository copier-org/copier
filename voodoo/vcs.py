# -*- coding: utf-8 -*-
from __future__ import print_function

from collections import namedtuple
import re
import shutil
import subprocess
import tempfile


RX_VCS = re.compile(r'^(git|hg)(@|\+[a-z]+://|://)', re.IGNORECASE)

VCS = namedtuple('VCS', 'type url')


def get_vcs_from_url(url):
    """Try to identify the URL as a git or mercurial repo and return a namedtuple
    `(type url)` if have success.
    """
    match = RX_VCS.match(url)
    if match:
        vcs_type = match.group(1)
        vcs_url = normalize_url(url)
    elif url.endswith('.git'):
        vcs_type = 'git'
        vcs_url = url
    else:
        # TODO: Raise exception if unable to process URL.
        return
    return VCS(vcs_type, vcs_url)


def normalize_url(url):
    """Ensure the url doesn't start with either git or hg."""
    if not url.startswith(('git+', 'hg+')):
        return url
    return url[4:]


def clone(vcs, quiet=False):
    """Clone a repo to `location` folder, if no location is given, create a
    temporary folder.

    Returns the path where the repository was cloned to.
    """
    location = tempfile.mkdtemp()

    shutil.rmtree(location)  # Path must not exists
    if not quiet:
        print('Cloning from {0}'.format(vcs.url))

    try:
        subprocess.check_call([vcs.type, 'clone', vcs.url, location])
    except:
        return None
    return location


def clone_install(vcs, cwd=None):
    """Clone a repo inside the `cwd` directory."""
    try:
        subprocess.Popen([vcs.type, 'clone', vcs.url], cwd=cwd)
    except:
        return None
