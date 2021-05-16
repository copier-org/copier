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

!!! info

    Some settings are _only_ available as CLI arguments, and some others _only_ as
    template configurations. Some behave differently depending on where they are
    defined. [Check the docs for each specific setting](#available-settings).

Copier obtains **answers** from these sources, in this order of priority:

1. Command line or API arguments.
1. Asking the user. Notice that Copier will not ask any questions answered in the
   previous source.
1. [Answer from last execution](#the-copier-answersyml-file).
1. Default values defined in [the `copier.yml` file](#the-copieryml-file).

## The `copier.yml` file

The `copier.yml` (or `copier.yaml`) file is found in the root of the template, and it is
the main entrypoint for managing your template configuration. It will be read and used
for two purposes:

-   [Prompting the user for information](#questions).
-   [Applying template settings](#available-settings) (excluding files, setting
    arguments defaults, etc.).

### Questions

For each key found, Copier will prompt the user to fill or confirm the values before
they become available to the project template.

!!! example

    This `copier.yml` file:

    ```yaml
    name_of_the_project: My awesome project
    number_of_eels: 1234
    your_email: ""
    ```

    Will result in a questionary similar to:

    <pre style="font-weight: bold">
    🎤 name_of_the_project? Format: str <span style="color:orange">My awesome project</span>
    🎤 number_of_eels? Format: int <span style="color:orange">1234</span>
    🎤 your_email? Format: str
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
    from typing it if it's quite common. When using `choices`, the default must be the
    choice _value_, not its _key_. If values are quite long, you can use
    [YAML anchors](https://confluence.atlassian.com/bitbucket/yaml-anchors-960154027.html).
-   **secret**: When `true`, it hides the prompt displaying asterisks (`*****`) and
    doesn't save the answer in [the answers file](#the-copier-answersyml-file)
-   **placeholder**: To provide a visual example for what would be a good value. It is
    only shown while the answer is empty, so maybe it doesn't make much sense to provide
    both `default` and `placeholder`.

    !!! warning

        Multiline placeholders are not supported currently, due to
        [this upstream bug](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1267).

-   **multiline**: When set to `true`, it allows multiline input. This is especially
    useful when `type` is `json` or `yaml`.

-   **when**: Condition that, if `false`, skips the question. If it is a boolean, it is
    used directly (although it's a bit absurd in that case). If it is a string, it is
    converted to boolean using a parser similar to YAML, but only for boolean values.
    This is most useful when [templated](#prompt-templating).

!!! example

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
        placeholder: my top secret password

    # I'll avoid default and help here, but you can use them too
    age:
        type: int

    height:
        type: float

    any_json:
        help: Tell me anything, but format it as a one-line JSON string
        type: json
        multiline: true

    any_yaml:
        help: Tell me anything, but format it as a one-line YAML string
        type: yaml # This is the default type, also for short syntax questions
        multiline: true

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

Most of those options can be templated using Jinja.

Keep in mind that the configuration is loaded as **YAML**, so the contents must be
**valid YAML** and respect **Copier's structure**. That is why we explicitly wrap some
strings in double-quotes in the following examples.

Answers provided through interactive prompting will not be rendered with Jinja, so you
cannot use Jinja templating in your answers.

!!! example

    ```yaml
    # default
    username:
        type: str

    organization:
        type: str

    email:
        type: str
        # Notice that both `username` and `organization` have been already asked
        default: "{{ username }}@{{ organization }}.com"

    # help
    copyright_holder:
        type: str
        when: "{% if organization != 'Public domain' %}true{% endif %}"
        help: The person or entity within {{ organization }} that holds copyrights.

    # type
    target:
        type: str
        choices:
            - humans
            - machines

    user_config:
        type: "{% if target == 'humans' %}yaml{% else %}json{% endif %}"

    # choices
    title:
        type: str
        help: Your title within {{ organization }}

    contact:
        choices:
            Copyright holder: "{{ copyright_holder }}"
            CEO: Alice Bob
            CTO: Carl Dave
            "{{ title }}": "{{ username }}"
    ```

!!! warning

    Keep in mind that:

    1. You can only template inside the value...
    1. ... which must be a string to be templated.
    1. Also you won't be able to use variables that aren't yet declared.

    ```yaml
    your_age:
        type: int

    # Valid
    double_it:
        type: int
        default: "{{ type * 2}}"

    # Invalid, the templating occurs outside of the parameter value
    did_you_ask:
        type: str
        {% if your_age %}
        default: "yes"
        {% else %}
        placeholder: "nope"
        {% endif %}

    # Invalid, `a_random_word` wasn't answered yet
    other_random_word:
        type: str
        placeholder: "Something different to {{ a_random_word }}"

    # Invalid, YAML interprets curly braces
    a_random_word:
        type: str
        default: {{ 'hello' }}
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

File where answers will be recorded by default.

!!! tip

    Remember to add that file to your Git template if you want to support
    [updates](updating.md).

Don't forget to read [the docs about the answers file](#the-copier-answersyml-file).

!!! example

    ```yaml
    _answers_file: .my-custom-answers.yml
    ```

### `cleanup_on_error`

-   Format: `bool`
-   CLI flags: `-C`, `--no-cleanup` (used to disable this setting; only available in
    `copier copy` subcommand)
-   Default value: `True`

When Copier creates the destination path, if there's any failure when rendering the
template (either in the rendering process or when running the [tasks](#tasks)), Copier
will delete that folder.

Copier will never delete the folder if it didn't create it. For this reason, when
running `copier update`, this setting has no effect.

!!! info

    Not supported in `copier.yml`.

### `data`

-   Format: `dict|List[str=str]`
-   CLI flags: `-d`, `--data`
-   Default value: N/A

Give answers to questions through CLI/API.

This cannot be defined in `copier.yml`, where its equivalent would be just normal
questions with default answers.

!!! example

    Example CLI usage to take all default answers from template, except the user name,
    which is overriden, and don't ask user anything else:

    ```sh
    copier -fd 'user_name=Manuel Calavera' copy template destination
    ```

### `envops`

-   Format: `dict`
-   CLI flags: N/A
-   Default value: `{}`

Configurations for the Jinja environment. It's empty by default, to use the same
defaults as upstream Jinja.

See [upstream docs](https://jinja.palletsprojects.com/en/2.11.x/api/#jinja2.Environment)
to know available options.

!!! warning

    Copier 5 and older had different, bracket-based defaults.

    If your template was created for Copier 5, you need to add this configuration to
    your `copier.yaml` to keep it working just like before:

    ```yaml
    _envops:
        autoescape: false
        block_end_string: "%]"
        block_start_string: "[%"
        comment_end_string: "#]"
        comment_start_string: "[#"
        keep_trailing_newline: true
        variable_end_string: "]]"
        variable_start_string: "[["
    ```

    By specifying this, your template will be compatible with both Copier 5 and 6.

    Copier 6 will apply these older defaults if your [min_copier_version][] is lower
    than 6, but that will be removed in the future.

### `exclude`

-   Format: `List[str]`
-   CLI flags: `-x`, `--exclude`
-   Default value:
    `["copier.yaml", "copier.yml", "~*", "*.py[co]", "__pycache__", ".git", ".DS_Store", ".svn"]`

[Patterns](#patterns-syntax) for files/folders that must not be copied.

The CLI option can be passed several times to add several patterns.

!!! info

    When you define this parameter in `copier.yml`, it will **replace** the default
    value.

    In this example, for instance, `"copier.yml"` will **not** be excluded:

    !!! example

        ```yaml
        _exclude:
            - "*.bar"
            - ".git"
        ```

!!! info

    When you add this parameter from CLI or API, it will **not replace** the values
    defined in `copier.yml` (or the defaults, if missing).

    Instead, CLI/API definitions **will extend** those from `copier.yml`.


    !!! example Example CLI usage to copy only a single file from the template

        ```sh
        copier --exclude '*' --exclude '!file-i-want' copy ./template ./destination
        ```

### `force`

-   Format: `bool`
-   CLI flags: `-f`, `--force`
-   Default value: `False`

Overwrite files that already exist, without asking.

Also don't ask questions to the user; just use default values
[obtained from other sources](#configuration-sources).

!!! info

    Not supported in `copier.yml`.

### `jinja_extensions`

-   Format: `List[str]`
-   CLI flags: N/A
-   Default value: `[]`

Additional Jinja2 extensions to load in the Jinja2 environment. Extensions can add
filters, global variables and functions, or tags to the environment.

The following extensions are _always_ loaded:

-   [`jinja2_ansible_filters.AnsibleCoreFiltersExtension`](https://gitlab.com/dreamer-labs/libraries/jinja2-ansible-filters/):
    this extension adds most of the
    [Ansible filters](https://docs.ansible.com/ansible/2.3/playbooks_filters.html) to
    the environment.

You don't need to tell your template users to install these extensions: Copier depends
on them, so they are always installed when Copier is installed.

!!! warning

    Including an extension allows Copier to execute uncontrolled code, thus making the
    template potentially more dangerous. Be careful about what extensions you install.

!!! info "Note to template writers"

    You must inform your users that they need to install the extensions alongside Copier,
    i.e. in the same virtualenv where Copier is installed.
    For example, if your template uses `jinja2_time.TimeExtension`,
    your users must install the `jinja2-time` Python package.

    ```bash
    # with pip, in the same virtualenv where Copier is installed
    pip install jinja2-time

    # if Copier was installed with pipx
    pipx inject copier jinja2-time
    ```

!!! example

    ```yaml
    _jinja_extensions:
        - jinja_markdown.MarkdownExtension
        - jinja2_slug.SlugExtension
        - jinja2_time.TimeExtension
    ```

!!! hint

    Examples of extensions you can use:

    -   From [cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/):

        -   [`cookiecutter.extensions.JsonifyExtension`](https://cookiecutter.readthedocs.io/en/latest/advanced/template_extensions.html#jsonify-extension):
            provides a `jsonify` filter, to format a dictionary as JSON. Note that Copier
            natively provides a `to_nice_json` filter that can achieve the same thing.
        -   [`cookiecutter.extensions.RandomStringExtension`](https://cookiecutter.readthedocs.io/en/latest/advanced/template_extensions.html#random-string-extension):
            provides a `random_ascii_string(length, punctuation=False)` global function.
            Note that Copier natively provides the `ans_random` and `hash` filters that can
            be used to achieve the same thing:

            !!! example

                ```jinja
                {{ 999999999999999999999999999999999|ans_random|hash('sha512') }}
                ```

        -   [`cookiecutter.extensions.SlugifyExtension`](https://cookiecutter.readthedocs.io/en/latest/advanced/template_extensions.html#slugify-extension):
            provides a `slugify` filter using
            [python-slugify](https://github.com/un33k/python-slugify).

    -   [`copier_templates_extensions.TemplateExtensionLoader`](https://github.com/pawamoy/copier-templates-extensions):
        enhances the extension loading mecanism to allow templates writers to put their
        extensions directly in their templates.
    -   [`jinja_markdown.MarkdownExtension`](https://github.com/jpsca/jinja-markdown):
        provides a `markdown` tag that will render Markdown to HTML using
        [PyMdown extensions](https://facelessuser.github.io/pymdown-extensions/).
    -   [`jinja2_slug.SlugExtension`](https://pypi.org/project/jinja2-slug/#files): provides
        a `slug` filter using [unicode-slugify](https://github.com/mozilla/unicode-slugify).
    -   [`jinja2_time.TimeExtension`](https://github.com/hackebrot/jinja2-time): adds a
        `now` tag that provides convenient access to the
        [arrow.now()](http://crsmithdev.com/arrow/#arrow.factory.ArrowFactory.now) API.

    Search for more extensions on GitHub using the
    [jinja2-extension topic](https://github.com/topics/jinja2-extension), or
    [other Jinja2 topics](https://github.com/search?q=jinja&type=topics), or
    [on PyPI using the jinja + extension keywords](https://pypi.org/search/?q=jinja+extension).

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

They will only run when _new version >= declared version > old version_. And only when
updating (not when copying for the 1st time).

If the migrations definition contains Jinja code, it will be rendered with the same
context as the rest of the template.

Migration processes will contain the `$VERSION_FROM`, `$VERSION_TO`, `$VERSION_CURRENT`
and `$STAGE` (before/after) environment variables

!!! example

    ```yaml
    _migrations:
        - version: v1.0.0
        before:
            - rm ./old-folder
        after:
            # {{ _copier_conf.src_path }} points to the path where the template was
            # cloned, so it can be helpful to run migration scripts stored there.
            - invoke -r {{ _copier_conf.src_path }} -c migrations migrate $VERSION_CURRENT
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

!!! info

    If Copier detects that there is a major version difference, it will warn you about
    possible incompatibilities. Remember that a new major release means that some
    features can be dropped or changed, so it's probably a good idea to ask the
    template maintainer to update it.

!!! example

    ```yaml
    _min_copier_version: "4.1.0"
    ```

### `pretend`

-   Format: `bool`
-   CLI flags: `-n`, `--pretend`
-   Default value: `False`

Run but do not make any changes.

!!! info

    Not supported in `copier.yml`.

### `quiet`

-   Format: `bool`
-   CLI flags: `-q`, `--quiet`
-   Default value: `False`

Suppress status output.

!!! info

    Not supported in `copier.yml`.

### `skip_if_exists`

-   Format: `List[str]`
-   CLI flags: `-s`, `--skip`
-   Default value: N/A

[Patterns](#patterns-syntax) for files/folders that must be skipped if they already
exist.

!!! example

    For example, it can be used if your project generates a password the 1st time and
    you don't want to override it next times:

    ```yaml
    # copier.yml
    _skip_if_exists: .secret_password.yml
    ```

    ```yaml
    # .secret_password.yml.tmpl
    {{999999999999999999999999999999999|ans_random|hash('sha512')}}
    ```

### `subdirectory`

-   Format: `str`
-   CLI flags: N/A
-   Default value: N/A

Subdirectory to use as the template root when generating a project. If not specified,
the root of the template is used.

This allows you to keep separate the template metadata and the template code.

!!! tip

    If your template is meant to be applied to other templates (a.k.a. recursive
    templates), use this option to be able to use [updates](updating.md).

!!! example

    ```yaml
    _subdirectory: template
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
    - "rm {{ name_of_the_project }}/README.md"
    # Arrays are executed without shell, saving you the work of escaping arguments
    - [invoke, "--search-root={{ _copier_conf.src_path }}", after-copy]
    # You are able to output the full conf to JSON, to be parsed by your script,
    # but you cannot use the normal `|tojson` filter; instead, use `.json()`
    - [invoke, end-process, "--full-conf={{ _copier_conf.json() }}"]
```

### `templates_suffix`

-   Format: `str`
-   CLI flags: N/A
-   Default value: `.jinja`

Suffix that instructs which files are to be processed by Jinja as templates.

!!! example

    ```yaml
    _templates_suffix: .my-custom-suffix
    ```

An empty suffix is also valid, and will instruct Copier to copy
and render _every file_, except those that are [excluded by default](#default).

!!! example

    ```yaml
    _templates_suffix: ""
    ```

!!! warning

    Copier 5 and older had a different default value: `.tmpl`. If you wish to keep it,
    add it to your `copier.yml` to keep it future-proof.

    Copier 6 will apply that old default if your [min_copier_version][] is lower
    than 6, but that will be removed in the future.

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

    Not supported in `copier.yml`.

### `vcs_ref`

-   Format: `str`
-   CLI flags: `-r`, `-vcs-ref`
-   Default value: N/A (use latest release)

When copying or updating from a git-versioned template, indicate which template version
to copy.

This is stored automatically in the answers file, like this:

```yaml
_commit: v1.0.0
```

!!! info

    Not supported in `copier.yml`.

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

The file **must be called exactly `{{ _copier_conf.answers_file }}.jinja`** (or ended
with [your chosen suffix](#templates_suffix)) in your template's root folder) to allow
[applying multiple templates to the same subproject](#applying-multiple-templates-to-the-same-subproject).

The default name will be `.copier-answers.yml`, but
[you can define a different default path for this file](#answers_file).

The file must have this content:

```yaml
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
{{_copier_answers|to_nice_yaml}}
```

!!! important

    Did you notice that `NEVER EDIT MANUALLY` part?
    [It is important](updating.md#never-change-the-answers-file-manually).

The builtin `_copier_answers` variable includes all data needed to smooth future updates
of this project. This includes (but is not limited to) all JSON-serializable values
declared as user questions in [the `copier.yml` file](#the-copieryml-file).

As you can see, you also have the power to customize what will be logged here. Keys that
start with an underscore (`_`) are specific to Copier. Other keys should match questions
in `copier.yml`.

### Applying multiple templates to the same subproject

Imagine this scenario:

1. You use one framework that has a public template to generate a project. It's
   available at `https://github.com/example-framework/framework-template.git`.
1. You have a generic template that you apply to all your projects to use the same
   pre-commit configuration (formatters, linters, static type checkers...). You have
   published that in `https://gitlab.com/my-stuff/pre-commit-template.git`.
1. You have a private template that configures your subproject to run in your internal
   CI. It's found in `git@gitlab.example.com:my-company/ci-template.git`.

All 3 templates are completely independent:

-   Anybody can generate a project for the specific framework, no matter if they want to
    use pre-commit or not.
-   You want to share the same pre-commit configurations, no matter if the subproject is
    for one or another framework.
-   You want to have a centralized CI configuration for all your company projects, no
    matter their pre-commit configuration or the framework they rely on.

Well, don't worry. Copier has you covered. You just need to use a different answers file
for each one. All of them contain a `{{ _copier_conf.answers_file }}.jinja` file
[as specified above](#the-copier-answersyml-file). Then you apply all the templates to
the same project:

```bash
mkdir my-project
cd my-project
git init
# Apply framework template
copier -a .copier-answers.main.yml copy https://github.com/example-framework/framework-template.git .
git add .
git commit -m 'Start project based on framework template'
# Apply pre-commit template
copier -a .copier-answers.pre-commit.yml copy https://gitlab.com/my-stuff/pre-commit-template.git .
git add .
pre-commit run -a  # Just in case 😉
git commit -am 'Apply pre-commit template'
# Apply internal CI template
copier -a .copier-answers.ci.yml copy git@gitlab.example.com:my-company/ci-template.git .
git add .
git commit -m 'Apply internal CI template'
```

Done!

After a while, when templates get new releases, updates are handled separately for each
template:

```bash
copier -a .copier-answers.main.yml update
copier -a .copier-answers.pre-commit.yml update
copier -a .copier-answers.ci.yml update
```
