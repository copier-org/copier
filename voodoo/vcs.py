# coding=utf-8
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
        return
    return VCS(vcs_type, vcs_url)


def normalize_url(url):
    """Ensure the url doesn't start with either git or hg."""
    if not url.startswith(('git+', 'hg+')):
        return url
    return url[4:]


def clone(vcs, location=None):
    """Clone a repo to `location` folder, if no location is given, create a
    temporary folder.

    Returns the path where the repository was cloned to.
    """
    if not location:
        return _clone_to_temp(vcs)
    return _clone_to(vcs, location)


def _clone_to_temp(vcs):
    location = tempfile.mkdtemp()
    shutil.rmtree(location)  # Path must not exists
    try:
        subprocess.check_call([vcs.type, 'clone', vcs.url, location])
    except Exception as e:
        print(e)
        return None
    return location


def _clone_to(vcs, location):
    """Clone a repo inside the `location` folder."""
    try:
        subprocess.Popen([vcs.type, 'clone', vcs.url], cwd=location)
    except:
        return location
