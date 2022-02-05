# Changelog

All notable changes to this project will be documented in this file. This project
adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) versioning schema, and
the changelog itself conforms to [Keep A Changelog](https://keepachangelog.com/).

## [Unreleased]

[All changes here](https://github.com/copier-org/copier/issues?q=milestone%3Av6.0.0).
Summary:

### Added

-   Allow using additional Jinja 2 extensions.
-   Major version mismatch warning. If your Copier version is too new, you'll be warned.
-   Specific exceptions, which will help on error detection for API usages.
-   Multiline questions.
-   Conditional questions.
-   Placeholders.
-   Interactive TUI for questionaries. Prompts are way cooler now. 😎
-   Python 3.9 support.
-   Python 3.10 support.
-   Support empty templates suffix, telling Copier to render every file.
-   Added `--defaults` flag to use default answers to questions, which might be null if
    not specified.
-   Added `--overwrite` flag to overwrite files that already exist, without asking.
-   In migration scripts, we have the new environment variables `$VERSION_PEP440_FROM`,
    `$VERSION_PEP440_CURRENT` and `$VERSION_PEP440_TO`, which will always get a valid
    PEP440 version identifier, without the `v` prefix, allowing your migration scripts
    to have a valid standard where to base their logic.
-   Raise a CopierAnswersInterrupt instead of a bare KeyboardInterrupt to provide
    callers with additional context - such as the partially completed AnswersMap.
-   Support for `user_defaults`, which take precedence over template defaults.
-   Copy dirty changes from a git-tracked template to the project by default, to make
    testing easier.
-   Advertise clearly which version is being copied or updated in the CLI.

### Changed

-   Fully refactored core.
-   Running `copier copy` on a preexisting project now recopies the project instead of
    updating it. That means that it respects old answers, but ignores history diff.
-   We use Jinja 2 defaults now. `{{ }}` instead of `[[ ]]` and similar.
-   We keep trailing newlines by default for Jinja 2 templates.
-   Copier will never ask for overwriting the answers file.
-   Multi-typed choices follow the same type-casting logic as any other question, so
    it's easier to reason about them. However, if you were using this feature, you might
    be surprised about its side effects if you don't specify the type explicitly. Just
    add `type: yaml` to make it behave _mostly_ as before. Or just don't use that, it's
    complicated anyway (warn added to docs).
-   Changed `--force` to be the same as `--defaults --overwrite`.
-   Copied files will reflect permissions on the same files in the template.
-   Copier now uses `git clone --filter=blob:none` when cloning, to be faster.

### Deprecated

-   Deprecated `now` and `make_secret` functions. If your template used those, Copier
    will emit warnings leading you on how to upgrade it.
-   Templates marked with `_min_copier_version` below 6 will still default to use
    bracket-based Jinja defaults, but that will disappear soon. If you want your
    template to work on Copier 5 and 6, make sure to declare `_envops` explicitly in
    your `copier.yaml`.
-   `copier.copy()` is confusing, now that actually copying and updating are 2
    completely different actions (before, you were actually always updating if
    possible). Its direct equivalent is now `copier.run_auto()`, and `copier.copy()`
    will disappear in the future.

### Removed

-   Minimal supported Python version is now 3.7 (dropped Python 3.6 support).
-   Removed the `json` method on `_copier_conf`. Where you would previously use
    `_copier_conf.json()` in your templates, please now use `_copier_conf|to_json`
    instead.
-   `--subdirectory` flag, which was confusing... and probably useless.
-   Lots of dead code.

### Fixed

-   A directory that gets an empty name works as expected: not copied (nor its
    contents).
-   When comparing versions to update, PEP 440 is always used now. This way, we avoid
    fake ordering when git commit descriptions happen to be ordered in a non-predictable
    way.

### Security

## [5.1.0] - 2020-08-17

[All changes here](https://github.com/copier-org/copier/milestone/14?closed=1). Summary:

-   Forbid downgrades.
-   Print all logs to STDERR.

## [5.0.0] - 2020-08-13

[All changes here](https://github.com/copier-org/copier/milestone/2?closed=1). Summary:

-   Add `--prerelease` flag, which will be `False` by default. This is a behavioral
    change and that's basically why I'm doing a new major release. All other changes are
    minor here.
-   Better docs.

## [4.1.0] - 2020-08-10

[All changes here](https://github.com/copier-org/copier/milestone/12?closed=1). Summary:

-   Make copier work fine with Git 2.28.
-   We have [docs](https://copier.readthedocs.io/)!
-   Polish docs a little bit.
-   We now run tests on macOS and Windows!

## [4.0.2] - 2020-07-21

[All changes here](https://github.com/copier-org/copier/milestone/11?closed=1). Summary:

-   Fix wrong templated default answers classification, which produced some questions
    being ignored.

## [4.0.1] - 2020-06-23

[All changes here](https://github.com/copier-org/copier/milestone/10?closed=1). Summary:

-   Fix wrong prompt regression when updating.
-   Remove redundant `dst` fixture in tests.

## [4.0.0] - 2020-06

[All changes here](https://github.com/copier-org/copier/milestone/9?closed=1). Summary:

-   Remove semver to avoid having 2 different versioning systems. We stick to PEP 440
    now.
-   Remember where an answer comes from.
-   Do not re-ask to the user if already answer via `--data`.
-   Support pre-migration scripts that modify the answers file.

## [3.2.0] - 2020-06

[All changes here](https://github.com/copier-org/copier/milestone/8?closed=1). Summary:

-   Templates can now use a subdirectory instead of always the template root.

## [3.1.0] - 2020-05

[All changes here](https://github.com/pykong/copier/milestone/7?closed=1). Summary:

-   Assert minimum copier version.
-   Prettier prompts.
-   Prompt self-templating.
-   Better README.

## [3.0.0] - 2020-03

This is a big release with many new features added and improved. The code base also
received a lot of love and hardening.

### Features

-   Minimal supported Python version is now 3.6.
-   Dropped support for deprecated `voodoo.json`.
-   Introduced gitignore-style patterns for `exclude` und `skip-if-exists`.
-   Dropped support for `include` option.
-   Added support for extending content of config files via content of other files via
    `pyaml-include`.
-   Customizable template extension.
-   Ability to remember last answers.
-   Ability to choose where to remember them.
-   Template upgrades support, (based on the previous points) with migration tasks
    specification.
-   Extended questions format, supporting help, format, choices and secrets.
-   More beautiful prompts.
-   New CLI experience.

### Other

-   Moved to `poetry` for package management.
-   Type annotated entire code base.
-   Increased test coverage.
-   Ditched `ruamel.yaml` for `PyYaml`.
-   Ditched Travis CI for GitHub Actions.
-   Added `pre-commit` for enforced linting.
-   Added `prettier`, `black` and `isort` for code formatting.
-   Added `pytest` for running tests.
-   Use `plumbum` as CLI and subprocess engine.

### [2.5.0] - 2019-06-16

-   Expanduser on all paths (so "~/foo/bar" is expanded to
    "<YOUR_HOME_FOLDER>/foo/bar").
-   Improve the output when running tasks.
-   Remove the destination folder if the copy process or one of the tasks fail.
-   Add a `cleanup_on_error` flag to optionally disable the cleanup feature.
-   Add the `skip_if_exists` option to skip files, without asking, if they already
    exists in the destination folder.

## [2.4.2] - 2019-06-09

-   Fix MAJOR bug that was preventing the `_exclude`, `_include` and `_tasks` keys from
    `copier.yml` (or alternatives) to be used at all. It also interpreted `_tasks` as a
    user-provided variable.

### [2.4.0] - 2019-06-08

-   Empty folders are now copied. The folders are also displayed in the console output
    instead of just the files.
-   `prompt_bool` can now have an undefined default (ans answer is mandatory in that
    case).
-   Reactivates the `copier.yml` and `copier.yaml` as configuration files.
-   The new `extra_paths` argument specifies additional paths to find templates to
    inherit from.

### [2.3.0] - 2019-04-17

-   Back to using a setup.py intead of a pyproject.toml.
-   The recommended configuration file is now `copier.toml`.

### [2.2.3] - 2019-04-13

-   The `copier` command-line script now accepts "help" and "version" as commands.

### [2.1.0] - 2019-02-08

-   Task runner 🎉.
-   Use `_exclude`, `_include`, and `_tasks` keys in `copier.yml` as the default values
    for the `.copy()` arguments `exclude`, `include`, and `tasks`.

### [2.0.0] - 2019-02-07

-   Rebranded from `Voodoo` to `Copier`!
-   Dropped support for Python 2.x, the minimal version is now Python 3.5.
-   Cleanup and 100% test coverage.
-   The recommended configuration file is now `copier.yaml`, but a `copier.json` can be
    used as well. The old `voodoo.json` is also supported _for now_ but is deprecated
    and will be removed in version 2.2.
-   Python package format updated to the latest standard (no `setup.py` 😵).
-   Renamed the `render_skeleton()` function to `copy()`. The function signature remains
    almost the same, the only changes are:
    -   `filter_this` parameter is now called `exclude`.
    -   `ignore_this` parameter is now called just `ignore`.
-   Dropped the idea of storing the templates in a hidden `$HOME` folder.
