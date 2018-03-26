#!/usr/bin/env python
# coding=utf-8
from __future__ import print_function

from os import getenv, urandom, getcwd
from os.path import join, expanduser, isdir, basename
from hashlib import sha512
import shutil

import baker

from voodoo.helpers import make_dirs, list_dirs
from voodoo.main import render_skeleton
from voodoo.vcs import get_vcs_from_url, clone


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
    for index, template_folder in enumerate(list_dirs(VOODOO_TEMPLATES_DIR)):
        print("{index}: {template_folder}".format(
            index=index, template_folder=basename(template_folder))
        )


@baker.command
def new(template, destination_folder=None):
    """Render the `template` at the `destination_folder`."""
    if destination_folder is None:
        destination_folder = getcwd()
    
    if isdir(template):
        print('The template is a local folder')
        new_from_folder(template, destination_folder)
        return

    vcs = get_vcs_from_url(template)
    if vcs:
        print('The template is an URL repo')
        new_from_vcs(vcs, destination_folder)
        return

    print('Using the previously installed template')
    new_from_name(template, destination_folder)


def new_from_folder(template_path, destination_folder):
    new_project(destination_folder, template_path)


def new_from_vcs(vcs, destination_folder):
    temp_folder = clone(vcs)
    new_project(destination_folder, temp_folder)
    shutil.rmtree(temp_folder)


def new_from_name(template_name, destination_folder):
    make_dirs(VOODOO_TEMPLATES_DIR)
    template_folder = join(VOODOO_TEMPLATES_DIR, template_name)
    if not isdir(template_folder):
        raise IOError("Template {template_name} does not exist.".format(
            template_name=template_name))
    new_project(destination_folder, template_folder)


@baker.command
def install(template_url, template_name=None):
    """Installs the template in VOODOO_TEMPLATES_DIR"""
    # TODO: Use template_name
    vcs = get_vcs_from_url(template_url)
    if vcs:
        make_dirs(VOODOO_TEMPLATES_DIR)
        clone(vcs, VOODOO_TEMPLATES_DIR)
        print('done')
    else:
        print("Couldn't process URL.")


def run():
    baker.run()


if __name__ == '__main__':
    run()
