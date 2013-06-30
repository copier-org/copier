# -*- coding: utf-8 -*-
from __future__ import print_function
from hashlib import sha512
from os import urandom
from os.path import join, dirname, basename

from voodoo import render_skeleton


default_context = {
    'py3': True,
    'make_secret': lambda: sha512(urandom(48)).hexdigest()
}
SKELETON_PATH = join(dirname(__file__), '..', 'tests', 'demo')


def new_project(path, options):
    data = default_context.copy()
    data['package'] = basename(path)
    # print(SKELETON_PATH, path, data, options)
    render_skeleton(SKELETON_PATH, path, data=data, **options)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Create a new project')
    parser.add_argument('path', help='The name or fullpath of the new project')
    parser.add_argument('-p', '--pretend', action='store_true',
                        help='Run but do not make any changes')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Overwrite files that already exist, without asking')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip files that already exist, without asking')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress status output')

    args = parser.parse_args()
    da = vars(args)
    new_project(da.pop('path'), da)
