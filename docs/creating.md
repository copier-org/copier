# Creating a template

A template is a directory: usually the root folder of a Git repository.

The content of the files inside the project template is copied to the destination
without changes, **unless they end with `.jinja`** (or [your chosen
suffix][templates_suffix]). In that case, the templating engine will be used to render
them.

Jinja2 templating is used. Learn more about it by reading
[Jinja2 documentation](https://jinja.palletsprojects.com/).

If a **YAML** file named `copier.yml` or `copier.yaml` is found in the root of the
project, the user will be prompted to fill in or confirm the default values.

## Minimal example

```tree result="shell"
my_copier_template                            # your template project
    copier.yml                                # your template configuration
    .git/                                     # your template is a Git repository
    {{project_name}}                          # a folder with a templated name
        {{module_name}}.py.jinja              # a file with a templated name
    {{_copier_conf.answers_file}}.jinja       # answers are recorded here
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
{{ _copier_answers|to_nice_yaml -}}
```

Generating a project from this template with `super_project` and `world` as answers for
the `project_name` and `module_name` questions respectively would create in the
following directory and files:

```tree result="shell"
generated_project
    super_project
        world.py
    .copier-answers.yml
```

```python title="super_project/world.py"
print("Hello from world!")
```

```yaml title=".copier-answers.yml"
# Changes here will be overwritten by Copier
_commit: 0.1.0
_src_path: gh:your_account/your_template
project_name: super_project
module_name: world
```

Copier allows much more advanced templating: see the next chapter,
[configuring a template](configuring.md), to see all the configurations options and
their usage.

## Template helpers

In addition to
[all the features Jinja supports](https://jinja.palletsprojects.com/en/3.1.x/templates/),
Copier provides all functions and filters from
[jinja2-ansible-filters](https://gitlab.com/dreamer-labs/libraries/jinja2-ansible-filters/).
This includes the `to_nice_yaml` filter, which is used extensively in our context.

## Variables (global)

The following variables are always available in Jinja templates:

### `_copier_answers`

`_copier_answers` includes the current answers dict, but slightly modified to make it
suitable to [autoupdate your project safely][the-copier-answersyml-file]:

-   It doesn't contain secret answers.
-   It doesn't contain any data that is not easy to render to JSON or YAML.
-   It contains special keys like `_commit` and `_src_path`, indicating how the last
    template update was done.

### `_copier_conf`

!!! note

    - `_copier_conf` contains JSON-serializable data.
    - `_copier_conf` can be serialized with `#!jinja {{ _copier_conf|to_json }}`.
    - ⚠️ `_copier_conf` may contain secret answers inside its `.data` key.
    - Modifying `_copier_conf` doesn't alter the current rendering configuration.

Attributes:

| Name               | Type                                                          | Description                                                                                                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `answers_file`     | `PurePath`                                                    | The path for [the answers file][the-copier-answersyml-file] relative to `dst_path`.<br>See the [`answers_file`][] setting for related information.                                                                                                         |
| `cleanup_on_error` | `bool`                                                        | When `True`, delete `dst_path` if there's an error.<br>See the [`cleanup_on_error`][] setting for related information.                                                                                                                                     |
| `conflict`         | `Literal["inline", "rej"]`                                    | The output format of a diff code hunk when [updating][updating-a-project] a file yields conflicts.<br>See the [`conflict`][] setting for related information.                                                                                              |
| `context_lines`    | `PositiveInt`                                                 | Lines of context to consider when solving conflicts in updates.<br>See the [`context_lines`][] setting for related information.                                                                                                                            |
| `data`             | `dict[str, Any]`                                              | Answers to the questionnaire, defined in the template, provided via CLI (`-d,--data`) or API (`data`).<br>See the [`data`][] setting for related information.<br>⚠️ May contain secret answers.                                                            |
| `defaults`         | `bool`                                                        | When `True`, use default answers to questions.<br>See the [`defaults`][] setting for related information.                                                                                                                                                  |
| `dst_path`         | `PurePath`                                                    | Destination path where to render the subproject.<br>⚠️ When [updating a project][updating-a-project], it may be a temporary directory, as Copier's update algorithm generates fresh copies using the old and new template versions in temporary locations. |
| `exclude`          | `Sequence[str]`                                               | Specified additional [file exclusion patterns][patterns-syntax].<br>See the [`exclude`][] setting for related information.                                                                                                                                 |
| `os`               | <code>Literal["linux", "macos", "windows"] &vert; None</code> | The detected operating system, `None` if it could not be detected.                                                                                                                                                                                         |
| `overwrite`        | `bool`                                                        | When `True`, overwrite files that already exist, without asking.<br>See the [`overwrite`][] setting for related information.                                                                                                                               |
| `pretend`          | `bool`                                                        | When `True`, produce no real rendering.<br>See the [`pretend`][] setting for related information.                                                                                                                                                          |
| `quiet`            | `bool`                                                        | When `True`, disable all output.<br>See the [`quiet`][] setting for related information.                                                                                                                                                                   |
| `sep`              | `str`                                                         | The operating system-specific directory separator.                                                                                                                                                                                                         |
| `settings`         | [`copier.settings.Settings`][]                                | General user settings.<br>See the [`settings`][] page for related information.                                                                                                                                                                             |
| `skip_answered`    | `bool`                                                        | When `True`, skip questions that have already been answered.<br>See the [`skip_answered`][] setting for related information.                                                                                                                               |
| `skip_if_exists`   | `Sequence[str]`                                               | Specified additional [file skip patterns][patterns-syntax].<br>See the [`skip_if_exists`][] setting for related information.                                                                                                                               |
| `skip_tasks`       | `bool`                                                        | When `True`, skip [template tasks execution][tasks].<br>See the [`skip_tasks`][] setting for related information.                                                                                                                                          |
| `src_path`         | `PurePath`                                                    | The absolute path to the (cloned/downloaded) template on disk.                                                                                                                                                                                             |
| `unsafe`           | `bool`                                                        | When `True`, allow usage of unsafe templates.<br>See the [`unsafe`][] setting for related information.                                                                                                                                                     |
| `use_prereleases`  | `bool`                                                        | When `True`, `vcs_ref`/`vcs_ref_hash` may refer to a prerelease version of the template.<br>See the [`use_prereleases`][] setting for related information.                                                                                                 |
| `user_defaults`    | `dict[str, Any]`                                              | Specified user defaults that may override a template's defaults during question prompts.                                                                                                                                                                   |
| `vcs_ref`          | <code>str &vert; None</code>                                  | The VCS tag/commit of the template, `None` if the template is not VCS-tracked.<br>See the [`vcs_ref`][] setting for related information.                                                                                                                   |
| `vcs_ref_hash`     | <code>str &vert; None</code>                                  | The VCS commit hash of the template, `None` if the template is not VCS-tracked.                                                                                                                                                                            |

### `_copier_python`

The absolute path of the Python interpreter running Copier.

### `_external_data`

A dict of the data contained in [external_data][].

When rendering the template, that data will be exposed in the special `_external_data`
variable:

-   Keys will be the same as in [external_data][].
-   Values will be the files contents parsed as YAML. JSON is also compatible.
-   Parsing is done lazily on first use.

### `_folder_name`

The name of the project root directory.

### `_copier_phase`

The current phase, one of `"prompt"`,`"tasks"`, `"migrate"` or `"render"`.

!!! note

    There is also an additional `"undefined"` phase used when not in any phase.
    You may encounter this phase when rendering outside of those phases,
    when rendering lazily (and the phase notion can be irrelevant) or when testing.

## Variables (context-dependent)

Some variables are only available in select contexts:

### `_copier_operation`

The current operation, either `"copy"` or `"update"`.

Availability: [`exclude`](configuring.md#exclude), [`tasks`](configuring.md#tasks)

## Variables (context-specific)

Some rendering contexts provide variables unique to them:

-   [`migrations`](configuring.md#migrations)

## Loop over lists to generate files and directories

You can use the special `yield` tag in file and directory names to generate multiple
files or directories based on a list of items.

In the path name, `#!jinja {% yield item from list_of_items %}{{ item }}{% endyield %}`
will loop over the `list_of_items` and replace `#!jinja {{ item }}` with each item in
the list.

A looped `#!jinja {{ item }}` will be available in the scope of generated files and
directories.

```yaml title="copier.yml"
commands:
    type: yaml
    multiselect: true
    choices:
        init:
            value: &init
                name: init
                subcommands:
                    - config
                    - database
        run:
            value: &run
                name: run
                subcommands:
                    - server
                    - worker
        deploy:
            value: &deploy
                name: deploy
                subcommands:
                    - staging
                    - production
    default: [*init, *run, *deploy]
```

```tree result="shell"
commands
    {% yield cmd from commands %}{{ cmd.name }}{% endyield %}
        __init__.py
        {% yield subcmd from cmd.subcommands %}{{ subcmd }}{% endyield %}.py.jinja
```

```python+jinja title="{% yield subcmd from cmd.subcommands %}{{ subcmd }}{% endyield %}.py.jinja"
print("This is the `{{ subcmd }}` subcommand in the `{{ cmd.name }}` command")
```

If you answer with the default to the question, Copier will generate the following
structure:

```tree result="shell"
commands
    deploy
        __init__.py
        production.py
        staging.py
    init
        __init__.py
        config.py
        database.py
    run
        __init__.py
        server.py
        worker.py
```

Where looped variables `cmd` and `subcmd` are rendered in generated files:

```python title="commands/init/config.py"
print("This is the `config` subcommand in the `init` command")
```
