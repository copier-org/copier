# Creating a template

A template is a directory: usually the root folder of a git repository.

The content of the files inside the project template is copied to the destination
without changes, **unless they end with `.jinja`** (or
[your chosen suffix](configuring.md#templates_suffix)). In that case, the templating
engine will be used to render them.

Jinja2 templating is used. Learn more about it by reading
[Jinja2 documentation](https://jinja.palletsprojects.com/).

If a **YAML** file named `copier.yml` or `copier.yaml` is found in the root of the
project, the user will be prompted to fill in or confirm the default values.

## Template helpers

In addition to
[all the features Jinja supports](https://jinja.palletsprojects.com/en/2.11.x/templates/),
Copier includes:

-   All functions and filters from
    [jinja2-ansible-filters](https://gitlab.com/dreamer-labs/libraries/jinja2-ansible-filters/).

    -   This includes the `to_nice_yaml` filter, which is used extensively in our
        context.

-   `_copier_answers` includes the current answers dict, but slightly modified to make
    it suitable to [autoupdate your project safely](configuring.md#the-answers-file):
    -   It doesn't contain secret answers.
    -   It doesn't contain any data that is not easy to render to JSON or YAML.
    -   It contains special keys like `_commit` and `_src_path`, indicating how the last
        template update was done.
-   `_copier_conf` includes a representation of the current copier
    <!-- prettier-ignore -->
    [Worker][copier.main.Worker] object, also slightly modified:
    -   It only contains JSON-serializable data.
    -   But you have to serialize it with `{{ _copier_conf.json() }}` instead of
        `{{ _copier_conf|to_json }}`.
    -   ⚠️ It contains secret answers inside its `.data` key.
    -   Modifying it doesn't alter the current rendering configuration.
