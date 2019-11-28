## Think this library is awesome? Vote with a 👍 to include it in the awesome-python list: https://github.com/vinta/awesome-python/pull/1350

![Copier](https://github.com/pykong/copier/raw/master/copier-logotype.png)

[![Coverage Status](https://coveralls.io/repos/github/pykong/copier/badge.svg?branch=master)](https://coveralls.io/github/pykong/copier?branch=master) [![Tests](https://travis-ci.org/pykong/copier.svg?branch=master)](https://travis-ci.org/pykong/copier/) [![](https://img.shields.io/pypi/pyversions/copier.svg)](https://pypi.python.org/pypi/copier)

A library for rendering projects templates.

- Works with **local** paths and **git URLs**.
- Your project can include any file and `Copier` can dynamically replace values in any kind of text files.
- It generates a beautiful output and takes care of not overwrite existing files unless instructed to do so.

![Sample output](https://github.com/pykong/copier/raw/master/copier-output.png)

## How to use

- Use it in your Python code:

```python
from copier import copy

# Create a project from a local path
copy("path/to/project/template", "path/to/destination")

# Or from a git URL.
copy("https://github.com/pykong/copier.git", "path/to/destination")

# You can also use "gh:" as a shortcut of "https://github.com/"
copy("gh:pykong/copier.git", "path/to/destination")

# Or "gl:" as a shortcut of "https://gitlab.com/"
copy("gl:pykong/copier.git", "path/to/destination")
```

- Or as a command-line tool:

```bash
copier path/to/project/template path/to/destination
```

## How it works

The content of the files inside the project template is copied to the destination
without changes, **unless are suffixed with the extension '.tmpl'.**
In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is
those variables are referenced with `[[ name ]]` instead of
`{{ name }}` and blocks are `[% if name %]` instead of
`{% if name %}`. To read more about templating see the [Jinja2
documentation](http://jinja.pocoo.org/docs>).

If a **YAML** file named `copier.yml` is found in the root of the
project (alternatively, a YAML file named `copier.yaml`), the user will be
prompted to fill in or confirm the default values.

Use the `data` argument to pass whatever extra context you want to be available
in the templates. The arguments can be any valid Python value, even a
function.

Since version 3.0, only Python 3.6 or later are supported. Please use the
2.5.1 version if your project runs on a previous Python version.

## The `copier.yml`ile

If a `copier.yml`, or `copier.yaml` file is found in the root of the template,
it will be read and used for two purposes:

### Prompt the user for information

For each key found, Copier will prompt the user to fill or confirm the values before
they become available to the project template. So content like this:

```yaml
name_of_the_project: My awesome project
number_of_eels: 1234
your_email: ""
```

will result in this series of questions:

```bash
name_of_the_project? [My awesome project]
your_email? [] myemail@gmail.com
number_of_eels? [1234] 42
```

**NOTE:** All values are required. If you want some value to be optional, do not use
an empty string as the default value or copier will not allow you to continue without
answering with a value. Use `null` instead, so you can press ENTER to accept the
"empty" default value.

```yaml
# DO NOT do this for optionals
bad_optional_value: ""

# DO THIS instead
good_optional_value: null
```

### Arguments defaults

The keys `_exclude`, `_include`, `_skip_if_exists`, `_tasks`, and `_extra_paths`
in the `copier.yml` file, will be treated as the default values for the `exclude`,
`include`, `tasks`, and , `extra_paths` arguments to `copier.copy()`.

Note that they become just _the defaults_, so any explicitly-passed argument will
overwrite them.

```yaml
# Shell-style patterns files/folders that must not be copied.
_exclude:
  - "*.bar"
  - ".git"
  - ".git/*"

# Shell-style patterns files/folders that *must be* copied, even if
# they are in the exclude list
_include:
  - "foo.bar"

# Shell-style patterns files to skip, without asking, if they already exists
# in the destination folder
_skip_if_exists:

# Commands to be executed after the copy
_tasks:
  - "git init"
  - "rm [[ name_of_the_project ]]/README.md"

# Additional paths, from where to search for templates
_extra_paths:
  - ~/Projects/templates
```

**Warning:** Use only trusted project templates as these tasks run with the
same level of access as your user.

## The `.copier-answers.yml` file

If the destination path exists and a `.copier-answers.yml` (or `.copier-answers.yaml`) file is
present there, it will be used to load last user's answers to the questions
made in [the `copier.yml` file](#the-copieryml-file).

This makes projects easier to update because when the user is asked, the default
answers will be the last ones he used.

To make sure projects based on your templates can make use of this nice feature,
add a file called `.copier-answers.yml.tmpl` in your template's root folder, with
this content:

```yml
# Changes here will be overwritten by Copier
[[ _log|to_nice_yaml ]]
```

The builtin `_log` variable includes all data needed to smooth future updates
of this project. This includes (but is not limited to) all JSON-serializable
values declared as user questions in [the `copier.yml` file](#the-copieryml-file).

As you can see, you also have the power to customize what will be logged here.
Keys that start with an underscore (`_`) are specific to Copier. Other keys
should match questions in `copier.yml`.

## Template helpers

In addition to [all the features Jinja supports](https://jinja.palletsprojects.com/en/2.10.x/templates/),
Copier includes:

### Builtin variables/functions

- `now()` to get current UTC time.
- `make_secret()` to get a random string.

### Builtin filters

- `anything|to_nice_yaml` to print as pretty-formatted YAML.

  Without arguments it defaults to:
  `anything|to_nice_yaml(indent=2, width=80, allow_unicode=True)`,
  but you can modify those.

---

## API

#### copier.copy()

```python
copier.copy(
    src_path,
    dst_path,

    data=DEFAULT_DATA,
    *,
    exclude=DEFAULT_FILTER,
    include=DEFAULT_INCLUDE,
    skip_if_exists=[],
    tasks=[],

    envops={},
    extra_paths=[],

    pretend=False,
    force=False,
    skip=False,
    quiet=False,
    cleanup_on_error=True
)
```

Uses the template in _src_path_ to generate a new project at _dst_path_.

**Arguments**:

- **src_path** (str):<br>
  Absolute path to the project skeleton. Can be a version control system URL.

- **dst_path** (str):<br>
  Absolute path to where to render the skeleton.

- **data** (dict):<br>
  Data to be passed to the templates in addition to the user data from
  a `copier.yml`.

- **exclude** (list):<br>
  A list of names or shell-style patterns matching files or folders
  that must not be copied.

  To exclude a folder you should use **two** entries, one for the folder and
  the other for its content: `[".git", ".git/*"]`.

- **include** (list):<br>
  A list of names or shell-style patterns matching files or folders that
  must be included, even if its name is a match for the `exclude` list.
  Eg: `['.gitignore']`. The default is an empty list.

- **skip_if_exists** (list):<br>
  Skip any of these files, without asking, if another with the same name already
  exists in the destination folder. (it only makes sense if you are copying to a
  folder that already exists).

- **tasks** (list):<br>
  Optional lists of commands to run in order after finishing the copy. Like in
  the templates files, you can use variables on the commands that will be
  replaced by the real values before running the command. If one of the commands
  fails, the rest of them will not run.

- **envops** (dict):<br>
  Extra options for the Jinja template environment.

- **extra_paths** (list):<br>
  Additional paths, from where to search for templates. This is intended to be
  used with shared parent templates, files with macros, etc. outside the copied
  project skeleton.

- **pretend** (bool):<br>
  Run but do not make any changes.

- **force** (bool):<br>
  Overwrite files that already exist, without asking.

- **skip** (bool):<br>
  Skip files that already exist, without asking.

- **quiet** (bool):<br>
  Suppress the status output.

- **cleanup_on_error** (bool):<br>
  Remove the destination folder if the copy process or one of the tasks fail.
  True by default.
