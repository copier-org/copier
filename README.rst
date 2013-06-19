============
Voodoo
============

Voodoo is a template system for project skeletons (similar to the template part of PasteScript):
It can make a copy of a project skeleton processing some files, filter others, etc.

It generates a beatiful output and take care of not overwrite existing files, unless instructed to do so.

.. image:: docs/images/output.png


How to use
------------

The interface is very simple. A `reanimate_skeleton` function that takes two absolute paths: the project skeleton to process, and where to copy it.:

    from voodoo import reanimate_skeleton

    reanimate_skeleton(skeleton_path, new_project_path)

It also has the `prompt` and `prompt_bool` functions that take user input, to help you to make interactive scripts.


How it works
------------

Files inside the skeleton are be copied to destination directly, unless are suffixed with the extension `.tmpl`. In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is that variables are referenced with [[ name ]] instead of {{ name }} and blocks are [% if name %] instead of {% if name %}. To read more about templating see the `Jinja2 documentation <http://jinja.pocoo.org/docs>`_.


API
-----

`render_skeleton(src_path, dst_path, data=None, filter_ext=None, env_options=None, **options)`

src_path:
    Absolute path to the project skeleton

dst_path:
    Absolute path to where to render the skeleton

data:
    Data to be passed to the templates, as context.

filter_ext:
    Don't copy files with extensions in this list

env_options:
    Extra options for the jinja template environment.

options:
    General options:

    * 'pretend':  Run but do not make any changes
    * 'force':  Overwrite files that already exist
    * 'skip':  Skip files that already exist
    * 'quiet':  Suppress any print output


---------------------------------------

© 2011 by [Lúcuma labs] (http://lucumalabs.com).

License: [MIT License] (http://www.opensource.org/licenses/mit-license.php).


