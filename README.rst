============
Voodoo
============

Voodoo is a template system for project skeletons (similar to the template part of PasteScript):
It can make a copy of a project skeleton processing some files, filter others, etc.

It generates a beatiful output and take care of not overwrite existing files, unless instructed to do so.

.. figure:: docs/images/output.png
   :alt: Voodoo sample output

   Voodoo sample output as used in a program.


How to use
------------------------

The API is very simple. A ``render_skeleton`` function that takes two absolute paths: the project skeleton to process, and where to copy it.:

.. code:: python

    from voodoo import render_skeleton

    render_skeleton(skeleton_path, new_project_path)

It also has the ``prompt`` and ``prompt_bool`` functions that take user input, to help you to make interactive scripts.


How it works
------------------------

Files inside the skeleton are be copied to destination directly, unless are suffixed with the extension `'.tmpl'`. In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is that variables are referenced with ``[[ name ]]`` instead of ``{{ name }}`` and blocks are ``[% if name %]`` instead of ``{% if name %}``. To read more about templating see the `Jinja2 documentation <http://jinja.pocoo.org/docs>`_.


API
------------------------

``render_skeleton(src_path, dst_path, data=None, filter_ext=None, pretend=False, force=False, skip=False, quiet=False, envops=None)``

src_path:
    Absolute path to the project skeleton

dst_path:
    Absolute path to where to render the skeleton

data:
    Data to be passed to the templates, as context.

filter_this:
    A list of names or shell-style patterns matching files or folders
    that musn't be copied. The default is: ``['.*', '~*', '*.py[co]']``

include_this:
    A list of names or shell-style patterns matching files or folders that
    must be included, even if its name are in the `filter_this` list.
    Eg: ``['.gitignore']``. The default is an empty list.

pretend:
    Run but do not make any changes

force:
    Overwrite files that already exist, without asking

skip:
    Skip files that already exist, without asking

quiet:
    Suppress the status output

envops:
    Extra options for the Jinja template environment.

---------------------------------------------------------------

© 2011 by `Lúcuma labs <http://http://lucumalabs.com/>`_. See `AUTHORS.md` for more details.

License: `MIT License <http://www.opensource.org/licenses/mit-license.php>`_.


