#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# Voodoo

Voodoo is a template system for project skeletons (similar to the template
part of PasteScript):

It can make a copy of a project skeleton processing some files, filter
others, etc.

It generates a beatiful and colored output and take care of not overwrite
existing files, unless instructed to do so.

------------
© 2011 by [Lúcuma labs] (http://lucumalabs.com).
License: [MIT License] (http://www.opensource.org/licenses/mit-license.php).

"""
from .main import render_skeleton
from .cli import prompt, prompt_bool

__version__ = '1.1'

reanimate_skeleton = render_skeleton  # backward compat
