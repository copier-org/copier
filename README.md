# Copier · [![](https://img.shields.io/pypi/v/copier.svg)](https://pypi.python.org/pypi/copier) [![](https://img.shields.io/pypi/pyversions/copier.svg)](https://pypi.python.org/pypi/copier)

A library for rendering projects templates.

* Works with **local** paths and **git URLs**.
* Your project can include any file and `Copier` can dynamically replace values in any kind of text files.
* It generates a beautiful output and take care of not overwrite existing files, unless instructed to do so.

![Sample output](https://github.com/jpscaletti/copier/raw/master/copier-output.png)


## How to use

- Use it in your Python code:

```python
from copier import copy

# Create a project from a local path
copy('path/to/project/template', 'path/to/destination')

# Or from a git URL.
copy('https://github.com/jpscaletti/copier.git', 'path/to/destination')

# You can also use "gh:" as a shortcut of "https://github.com/"
copy('gh:jpscaletti/copier.git', 'path/to/destination')

# Or "gl:"  as a shortcut of "https://gitlab.com/"
copy('gl:jpscaletti/copier.git', 'path/to/destination')
```

- Or as a command-line tool:

```bash
copier path/to/project/template path/to/destination
```

## Prompt the user for information

If a YAML file named `copier.yaml` (alternatively, a `copier.json` ) is found in the root
of the project, it will be used to prompt the user to fill or confirm the values before
become avaliable to the project template.

```yaml
name_of_the_project: "My awesome project"
your_email: null
```


## How it works

The content of the files inside the project template are copied to the destination
without changes, **unless are suffixed with the extension '.tmpl'.**
In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is
that variables are referenced with ``[[ name ]]`` instead of
``{{ name }}`` and blocks are ``[% if name %]`` instead of
``{% if name %}``. To read more about templating see the [Jinja2
documentation](http://jinja.pocoo.org/docs>).

If a `copier.yaml` is found in the root of the project, the user will be prompted to
fill or confirm the values.

Use the `extra_data` argument to pass whatever extra context you want to be available
in the templates. The arguments can be any valid Python value, even a
function.


## API

#### copier.copy()

`copier.copy(src_path, dst_path, data=None, *,
    exclude=DEFAULT_FILTER, include=DEFAULT_INCLUDE, envops=None,
    pretend=False, force=False, skip=False, quiet=False,
)`

Uses the template in src_path to generate a new project at dst_path.

**Arguments**:

- **src_path** (str):
    Absolute path to the project skeleton. May be a version control system URL

- **dst_path** (str):
    Absolute path to where to render the skeleton

- **data** (dict):
    Optional. Data to be passed to the templates in addtion to the user data from
    a `copier.yaml`.

- **exclude** (list):
    Optional. A list of names or shell-style patterns matching files or folders
    that musn't be copied.

- **include** (list):
    Optional. A list of names or shell-style patterns matching files or folders that
    must be included, even if its name are in the `exclude` list.
    Eg: `['.gitignore']`. The default is an empty list.

- **envops** (dict):
    Optional. Extra options for the Jinja template environment.

- **pretend** (bool):
    Optional. Run but do not make any changes

- **force** (bool):
    Optional. Overwrite files that already exist, without asking

- **skip** (bool):
    Optional. Skip files that already exist, without asking

- **quiet** (bool):
    Optional. Suppress the status output
