# Configuring a template

## Configuration sources

It is important that you understand how Copier works. It has 2 kinds of configurations:

1. **Settings** for Copier itself. This includes things as minimal copier version
   required, which subdirectory to render, tasks to run, etc.
1. **Answers**. This is customized per template. The user answers template questions,
   and those answers are stored as variables available for the template at rendering
   time.

Copier reads **settings** from these sources, in this order of priority:

1. Command line or API arguments.
1. [The `copier.yml` file](#the-copieryml-file). Settings here always start with an
   underscore (e.g. `_min_copier_version`).

Copier obtains **answers** from these sources, in this order of priority:

1. Command line or API arguments.
1. Asking the user. Notice that Copier will not ask any questions answered in the
   previous source.
1. The last answers file.
1. [The `copier.yml` file](#the-copieryml-file), where default values are defined.

## The `copier.yml` file

The `copier.yml` (or `copier.yaml`) file is found in the root of the template, and it is
the main entrypoint for managing your template configuration. It will be read and used
for two purposes:

-   [Prompting the user for information](#questions).
-   [Applying template settings](#available-settings) (excluding files, setting
    arguments defaults, etc.).

### Questions

For each key found, Copier will prompt the user to fill or confirm the values before
they become available to the project template. For example, this:

```yaml
name_of_the_project: My awesome project
number_of_eels: 1234
your_email: ""
```

Will result in these questions:

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

-   **type**: User input must match this type. Options are: `bool`, `float`, `int`,
    `json`, `str`, `yaml` (default).
-   **help**: Additional text to help the user know what's this question for.
-   **choices**: To restrict possible values.
-   **default**: Leave empty to force the user to answer. Provide a default to save him
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
    # Notice that both `username` and `organization` have been already asked
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

### Include other YAML files

The `copier.yml` file supports multiple documents. When found, they are merged (**not**
deeply merged; just merged) and the latest one defined has priority.

It also supports using the `!include` tag to include other configurations from
elsewhere.

These two features, combined, allow you to reuse common partial sections from your
templates.

!!! hint

    You can use [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
    to sanely include shared code into templates.

!!! example

    This would be a valid `copier.yml` file:

    ```yaml
    ---
    # Copier will load all these files
    !include shared-conf/common.*.yml

    # These 3 lines split the several YAML documents
    ---
    # These two documents include common questions for these kind of projects
    !include common-questions/web_app.yml
    ---
    !include common-questions/python-project.yml
    ---

    # Here you can specify any settings or questions specific for your template,
    _skip_if_exists:
        - .password.txt
    custom_question: default answer
    ```

## Available settings

Template settings alter how the template is rendered.
[They come from several sources](#configuration-sources).

Remember that **the key must be prefixed with an underscore if you use it in
[the `copier.yml` file](#the-copieryml-file)**.

### `answers_file`

-   Format: `str`
-   CLI flags: `-a`, `--answers-file`
-   Default value: `.copier-answers.yml`

File where answers will be recorded by default. Remember to add that file to your Git
template if you want to support updates.

Don't forget to read [the docs about the answers file](#the-copier-answersyml-file).

Example `copier.yml`:

```yaml
_answers_file: .my-custom-answers.yml
```

### `data`

-   Format: `dict|List[str=str]`
-   CLI flags: `-d`, `--data`
-   Default value: N/A

Give answers to questions through CLI/API.

This cannot be defined in `copier.yml`, where its equivalent would be just normal
questions with default answers.

Example CLI usage to take all default answers from template, except the user name, which
is overriden, and don't ask user anything else:

```sh
copier -fd 'user_name=Manuel Calavera' copy template destination
```

### `exclude`

-   Format: `List[str]`
-   CLI flags: `-x`, `--exclude`
-   Default value:
    `["copier.yaml", "copier.yml", "~*", "*.py[co]", "__pycache__", ".git", ".DS_Store", ".svn"]`

[Patterns](#patterns-syntax) for files/folders that must not be copied.

The CLI option can be passed several times to add several patterns.

Example `copier.yml`:

```yaml
_exclude:
    - "*.bar"
    - ".git"
```

Example CLI usage to copy only a single file from the template:

```sh
copier --exclude '*' --exclude '!file-i-want' copy template destination
```

### `extra_paths`

-   Format: `List[str]`
-   CLI flags: `-p`, `--extra-paths`
-   Default value: N/A

Additional paths from where to search for templates.

Example `copier.yml`:

```yaml
_extra_paths:
    - ~/Projects/templates
```

### `force`

-   Format: `bool`
-   CLI flags: `-q`, `--force`
-   Default value: `False`

Overwrite files that already exist, without asking.

Also don't ask questions to the user; just use default values
[obtained from other sources](#configuration-sources).

!!! info

    It makes no sense to define this in `copier.yml`.

### `migrations`

-   Format: `List[dict]`
-   CLI flags: N/A
-   Default value: N/A

Migrations are like [tasks](#tasks), but each item in the list is a `dict` with these
keys:

-   **version**: Indicates the version that the template update has to go through to
    trigger this migration. It is evaluated using
    [PEP 440](https://www.python.org/dev/peps/pep-0440/).
-   **before** (optional): Commands to execute before performing the update. The answers
    file is reloaded after running migrations in this stage, to let you migrate answer
    values.
-   **after** (optional): Commands to execute after performing the update.

Migrations will run in the same order as declared here (so you could even run a
migration for a higher version before running a migration for a lower version if the
higher one is declared before and the update passes through both).

They will only run when new version >= declared version > old version. And only when
updating (not when copying for the 1st time).

If the migrations definition contains Jinja code, it will be rendered with the same
context as the rest of the template.

Migration processes will contain the `$VERSION_FROM`, `$VERSION_TO`, `$VERSION_CURRENT`
and `$STAGE` (before/after) environment variables

Example `copier.yml`:

```yaml
_migrations:
    - version: v1.0.0
      before:
          - rm ./old-folder
      after:
          # [[ _copier_conf.src_path ]] points to the path where the template was
          # cloned, so it can be helpful to run migration scripts stored there.
          - invoke -r [[ _copier_conf.src_path ]] -c migrations migrate $VERSION_CURRENT
```

### `min_copier_version`

-   Format: `str`
-   CLI flags: N/A
-   Default value: N/A

Specifies the minimum required version of Copier to generate a project from this
template. The version must be follow the
[PEP 440](https://www.python.org/dev/peps/pep-0440/) syntax. Upon generating or updating
a project, if the installed version of Copier is less than the required one, the
generation will be aborted and an error will be shown to the user.

Example `copier.yml`:

```yaml
_min_copier_version: "4.1.0"
```

### `only_diff`

-   Format: `bool`
-   CLI flags: `-D`, `--no-diff` (used to disable this setting; only available in
    `copier update` subcommand)
-   Default value: `True`

When doing an update, by default Copier will do its best to understand how the template
has evolved since the last time you updated it, and will try to apply only that diff to
your subproject, respecting the subproject's own evolution as much as possible.

Update with `only_diff=False` to avoid this behavior and let Copier override any changes
in the subproject.

It makes no sense to define this in `copier.yml`.

### `pretend`

-   Format: `bool`
-   CLI flags: `-q`, `--pretend`
-   Default value: `False`

Run but do not make any changes.

!!! info

    It makes no sense to define this in `copier.yml`.

### `quiet`

-   Format: `bool`
-   CLI flags: `-q`, `--quiet`
-   Default value: `False`

Suppress status output.

!!! info

    It makes no sense to define this in `copier.yml`.

### `skip_if_exists`

-   Format: `List[str]`
-   CLI flags: `-s`, `--skip`
-   Default value: N/A

[Patterns](#patterns-syntax) for files/folders that must be skipped if they already
exist.

For example, it can be used if your project generates a password the 1st time and you
don't want to override it next times:

```yaml
# copier.yml
_skip_if_exists: .secret_password.yml
```

```yaml
# .secret_password.yml.tmpl
[[make_secret()|tojson]]
```

### `subdirectory`

-   Format: `str`
-   CLI flags: `-b`, `--subdirectory`
-   Default value: N/A

Subdirectory to use as the template root when generating a project. If not specified,
the root of the template is used.

Example `copier.yml`:

```yaml
_subdirectory: src
```

Example CLI usage to choose a different subdirectory template:

```sh
copier --subdirectory template2 -b copy template destination
```

### `tasks`

-   Format: `List[str|List[str]]`
-   CLI flags: N/A
-   Default value: N/A

Commands to execute after generating or updating a project from your template.

They run ordered, and with the `$STAGE=task` variable in their environment.

Can be overridden with the `tasks` API option, but not from CLI.

Example `copier.yml`:

```yaml
_tasks:
    # Strings get executed under system's default shell
    - "git init"
    - "rm [[ name_of_the_project ]]/README.md"
    # Arrays are executed without shell, saving you the work of escaping arguments
    - [invoke, "--search-root=[[ _copier_conf.src_path ]]", after-copy]
    # You are able to output the full conf to JSON, to be parsed by your script,
    # but you cannot use the normal `|tojson` filter; instead, use `.json()`
    - [invoke, end-process, "--full-conf=[[ _copier_conf.json() ]]"]
```

### `templates_suffix`

-   Format: `str`
-   CLI flags: N/A
-   Default value: `.tmpl`

Suffix that instructs which files are to be processed by Jinja as templates.

Example `copier.yml`:

```yaml
_templates_suffix: .jinja
```

### `use_prereleases`

-   Format: `bool`
-   CLI flags: `g`, `--prereleases`
-   Default value: `False`

Imagine that the template supports updates and contains these 2 git tags: `v1.0.0` and
`v2.0.0a1`. Copier will copy by default `v1.0.0` unless you add `--prereleases`.

<!-- prettier-ignore-start -->
Also, if you run [`copier update`][copier.cli.CopierUpdateSubApp], Copier would ignore
the `v2.0.0a1` tag unless this flag is enabled.
<!-- prettier-ignore-end -->

!!! warning

    This behavior is new from Copier 5.0.0. Before that release, prereleases were
    never ignored.

!!! info

    It makes no sense to define this in `copier.yml`.

### `vcs_ref`

-   Format: `str`
-   CLI flags: `-r`, `-vcs-ref`
-   Default value: N/A (use latest release)

When copying or updating from a git-versioned template, indicate which template version
to copy.

This is stored automatically in the answers file, like this:

```yaml
_vcs_ref: v1.0.0
```

!!! info

    It makes no sense to define this in `copier.yml`.

By default, copier will copy from the last release found in template git tags, sorted as
[PEP 440](https://www.python.org/dev/peps/pep-0440/).

## Patterns syntax

Copier supports matching names against patterns in a gitignore style fashion. This works
for the options `exclude` and `skip`. This means you can write patterns as you would for
any `.gitignore` file. The full range of the gitignore syntax ist supported via
[pathspec](https://github.com/cpburnz/python-path-specification).

For example, with the following settings in your `copier.yml` file would exclude all
files ending with `txt` from being copied to the destination folder, except the file
`a.txt`.

```yaml
_exclude:
    # match all text files...
    - "*.txt"
    # .. but not this one:
    - "!a.txt"
```

## The `.copier-answers.yml` file

If the destination path exists and a `.copier-answers.yml` file is present there, it
will be used to load the last user's answers to the questions made in
[the `copier.yml` file](#the-copieryml-file).

This makes projects easier to update because when the user is asked, the default answers
will be the last ones he used.

To make sure projects based on your templates can make use of this nice feature, **add a
file called `[[ _copier_conf.answers_file ]].tmpl`** (or
[your chosen suffix](#templates_suffix)) in your template's root folder, with this
content:

```yaml
# Changes here will be overwritten by Copier
[[_copier_answers|to_nice_yaml]]
```

**Warning**: If this file is not called exactly `[[ _copier_conf.answers_file ]].tmpl`
your users will not be able to choose a custom answers file name, and thus they will not
be able to integrate several updatable templates into one destination directory.

The builtin `_copier_answers` variable includes all data needed to smooth future updates
of this project. This includes (but is not limited to) all JSON-serializable values
declared as user questions in [the `copier.yml` file](#the-copieryml-file).

As you can see, you also have the power to customize what will be logged here. Keys that
start with an underscore (`_`) are specific to Copier. Other keys should match questions
in `copier.yml`.

If you plan to integrate several templates into one single downstream project,
[you can define a different default path for this file](#answers_file).
