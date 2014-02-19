#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from hashlib import sha512
from os import urandom
import sys

from .main import render_skeleton


default_context = {
    'make_secret': lambda: sha512(urandom(48)).hexdigest()
}


def new_project(path, tmpl=None, **options):
    data = default_context.copy()
    render_skeleton(
        tmpl, path, data=data,
        filter_this=['voodoo.json', '.git/*', '.hg/*'],
        include_this=['.gittouch'],
        **options
    )


class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n\n' % message)
        self.print_help()
        sys.exit(2)


def run():
    parser = DefaultHelpParser(description='Create a project from a Voodoo project template.')
    parser.add_argument('tmpl',
                        help='Fullpath or a git/hg URL of a project template ')
    parser.add_argument('path',
                        help='The name or final fullpath of the new project')
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
    new_project(da.pop('path'), **da)


if __name__ == '__main__':
    run()
