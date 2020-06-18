## Think this library is awesome? Vote with a 👍 to include it in the awesome-python list: https://github.com/vinta/awesome-python/pull/1350

# ![Copier](https://github.com/pykong/copier/raw/master/img/copier-logotype.png)

[![codecov](https://codecov.io/gh/pykong/copier/branch/master/graph/badge.svg)](https://codecov.io/gh/pykong/copier)
![](https://github.com/pykong/copier/workflows/CI/badge.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
![](https://img.shields.io/pypi/pyversions/copier)
![](https://img.shields.io/pypi/v/copier)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A library for rendering project templates.

- Works with **local** paths and **git URLs**.
- Your project can include any file and `Copier` can dynamically replace values in any
  kind of text file.
- It generates a beautiful output and takes care of not overwrite existing files unless
  instructed to do so.

![Sample output](https://github.com/pykong/copier/raw/master/img/copier-output.png)

<details>
<!-- prettier-ignore-start -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
<summary>Table of contents</summary>

- [Installation](#installation)
- [Quick usage](#quick-usage)
- [Creating a template](#creating-a-template)
  - [The `copier.yml` file](#the-copieryml-file)
    - [Prompt the user for information](#prompt-the-user-for-information)
      - [Advanced prompt formatting](#advanced-prompt-formatting)
      - [Prompt templating](#prompt-templating)
    - [Special options](#special-options)
      - [Patterns syntax](#patterns-syntax)
        - [Examples for pattern matching](#examples-for-pattern-matching)
    - [Include other yaml files](#include-other-yaml-files)
  - [The `.copier-answers.yml` file](#the-copier-answersyml-file)
  - [Template helpers](#template-helpers)
    - [Builtin variables/functions](#builtin-variablesfunctions)
    - [Builtin filters](#builtin-filters)
- [Generating a project](#generating-a-project)
- [Updating a project](#updating-a-project)
- [Browse or tag public templates](#browse-or-tag-public-templates)
- [API](#api)
  - [copier.copy()](#copiercopy)
- [Comparison with other project generators](#comparison-with-other-project-generators)
  - [Cookiecutter](#cookiecutter)
- [Credits](#credits)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- prettier-ignore-end -->
</details>

## Installation

1. Install Git 2.24 or newer.
1. To use as a CLI app: `pipx install copier`
1. To use as a library: `pip install copier`

## Quick usage

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

## Creating a template

A template is a directory: usually the root folder of a git repository.

The content of the files inside the project template is copied to the destination
without changes, **unless they end with `.tmpl`** (or your chosen `templates_suffix`).
In that case, the templating engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is those variables
are referenced with `[[ name ]]` instead of `{{ name }}` and blocks are `[% if name %]`
instead of `{% if name %}`. To read more about templating see the
[Jinja2 documentation](https://jinja.palletsprojects.com/).

If a **YAML** file named `copier.yml` is found in the root of the project
(alternatively, a YAML file named `copier.yaml`), the user will be prompted to fill in
or confirm the default values.

Since version 3.0, only Python 3.6 or later are supported. Please use the 2.5.1 version
if your project runs on a previous Python version.

### The `copier.yml` file

If a `copier.yml`, or `copier.yaml` is found in the root of the template, it will be
read and used for two purposes:

- prompting the user for information
- configuring project generation (excluding files, setting arguments defaults, etc.)

#### Prompt the user for information

For each key found, Copier will prompt the user to fill or confirm the values before
they become available to the project template. So content like this:

```yaml
name_of_the_project: My awesome project
number_of_eels: 1234
your_email: ""
```

will result in this series of questions:

<pre>
  <b>name_of_the_project</b>? Format: yaml
🎤 [My awesome project]:

  <b>number_of_eels</b>? Format: yaml
🎤 [1234]:

  <b>your_email</b>? Format: yaml
🎤 []:
</pre>

##### Advanced prompt formatting

Apart from the simplified format, as seen above, Copier supports a more advanced format
to ask users for data. To use it, the value must be a dict.

Supported keys:

- **type**: User input must match this type. Options are: bool, float, int, json, str,
  yaml.
- **help**: Additional text to help the user know what's this question for.
- **default**: Leave empty to force the user to answer. Provide a default to save him
  from typing it if it's quite common. When using **choices**, the default must be the
  choice _value_, not its _key_. If values are quite long, you can use
  [YAML anchors](https://confluence.atlassian.com/bitbucket/yaml-anchors-960154027.html).

```yaml
love_copier:
  type: bool # This makes Copier ask for y/n
  help: Do you love Copier?
  default: yes # Without a default, you force the user to answer

project_name:
  type: str # Any value will be treated raw as a string
  help: An awesome project needs an awesome name. Tell me yours.
  default: paradox-specifier

rocket_launch_password:
  type: str
  secret: true # This value will not be logged into .copier-answers.yml
  default: my top secret password

# I'll avoid default and help here, but you can use them too
age:
  type: int

height:
  type: float

any_json:
  help: Tell me anything, but format it as a one-line JSON string
  type: json

any_yaml:
  help: Tell me anything, but format it as a one-line YAML string
  type: yaml # This is the default type, also for short syntax questions

your_favorite_book:
  # User will type 1 or 2, but your template will get the value
  choices:
    - The Bible
    - The Hitchhiker's Guide to the Galaxy

project_license:
  # User will type 1 or 2 and will see only the dict key, but you will
  # get the dict value in your template
  choices:
    MIT: &mit_text |
      Here I can write the full text of the MIT license.
      This will be a long text, shortened here for example purposes.
    Apache2: |
      Full text of Apache2 license.
  # When using choices, the default value is the value, **not** the key;
  # that's why I'm using the YAML anchor declared above to avoid retyping the
  # whole license
  default: *mit_text
  # You can still define the type, to make sure answers that come from --data
  # CLI argument match the type that your template expects
  type: str

close_to_work:
  help: Do you live close to your work?
  # This format works just like the dict one
  choices:
    - [at home, I work at home]
    - [less than 10km, quite close]
    - [more than 10km, not so close]
    - [more than 100km, quite far away]
```

##### Prompt templating

Values of prompted keys can use Jinja templates.

Keep in mind that the configuration is loaded as **YAML**, so the contents must be
**valid YAML** and respect **Copier's structure**. That is why we explicitly wrap some
strings in double-quotes in the following examples.

Answers provided through interactive prompting will not be rendered with Jinja, so you
cannot use Jinja templating in your answers.

```yaml
# default
username:
  type: str

organization:
  type: str

email:
  type: str
  default: "[[ username ]]@[[ organization ]].com"

# help
copyright_holder:
  type: str
  help: The person or entity within [[ organization ]] that holds copyrights.

# type
target:
  type: str
  choices:
    - humans
    - machines

user_config:
  type: "[% if target == 'humans' %]yaml[% else %]json[% endif %]"

# choices
title:
  type: str
  help: Your title within [[ organization ]]

contact:
  choices:
    Copyright holder: "[[ copyright_holder ]]"
    CEO: Alice Bob
    CTO: Carl Dave
    "[[ title ]]": "[[ username ]]"
```

#### Special options

Copier will also read special configuration options from the `copier.yml` file. They all
start with an underscore.

```yaml
# Specify the minimum required version of Copier to generate a project from this template.
# The version must be follow the PEP 440 syntax.
# Upon generating or updating a project, if the installed version of Copier is less than the required one,
# the generation will be aborted and an error will be shown to the user.
_min_copier_version: "4.1.0"

# File where answers will be recorded. Defaults to `.copier-answers.yml`.
# Remember to add that file to your template if you want to support updates.
_answers_file: .my-custom-answers.yml

# Suffix that instructs which files are to be processed by Jinja as templates
_templates_suffix: .tmpl

# gitignore-style patterns files/folders that must not be copied.
# Can be overridden with the `exclude` CLI/API option.
_exclude:
  - "*.bar"
  - ".git"

# gitignore-style patterns files to skip, without asking, if they already exists
# in the destination folder
# Can be overridden with the `skip_if_exist` API option.
_skip_if_exists:

# Subdirectory to use as the template root when generating a project.
# If not specified, the root of the git repository is used.
# Can be overridden with the `subdirectory` CLI/API option.
_subdirectory: "project"

# Commands to execute after generating or updating a project from your template.
# They run ordered, and with the $STAGE=task variable in their environment.
# Can be overridden with the `tasks` API option.
_tasks:
  # Strings get executed under system's default shell
  - "git init"
  - "rm [[ name_of_the_project / 'README.md' ]]"
  # Arrays are executed without shell, saving you the work of escaping arguments
  - [invoke, "--search-root=[[ _copier_conf.src_path ]]", after-copy]
  # You are able to output the full conf to JSON, to be parsed by your script,
  # but you cannot use the normal `|tojson` filter; instead, use `.json()`
  - [invoke, end-process, "--full-conf=[[ _copier_conf.json() ]]"]

# Migrations are like tasks, but they are executed:
# - Evaluated using PEP 440
# - In the same order as declared here (so you could even run a migration for a higher
#   version before running a migration for a lower version if the higher one is declared
#   before and the update passes through both)
# - Only when new version >= declared version > old version
# - Only when updating
# - After being rendered with Jinja, with the same context as the rest of the template
# - With $VERSION_FROM, $VERSION_TO, $VERSION_CURRENT and $STAGE (before/after)
#   environment variables
# - The answers file is reloaded after running migrations in the "before" stage.
_migrations:
  - version: v1.0.0
    before:
      - rm ./old-folder
    after:
      # [[ _copier_conf.src_path ]] points to the path where the template was
      # cloned, so it can be helpful to run migration scripts stored there.
      - invoke -r [[ _copier_conf.src_path ]] -c migrations migrate $VERSION_CURRENT

# Additional paths, from where to search for templates
# Can be overridden with the `extra_paths` API option.
_extra_paths:
  - ~/Projects/templates
```

##### Patterns syntax

Copier supports matching names against patterns in a gitignore style fashion. This works
for the options `exclude` and `skip`. This means you can write patterns as you would for
any `.gitignore` file. The full range of the gitignore syntax ist supported via
[pathspec](https://github.com/cpburnz/python-path-specification).

###### Examples for pattern matching

Putting the following settings in your `copier.yaml` file would exclude all files ending
with "txt" from being copied to the destination folder, except the file `a.txt`.

```yaml
_exclude:
  # match all text files...
  - "*.txt"
  # .. but not this one:
  - "!a.txt"
```

#### Include other yaml files

To reuse configurations across templates you can reference other yaml files. You just
need to state the `!include` together with the absolute or relative path to the file to
be included. Multiple files can be included per `copier.yml`. For more detailed
instructions, see [pyyaml-include](https://github.com/tanbro/pyyaml-include#usage).

```yaml
# other_place/include_me.yml
common_setting: "1"

# copier.yml
!include other_place/include_me.yml
```

### The `.copier-answers.yml` file

If the destination path exists and a `.copier-answers.yml` file is present there, it
will be used to load the last user's answers to the questions made in
[the `copier.yml` file](#the-copieryml-file).

This makes projects easier to update because when the user is asked, the default answers
will be the last ones he used.

To make sure projects based on your templates can make use of this nice feature, **add a
file called `[[ _copier_conf.answers_file ]].tmpl`** (or your chosen `templates_suffix`)
in your template's root folder, with this content:

```yml
# Changes here will be overwritten by Copier
[[_copier_answers|to_nice_yaml]]
```

If this file is called different than `[[ _copier_conf.answers_file ]].tmpl` your users
will not be able to choose a custom answers file name, and thus they will not be able to
integrate several updatable templates into one destination directory.

The builtin `_copier_answers` variable includes all data needed to smooth future updates
of this project. This includes (but is not limited to) all JSON-serializable values
declared as user questions in [the `copier.yml` file](#the-copieryml-file).

As you can see, you also have the power to customize what will be logged here. Keys that
start with an underscore (`_`) are specific to Copier. Other keys should match questions
in `copier.yml`.

If you plan to integrate several templates into one single downstream project, you can
use a different path for this file:

```yaml
# In your `copier.yml`:
_answers_file: .my-custom-answers.yml
```

### Template helpers

In addition to
[all the features Jinja supports](https://jinja.palletsprojects.com/en/2.11.x/templates/),
Copier includes:

#### Builtin variables/functions

- `now()` to get current UTC time.
- `make_secret()` to get a random string.
- `_copier_answers` includes the current answers dict, but slightly modified to make it
  suitable to [autoupdate your project safely](#the-answers-file):
  - It doesn't contain secret answers.
  - It doesn't contain any data that is not easy to render to JSON or YAML.
  - It contains special keys like `_commit` and `_src_path`, indicating how the last
    template update was done.
- `_copier_conf` includes the current copier `ConfigData` object, also slightly
  modified:
  - It only contains JSON-serializable data.
  - But you have to serialize it with `[[ _copier_conf.json() ]]` instead of
    `[[ _copier_conf|tojson ]]`.
  - ⚠️ It contains secret answers inside its `.data` key.
  - Modifying it doesn't alter the current rendering configuration.

#### Builtin filters

- `anything|to_nice_yaml` to print as pretty-formatted YAML.

  Without arguments it defaults to:
  `anything|to_nice_yaml(indent=2, width=80, allow_unicode=True)`, but you can modify
  those.

## Generating a project

**Warning:** Generate projects only from trusted templates as their tasks run with the
same level of access as your user.

As seen in the quick usage section, you can generate a project from a template using the
`copier` command-line tool:

```bash
copier path/to/project/template path/to/destination
```

Or within Python code:

```python
copier.copy("path/to/project/template", "path/to/destination")
```

The "template" parameter can be a local path, an URL, or a shortcut URL:

- GitHub: `gh:namespace/project`
- GitLab: `gl:namespace/project`

Use the `--data` command-line argument or the `data` parameter of the `copier.copy()`
function to pass whatever extra context you want to be available in the templates. The
arguments can be any valid Python value, even a function.

Use the `--vcs-ref` command-line argument to checkout a particular git ref before
generating the project.

All the available options are described with the `--help-all` option.

## Updating a project

The best way to update a project from its template is when all of these conditions are
true:

1. The template includes a valid `.copier-answers.yml` file.
2. The template is versioned with git (with tags).
3. The destination folder is versioned with git.

If that's your case, then just enter the destination folder, make sure `git status`
shows it clean, and run:

```bash
copier update
```

This will read all available git tags, will compare them using
[PEP 440](https://www.python.org/dev/peps/pep-0440/), and will check out the latest one
before updating. To update to the latest commit, add `--vcs-ref=HEAD`. You can use any
other git ref you want.

When updating, Copier will do its best to respect your project evolution by using the
answers you provided when copied last time. However, sometimes it's impossible for
Copier to know what to do with a diff code hunk. In those cases, you will find `*.rej`
files that contain the unresolved diffs. _You should review those manually_ before
committing.

You probably don't want `*.rej` files in your git history, but if you add them to
`.gitignore`, some important changes could pass unnoticed to you. That's why the
recommended way to deal with them is to _not_ add them to add a
[pre-commit](https://pre-commit.com/) (or equivalent) hook that forbids them, just like
this:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: forbidden-files
        name: forbidden files
        entry: found copier update rejection files; review them and remove them
        language: fail
        files: "\\.rej$"
```

## Browse or tag public templates

You can browse public copier templates in GitHub using
[the `copier-template` topic](https://github.com/topics/copier-template). Use them as
inspiration!

If you want your template to appear in that list, just add the topic to it! 🏷

## API

### copier.copy()

```python
copier.copy(
    src_path,
    dst_path,

    data=DEFAULT_DATA,
    *,
    exclude=DEFAULT_FILTER,
    skip_if_exists=[],
    tasks=[],

    envops={},
    extra_paths=[],

    pretend=False,
    force=False,
    skip=False,
    quiet=False,
    cleanup_on_error=True,
    subdirectory=None,
)
```

Uses the template in _src_path_ to generate a new project at _dst_path_.

**Arguments**:

- **src_path** (str):<br> Absolute path to the project skeleton, which can also be a
  version control system URL.

- **dst_path** (str):<br> Absolute path to where to render the skeleton.

- **data** (dict):<br> Data to be passed to the templates in addition to the user data
  from a `copier.yml`.

- **exclude** (list):<br> A list of names or gitignore-style patterns matching files or
  folders that must not be copied.

- **skip_if_exists** (list):<br> A list of names or gitignore-style patterns matching
  files or folders, that are skipped if another with the same name already exists in the
  destination folder. (It only makes sense if you are copying to a folder that already
  exists).

- **tasks** (list):<br> Optional lists of commands to run in order after finishing the
  copy. Like in the templates files, you can use variables on the commands that will be
  replaced by the real values before running the command. If one of the commands fails,
  the rest of them will not run.

- **envops** (dict):<br> Extra options for the Jinja template environment. See available
  options in
  [Jinja's docs](https://jinja.palletsprojects.com/en/2.10.x/api/#jinja2.Environment).

  Copier uses these defaults that are different from Jinja's:

  ```yml
  # copier.yml
  _envops:
    block_start_string: "[%"
    block_end_string: "%]"
    comment_start_string: "[#"
    comment_end_string: "#]"
    variable_start_string: "[["
    variable_end_string: "]]"
    keep_trailing_newline: true
  ```

  You can use default Jinja syntax with:

  ```yml
  # copier.yml
  _envops:
    block_start_string: "{%"
    block_end_string: "%}"
    comment_start_string: "{#"
    comment_end_string: "#}"
    variable_start_string: "{{"
    variable_end_string: "}}"
    keep_trailing_newline: false
  ```

- **extra_paths** (list):<br> Additional paths, from where to search for templates. This
  is intended to be used with shared parent templates, files with macros, etc. outside
  the copied project skeleton.

- **pretend** (bool):<br> Run but do not make any changes.

- **force** (bool):<br> Overwrite files that already exist, without asking.

- **skip** (bool):<br> Skip files that already exist, without asking.

- **quiet** (bool):<br> Suppress the status output.

- **cleanup_on_error** (bool):<br> Remove the destination folder if the copy process or
  one of the tasks fails. True by default.

- **subdirectory** (str):<br> Path to a sub-folder to use as the root of the template
  when generating the project. If not specified, the root of the git repository is used.

## Comparison with other project generators

### Cookiecutter

Cookiecutter and Copier are quite similar in functionality, except that:

- Cookiecutter uses a subdirectory to generate the project, while Copier can use either
  the root directory (default) or a subdirectory.
- Cookiecutter uses default Jinja templating characters: `{{`, `{%`, etc., while Copier
  uses `[[`, `[%`, etc., and can be configured to change those.
- Cookiecutter puts context variables in a namespace: `{{ cookiecutter.name }}`, while
  Copier sets them directly: `[[ name ]]`.
- You configure your template in `copier.yml` instead of `cookiecutter.json`.
- Prompts are enhanced in Copier:
  - Type-casting and verifications
  - YAML native types + `json` and `yaml`
  - Descriptions (help message for prompts)
  - Conditional prompts (_soon_)
- Copier has very useful features that are missing in Cookiecutter (or require extra
  software), like the ability to **update a generated project** when the original
  template changes, and to run **migrations** when updating.

## Credits

Special thanks go to [jpscaletti](https://github.com/jpscaletti) for originally creating
`Copier`. This project would not be a thing without him.

Big thanks also go to [Yajo](https://github.com/Yajo) for his relentless zest for
improving `Copier` even further.

Thanks a lot, [pawamoy](https://github.com/pawamoy) for polishing very important rough
edges and improving the documentation and UX a lot.
