# ![Copier](https://github.com/copier-org/copier/raw/master/img/copier-logotype.png)

[![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/copier-org/copier)
[![codecov](https://codecov.io/gh/copier-org/copier/branch/master/graph/badge.svg)](https://codecov.io/gh/copier-org/copier)
[![CI](https://github.com/copier-org/copier/workflows/CI/badge.svg)](https://github.com/copier-org/copier/actions?query=branch%3Amaster)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
![Python](https://img.shields.io/pypi/pyversions/copier?logo=python&logoColor=%23959DA5)
[![PyPI](https://img.shields.io/pypi/v/copier?logo=pypi&logoColor=%23959DA5)](https://pypi.org/project/copier/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation Status](https://img.shields.io/readthedocs/copier/latest?logo=readthedocs)](https://copier.readthedocs.io/en/latest)

A library and CLI app for rendering project templates.

-   Works with **local** paths and **Git URLs**.
-   Your project can include any file and Copier can dynamically replace values in any
    kind of text file.
-   It generates a beautiful output and takes care of not overwriting existing files
    unless instructed to do so.

![Sample output](https://github.com/copier-org/copier/raw/master/img/copier-output.png)

## Installation

1. Install Python 3.7 or newer (3.8 or newer if you're on Windows).
1. Install Git 2.27 or newer.
1. To use as a CLI app: `pipx install copier`
1. To use as a library: `pip install copier` or `conda install -c conda-forge copier`

## Quick start

To create a template:

```shell
📁 my_copier_template ------------------------ # your template project
├── 📄 copier.yml ---------------------------- # your template configuration
├── 📁 .git ---------------------------------- # your template is a Git repository
├── 📁 {{project_name}} ---------------------- # a folder with a templated name
│   └── 📄 {{module_name}}.py.jinja ---------- # a file with a templated name
└── 📄 {{_copier_conf.answers_file}}.jinja --- # answers are recorded here
```

```yaml title="copier.yml"
# questions
project_name:
    type: str
    help: What is your project name?

module_name:
    type: str
    help: What is your Python module name?
```

```python+jinja title="{{project_name}}/{{module_name}}.py.jinja"
print("Hello from {{module_name}}!")
```

```yaml+jinja title="{{_copier_conf.answers_file}}.jinja"
# Changes here will be overwritten by Copier
{{_copier_answers|to_nice_yaml}}
```

To generate a project from the template:

-   On the command-line:

    ```shell
    copier path/to/project/template path/to/destination
    ```

-   Or in Python code, programmatically:

    ```python
    from copier import run_auto

    # Create a project from a local path
    run_auto("path/to/project/template", "path/to/destination")

    # Or from a Git URL.
    run_auto("https://github.com/copier-org/copier.git", "path/to/destination")

    # You can also use "gh:" as a shortcut of "https://github.com/"
    run_auto("gh:copier-org/copier.git", "path/to/destination")

    # Or "gl:" as a shortcut of "https://gitlab.com/"
    run_auto("gl:copier-org/copier.git", "path/to/destination")
    ```

## Basic concepts

Copier is composed of these main concepts:

1. **Templates**. They lay out how to generate the subproject.
1. **Questionaries**. They are configured in the template. Answers are used to generate
   projects.
1. **Projects**. This is where your real program lives. But it is usually generated
   and/or updated from a template.

Copier targets these main human audiences:

1.  **Template creators**. Programmers that repeat code too much and prefer a tool to do
    it for them.

    !!! tip

         Copier doesn't replace the DRY principle... but sometimes you simply can't be
         DRY and you need a DRYing machine...

1.  **Template consumers**. Programmers that want to start a new project quickly, or
    that want to evolve it comfortably.

Non-humans should be happy also by using Copier's CLI or API, as long as their
expectations are the same as for those humans... and as long as they have feelings.

Templates have these goals:

1. **[Code scaffolding](<https://en.wikipedia.org/wiki/Scaffold_(programming)>)**. Help
   consumers have a working source code tree as quickly as possible. All templates allow
   scaffolding.
1. **Code lifecycle management**. When the template evolves, let consumers update their
   projects. Not all templates allow updating.

Copier tries to have a smooth learning curve that lets you create simple templates that
can evolve into complex ones as needed.

## Browse or tag public templates

You can browse public Copier templates on GitHub using
[the `copier-template` topic](https://github.com/topics/copier-template). Use them as
inspiration!

If you want your template to appear in that list, just add the topic to it! 🏷

## Credits

Special thanks go to [jpsca](https://github.com/jpsca) for originally creating `Copier`.
This project would not be a thing without him.

Many thanks to [pykong](https://github.com/pykong) who took over maintainership on the
project, promoted it, and laid out the bases of what the project is today.

Big thanks also go to [Yajo](https://github.com/Yajo) for his relentless zest for
improving `Copier` even further.

Thanks a lot, [pawamoy](https://github.com/pawamoy) for polishing very important rough
edges and improving the documentation and UX a lot.
