#!/usr/bin/env python
# coding=utf-8
from __future__ import print_function

from os import getenv, urandom, getcwd
from os.path import join, expanduser, isdir, basename
from hashlib import sha512

import baker

from voodoo.helpers import make_dirs, list_dirs
from voodoo.main import render_skeleton
from voodoo.vcs import get_vcs_from_url, clone_install


default_context = {
    'make_secret': lambda: sha512(urandom(48)).hexdigest()
}


VOODOO_TEMPLATES_DEFAULT_DIR = join(expanduser("~/"), ".voodoo/templates/")
VOODOO_TEMPLATES_DIR = getenv('VOODOO_TEMPLATES_DIR', VOODOO_TEMPLATES_DEFAULT_DIR)


def new_project(path, tmpl=None, **options):
    """Creates a new project using tmpl at path."""
    if tmpl is None:
        raise ValueError("tmpl must be be a path to the template.")
    data = default_context.copy()
    render_skeleton(tmpl, path, data=data, **options)


@baker.command
def list():
    print("Voodoo Templates installed:")
    make_dirs(VOODOO_TEMPLATES_DIR)
    for index, template_dir in enumerate(list_dirs(VOODOO_TEMPLATES_DIR)):
        print("{index}: {template_dir}".format(
            index=index, template_dir=basename(template_dir))
        )


@baker.command
def new(template_name, destination_directory=None):
    """Render the `template_name` template at the `destination_directory`."""
    if destination_directory is None:
        destination_directory = getcwd()
    make_dirs(VOODOO_TEMPLATES_DIR)
    template_dir = join(VOODOO_TEMPLATES_DIR, template_name)
    if not isdir(template_dir):
        raise IOError("Template {template_name} does not exist.".format(
            template_name=template_name))

    new_project(destination_directory, template_dir)


@baker.command
def install(template_url, template_name=None):
    """Installs the template in VOODOO_TEMPLATES_DIR"""
    # TODO: Use template_name
    vcs = get_vcs_from_url(template_url)
    if vcs:
        make_dirs(VOODOO_TEMPLATES_DIR)
        clone_install(vcs, VOODOO_TEMPLATES_DIR)
        print('done')
    else:
        print("Couldn't process URL.")


def run():
    baker.run()


if __name__ == '__main__':
    run()
