#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
============
Voodoo
============

Voodoo is a template system for project skeletons (similar to the template part
of PasteScript): It can make a copy of a project skeleton processing some files,
filter others, etc.

It generates a beautiful output and take care of not overwrite existing files,
unless instructed to do so.

See the documentation and code at: `<http://github.com/lucuma/Voodoo>`_

"""
from voodoo.main import render_skeleton
from voodoo.cli import prompt, prompt_bool

__version__ = '1.3.5'

reanimate_skeleton = render_skeleton  # backward compat
