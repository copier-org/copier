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

`_copier_conf` includes a representation of the current Copier
[Worker][copier.main.Worker] object, also slightly modified:

-   It only contains JSON-serializable data.
-   You can serialize it with `{{ _copier_conf|to_json }}`.
-   ⚠️ It contains secret answers inside its `.data` key.
-   Modifying it doesn't alter the current rendering configuration.

Furthermore, the following keys are added:

#### `os` { #\_copier_conf.os }

The detected operating system, either `"linux"`, `"macos"`, `"windows"` or `None`.

#### `sep` { #\_copier_conf.sep }

The operating system-specific directory separator.

#### `vcs_ref_hash` { #\_copier_conf.vcs_ref_hash }

The current commit hash from the template.

### `_copier_python`

The absolute path of the Python interpreter running Copier.

### `_folder_name`

The name of the project root directory.

## Variables (context-specific)

Some rendering contexts provide variables unique to them:

-   [`migrations`](configuring.md#migrations)

## Loop over lists to generate files and directories

You can use the special `yield` tag in file and directory names to generate multiple
files or directories based on a list of items.

In the path name, `{% yield item from list_of_items %}{{ item }}{% endyield %}` will
loop over the `list_of_items` and replace `{{ item }}` with each item in the list.

A looped `{{ item }}` will be available in the scope of generated files and directories.

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
