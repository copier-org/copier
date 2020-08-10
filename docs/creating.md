# Creating a template

A template is a directory: usually the root folder of a git repository.

The content of the files inside the project template is copied to the destination
without changes, **unless they end with `.tmpl`** (or
[your chosen suffix](configuring.md#templates_suffix)). In that case, the templating
engine will be used to render them.

A slightly customized Jinja2 templating is used. The main difference is those variables
are referenced with `[[ name ]]` instead of `{{ name }}` and blocks are `[% if name %]`
instead of `{% if name %}`. To read more about templating see the
[Jinja2 documentation](https://jinja.palletsprojects.com/).

If a **YAML** file named `copier.yml` is found in the root of the project
(alternatively, a YAML file named `copier.yaml`), the user will be prompted to fill in
or confirm the default values.

## Template helpers

In addition to
[all the features Jinja supports](https://jinja.palletsprojects.com/en/2.11.x/templates/),
Copier includes:

### Builtin variables/functions

-   `now()` to get current UTC time.
-   `make_secret()` to get a random string.
-   `_copier_answers` includes the current answers dict, but slightly modified to make
    it suitable to [autoupdate your project safely](configuring.md#the-answers-file):
    -   It doesn't contain secret answers.
    -   It doesn't contain any data that is not easy to render to JSON or YAML.
    -   It contains special keys like `_commit` and `_src_path`, indicating how the last
        template update was done.
-   `_copier_conf` includes the current copier `ConfigData` object, also slightly
    modified:
    -   It only contains JSON-serializable data.
    -   But you have to serialize it with `[[ _copier_conf.json() ]]` instead of
        `[[ _copier_conf|tojson ]]`.
    -   ⚠️ It contains secret answers inside its `.data` key.
    -   Modifying it doesn't alter the current rendering configuration.

### Builtin filters

-   `anything|to_nice_yaml` to print as pretty-formatted YAML.

    Without arguments it defaults to:
    `anything|to_nice_yaml(indent=2, width=80, allow_unicode=True)`, but you can modify
    those.
