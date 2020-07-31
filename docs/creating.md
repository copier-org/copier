# Creating a template

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

## The `copier.yml` file

If a `copier.yml`, or `copier.yaml` is found in the root of the template, it will be
read and used for two purposes:

- prompting the user for information
- configuring project generation (excluding files, setting arguments defaults, etc.)

### Prompt the user for information

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

#### Advanced prompt formatting

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

#### Prompt templating

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

### Special options

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

#### Patterns syntax

Copier supports matching names against patterns in a gitignore style fashion. This works
for the options `exclude` and `skip`. This means you can write patterns as you would for
any `.gitignore` file. The full range of the gitignore syntax ist supported via
[pathspec](https://github.com/cpburnz/python-path-specification).

##### Examples for pattern matching

Putting the following settings in your `copier.yaml` file would exclude all files ending
with "txt" from being copied to the destination folder, except the file `a.txt`.

```yaml
_exclude:
  # match all text files...
  - "*.txt"
  # .. but not this one:
  - "!a.txt"
```

### Include other yaml files

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

**Warning**: You can't have in the same file a top `!include` tag and classic YAML
syntax, see
[this pyyaml-include issue](https://github.com/tanbro/pyyaml-include/issues/7).

```yaml
# Invalid file
!include other_place/include_me.yml
foo: "bar"
```

## The `.copier-answers.yml` file

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

## Template helpers

In addition to
[all the features Jinja supports](https://jinja.palletsprojects.com/en/2.11.x/templates/),
Copier includes:

### Builtin variables/functions

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

### Builtin filters

- `anything|to_nice_yaml` to print as pretty-formatted YAML.

  Without arguments it defaults to:
  `anything|to_nice_yaml(indent=2, width=80, allow_unicode=True)`, but you can modify
  those.
