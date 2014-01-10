===============================
Voodoo
===============================

.. image:: https://badge.fury.io/py/Voodoo.png
    :target: http://badge.fury.io/py/Voodoo

.. image:: https://pypip.in/d/Voodoo/badge.png
    :target: https://crate.io/packages/Voodoo?version=latest

Voodoo is a template system for project skeletons (similar to the template part
of PasteScript):

* It can make a copy of a  project skeleton processing some files, filter others, etc.
* Works with **local** paths and **git/hg URLs**.
* It generates a beautiful output and take care of not overwrite existing files, unless instructed to do so.
* BSD License. See ``LICENSE`` for more details.


.. image:: https://raw.github.com/lucuma/Voodoo/master/docs/static/images/output.png
    :alt: Voodoo sample output as used in a program.

*Above, Voodoo sample output as used in a program*

**Requirements:**

* Pypy or Python 2.6, 2.7, 3.3 or newer.

* It also uses the Jinja2 and Colorama Python libraries.


As a command line tool
------------------------------------

Install it by doing::

    $  pip install voodoo

Then, whenever you want to clone a project template to make a new project, do::

    $  voodoo <Git URL or path to another folder> <New project name>

Example::

    $  voodoo git@github.com:lucuma/voodoo-flask.git myapp


Or in your programs
------------------------------

First of all install it and/or add it to your requirements.txt::

    $  pip install voodoo

The API is very simple. A ``render_skeleton`` function that takes two
absolute paths: the project skeleton to process, and where to copy it.:

.. code:: python

    from voodoo import render_skeleton

    render_skeleton(skeleton_path, new_project_path)

It also provide a ``prompt`` and ``prompt_bool`` functions that take
user input, to help you to make interactive scripts.

How it works
-------------

The content of the files inside the skeleton are copied to the destination
without changes, **unless are suffixed with the extension '.tmpl'.**
In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is
that variables are referenced with ``[[ name ]]`` instead of
``{{ name }}`` and blocks are ``[% if name %]`` instead of
``{% if name %}``. To read more about templating see the `Jinja2
documentation <http://jinja.pocoo.org/docs>`__.

Use the data argument to pass whatever context you want to be available
in the templates. The arguments can be any valid Python value, even a
function:

.. code:: python

    from hashlib import sha256
    from os import urandom
    from voodoo import render_skeleton

    data = {
        'package': 'demo',
        'py3': True,
        'make_secret': lambda: sha256(urandom(48)).hexdigest()
    }
    render_skeleton(skeleton_path, new_project_path, data=data)

so in your template you can have:

.. code:: jinja

    import [[ package ]]

    secret = '[[ make_secret() ]]'
    [% if py3 %]
    msg = 'Python 3!'
    [% else %]
    msg = 'meh'
    [% endif %]

Your folders and files can also use the ``[[ name ]]`` notation: ``mytemplate/[[ foo ]]/something/[[ bar ]].txt``


Using it in a script
--------------------

It's easy to integrate Voodoo with your own scripts. The following
example it's a classic make new project script found in many popular
frameworks:

.. code:: python

    from os.path import join, dirname, basename
    from voodoo import render_skeleton


    default_context = {
        'foo': 'bar',
    }
    SKELETON_PATH = join(dirname(__file__), '..', 'tests', 'demo')


    def new_project(path, options):
           data = default_context.copy()
        data['project_name'] = basename(path)
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

You can se this example working in the examples folder. Play with it,
generate a new project and manually update some files. Then run the
script again to see how it detects what files has changed, and what
files are identical and with no need of regeneration.

An interactive version of this script could be made using the
``voodoo.prompt`` and/or the ``voodoo.prompt_bool`` helper functions.

VCS Support
------------

Voodoo supports rendering project skeletons from a version control
system repository. Git and Mercurial are supported. It requires a
working VCS command on your path: git or hg.

The forms of the URL is the same that the ``pip`` installer uses,
detecting the type of VCS using URL prefixes: "git+" or "hg+".

Git
~~~

Currently supports cloning over ``git``, ``git+https`` and ``git+ssh``::

    git+git://git.myproject.org/MyProject
    git+https://git.myproject.org/MyProject
    git+ssh://git.myproject.org/MyProject
    git+git@git.myproject.org:MyProject

Passing branch names, a commit hash or a tag name is possible like so::

    git://git.myproject.org/MyProject.git@master
    git://git.myproject.org/MyProject.git@v1.0
    git://git.myproject.org/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709

Mercurial
~~~~~~~~~

The supported schemes are: ``hg+http``, ``hg+https``, ``hg+static-http``
and ``hg+ssh``::

    hg+http://hg.myproject.org/MyProject
    hg+https://hg.myproject.org/MyProject
    hg+ssh://hg.myproject.org/MyProject

You can also specify a revision number, a revision hash, a tag name or a
local branch name like so::

    hg+http://hg.myproject.org/MyProject@da39a3ee5e6b
    hg+http://hg.myproject.org/MyProject@2019
    hg+http://hg.myproject.org/MyProject@v1.0
    hg+http://hg.myproject.org/MyProject@special_feature

API
---

render_skeleton
~~~~~~~~~~~~~~~~

``render_skeleton (src_path, dst_path, data=None, filter_ext=None, pretend=False, force=False, skip=False, quiet=False, envops=None)``

src_path:
    Absolute path to the project skeleton

dst_path:
    Absolute path to where to render the skeleton

data:
    Data to be passed to the templates, as context.

filter_this:
    A list of names or shell-style patterns matching files or folders that musn't be copied. The default is: ``['.*', '~*', '*.py[co]']``

include_this:
    A list of names or shell-style patterns matching files or folders that must be included, even if its name are in the filter_this list. Eg: ``['.gitignore']``. The default is an empty list.

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

prompt
~~~~~~

``prompt (text, default=None)``

Ask a question via raw_input() and return their answer.

text:
    prompt text

default:
    default value if no answer is provided.

prompt_bool
~~~~~~~~~~~~

``prompt_bool (text, default=False, yes_choices=None, no_choices=None)``

Ask a yes/no question via raw_input() and return their answer.

text:
    prompt text

default:
    default value if no answer is provided.

yes_choices:
    default ``['y', 'yes', '1', 'on', 'true', 't']``

no_choices:
    default ``['n', 'no', '0', 'off', 'false', 'f']``