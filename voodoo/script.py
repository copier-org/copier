#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
from os import getenv, urandom, getcwd
from os.path import join, expanduser, isdir
from hashlib import sha512
from shutil import copytree

import baker

from voodoo.main import render_skeleton
from voodoo.vcs import get_vcs_from_url, clone_install
from voodoo.dir_utils import ensure_directory, list_dirs


default_context = {
    'make_secret': lambda: sha512(urandom(48)).hexdigest()
}



VOODOO_TEMPLATES_DEFAULT_DIR = join(expanduser("~/"), ".voodoo/templates/")
VOODOO_TEMPLATES_DIR = getenv('VOODOO_TEMPLATES_DIR',
                              VOODOO_TEMPLATES_DEFAULT_DIR)
ensure_directory(VOODOO_TEMPLATES_DIR)


def new_project(path, tmpl=None, **options):
    """Creates a new project using tmpl at path."""
    if tmpl is None:
        raise ValueError("tmpl must be be a path to the template.")
    data = default_context.copy()
    render_skeleton(
        tmpl, path, data=data,
        filter_this=['voodoo.json', '.git/*', '.hg/*'],
        include_this=['.gittouch'],
        **options
    )

@baker.command
def list():
    print("Voodoo Templates installed:")
    for index, template_dir in enumerate(list_dirs(VOODOO_TEMPLATES_DIR)):
        print("{index}: {template_dir}".format(index=index, template_dir=template_dir))

@baker.command
def new(template_name, destination_directory=None):
    """Render the `template_name` template at the `destination_directory`."""
    if destination_directory is None:
       destination_directory = getcwd()

    template_dir = join(VOODOO_TEMPLATES_DIR, template_name)
    if not isdir(template_dir):
        raise IOError("Template {template_name} does not exist.".format(
            template_name=template_name))

    new_project(desination_directory, template_dir)

@baker.command
def install(template_url, template_name=None):
    """Installs the template in VOODOO_TEMPLATES_DIR"""
    # TODO: Use template_name
    vcs = get_vcs_from_url(template_url)
    clone_install(vcs, VOODOO_TEMPLATES_DIR)

if __name__ == '__main__':
    baker.run()
