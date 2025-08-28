# Changelog

All notable changes to this project will be documented in this file. This project
adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) versioning schema, and
the changelog itself conforms to [Keep A Changelog](https://keepachangelog.com/).

## v9.10.1 (2025-08-28)

### Fix

-   **deps**: cap prompt-toolkit to <3.0.52

## v9.10.0 (2025-08-26)

### Feat

-   add support for nested multi-document includes in `copier.yml` (#2251)

### Fix

-   disable default answer validator for secret questions

## v9.9.1 (2025-08-18)

### Security

-   disallow render paths outside destination directory
-   cast Jinja context path variables to `pathlib.PurePath`

## v9.9.0 (2025-08-01)

### Feat

-   add support for prompting filesystem paths (#2210)

### Fix

-   **updating**: disable secret question validator when replaying old copy
-   **vcs**: fix cloning local dirty template repo when `core.fsmonitor=true` (#2151)

## v9.8.0 (2025-07-07)

### Feat

-   add support for providing serialized answers to multiselect choice questions
-   **updating**: add VCS ref sentinel `:current:` for referring to the current template
    ref

### Fix

-   avoid infinite recursion when accessing `_copier_conf.answers_file` via Jinja
    context hook
-   validate default answers
-   correct git stage order on merge conflicts

## v9.7.1 (2025-04-23)

### Refactor

-   import from module `_tools` instead of `tools`

## v9.7.0 (2025-04-22)

### Feat

-   raise new `TaskError` exception on task errors
-   raise `InteractiveSessionError` when prompting in non-interactive environment

### Fix

-   **settings**: use `<CONFIG_ROOT>/copier` as settings directory on Windows (#2071)
-   **updating**: ignore last answer of `when: false` questions
-   restore access to full rendering context in prompt phase

### Refactor

-   re-expose API with deprecation warnings on non-public API imports
-   rename internal modules with a `_` prefix

## v9.6.0 (2025-03-09)

### Feat

-   Add `_copier_operation` variable (#1733)
-   **context**: expose a `_copier_phase` context variable

### Fix

-   explicitly specify file encoding for windows (#2007)
-   auto-detect encoding when reading external data file
-   **settings**: auto-detect encoding when reading settings file
-   **cli**: auto-detect encoding when reading unicode-encoded file specified with
    `--data-file`
-   expose only answers in question rendering context
-   ignore `$file` if `$file.tmpl` exists when subdirectory is used
-   decode external data file content explicitly as UTF-8
-   decode answers file content explicitly as UTF-8

### Refactor

-   use common answers file loader

## v9.5.0 (2025-02-17)

### Feat

-   **external_data**: load data from other YAML files
-   **settings**: allow to define some trusted repositories or prefixes
-   **settings**: add user settings support with `defaults` values (fix #235)
-   add dynamic file structures in loop using yield-tag (#1855)
-   add support for dynamic choices

### Fix

-   correctly record missing stages in index for merge conflicts (#1907)
-   allow importing from a file that has a conditional name
-   **updating**: don't crash when file is removed from template's `.gitignore` file
    (#1886)
-   **deps**: update dependency packaging to v24.2
-   re-render answers file path when producing render context
-   restore compatibility with Git prior to v2.31 (#1838)
-   **updating**: don't validate computed values
-   Don't mark files without conflict markers as unmerged (#1813)

## v9.4.1 (2024-10-18)

### Fix

-   restore support for `preserve_symlinks: false` for directories (#1820)

## v9.4.0 (2024-10-15)

### Fix

-   **exclude**: support negative exclude matching child of excluded parent
-   parse new answer when `--skip-answered` is used
-   validate answers to secret questions
-   **updating**: do not recreate deleted paths on update (#1719)
-   support Git config without user identity

### Refactor

-   set default value for `keep_trailing_newline` more idiomatically
-   drop support for Python 3.8

### Perf

-   **updating**: avoid creating subproject copy

## v9.3.1 (2024-07-03)

### Fix

-   pass `--skip-tasks` flag to worker (#1688)

## v9.3.0 (2024-07-01)

### Feat

-   add simpler migrations configuration syntax (#1510)

### Fix

-   **tasks**: do not consider unsafe if they are being skipped
-   add context information to answer validation error message (#1609)
-   do not overwrite identical files (#1576)
-   **updating**: unset invalid last answers
-   render `default` list items for multi-select choice questions
-   **updating**: yield merge conflict when both template and project add same file

## v9.2.0 (2024-04-04)

### Feat

-   **tasks**: add support for skipping tasks (#1561)
-   add support for validating multi-select choice answers

### Fix

-   ignore empty YAML documents in `copier.yml`
-   preserve choices order in answers to multi-select choice questions
-   **exclude**: apply exclude matcher to rendered path

### Refactor

-   drop `pyyaml-include` dependency and reimplement relevant features

### Perf

-   apply `PERF` lint rules fixes (#1556)

## v9.1.1 (2024-01-16)

### Fix

-   don't fail in systems with windows 1252 encoding (probably)
-   skip excluded paths before rendering

## v9.1.0 (2023-11-27)

### Feat

-   Conflicts on updates now appear as git merge conflicts, also on VSCode
-   **choices**: support questionary checkbox for multiple choices using
    `multiselect: true`.

### Fix

-   mark package as typed
-   Normalize paths obtained from Git commands output
-   don't crash when update replaces file with symlink (or vice versa) (#1409)
-   keep git-ignored files on update (#1373)
-   address deprecation warning in `shutil.rmtree(onerror=...)` (#1401)

## v9.0.1 (2023-10-30)

### Fix

-   don't produce output when imported with `$FORCE_COLOR=1` env

## v9.0.0 (2023-10-22)

### BREAKING CHANGE

-   Changes the return code for unsafe template error from 2 to 4 to avoid return code
    collision with Plumbum's `SwitchError` type errors which use return code 2.

### Feat

-   allow overriding data file with CLI arguments (#1332)
-   **cli**: read answers from yaml file (#1325)

### Fix

-   **vcs**: prevent local clone from being stuck by gpg prompts (#1360)
-   **pydantic**: compatible with 2.4+, solving `FieldValidationInfo` warning (#1342)
-   fix answer validation for `type: str` questions
-   version guess from tags that don't start with `v`, but are still PEP440 compliant
    (#1048)
-   **cli**: use return code 4 for unsafe template error
-   **nix**: detect build version appropriately

## v8.3.0 (2023-09-05)

### Feat

-   add `-A` as an alias for `--skip-answered`, and support it in `recopy` too
-   add `--skip-answered` flag to avoid repeating recorded answers

### Fix

-   **recopy**: never clone old template (even less if it's just for cleanup)

## v8.2.0 (2023-08-28)

### Feat

-   release on FlakeHub.com too
-   add support for pre-update and post-update messages (#1288)
-   add support for pre-copy and post-copy messages

### Fix

-   do not immediately fail if git is not available
-   provide more clarification in unsafe error message (#1280)
-   clean up tmp dir
-   don't lie about updated files
-   require default value for secret question
-   fix answer validation against conditional choices with duplicate values

### Refactor

-   drop support for Python 3.7 (#1252)

## v8.1.0 (2023-07-10)

### Feat

-   add support for computed values via skipped questions (#1220)
-   add `--trust` as a less scary alternative to `--UNSAFE` (#1179)
-   add OS identifier to render context

### Fix

-   **pydantic**: add upper dependency bound to fix unlocked installations

### Refactor

-   request answers imperatively instead of implicitly via impure property

## v8.0.0 (2023-06-04)

### BREAKING CHANGE

-   Updates will overwrite existing files always. If you need to select only some files,
    just use `git mergetool` or `git difftool` after updating.
-   Flag `--overwrite/-w` disappeared from `copier update`. It is now implicit.
-   To update via API, `overwrite=True` is now required.
-   The default update conflict mode is now `inline` instead of `rej`.
-   By default, updates now consider 3 lines of context instead of just 1.
-   All CLI calls to Copier must now include the subcommand as the 1st argument. For
    example, `copier` must become now `copier update`; also `copier ./tpl ./dst` must
    become `copier copy ./tpl ./dst`.
-   All flags must go after the subcommand now. For example,
    `copier -r HEAD update ./dst` must now become `copier update -r HEAD ./dst` or
    `copier update ./dst -r HEAD`.
-   Automatic mode removed. Since now subcommands are required, the automatic mode is
    removed.
-   Deprecated `copier.copy` function is removed. Use `copier.run_copy`,
    `copier.run_update` or `copier.run_recopy` explicitly as needed.
-   default values must be of the same type than the question.

### Feat

-   disable unsafe features by default and add `--UNSAFE` switch (#1171)
-   basic nixpkgs overlay
-   add `recopy` command and function
-   support conditional choices (#1010)
-   validate default values (#1075)

### Fix

-   explain better why an answer casting fails
-   **cli**: display subcommand args meaning
-   preserver recursive symlinks
-   work around Pydantic bug when parsing choices
-   skip validating question and generating its default value when its skip condition is
    met

### Refactor

-   overwrite always on updates
-   **update**: default to inline markers and 3 lines of context
-   remove unused local overrides to answers

## v7.2.0 (2023-04-19)

### Feat

-   customizable update accuracy

### Fix

-   fix using a branch name as VCS ref
-   answer validation for question with complex choices (#1110)

## v7.1.0 (2023-04-07)

### Feat

-   include git in flake app
-   support preserving symlinks when copying templates (#938)
-   allow imports in inline templates (#986)
-   properly support update in repo subdirectory (#1069)
-   allow templating `_answers_file` setting (#1027)
-   let answers file exist in a subdirectory
-   validate answers given via CLI/API
-   exclude nothing by default when using subdirectory
-   add native OS directory separator variable in `_copier_conf.sep` to allow generating
    dynamic directory structures
-   nix support

### Fix

-   include dirty local changes when copying HEAD
-   require answer for questions without default value (#958)
-   **cleanup**: don't clean up local template in parent folder
-   delete conditionally created file when answer changes (#982)
-   properly support diffs over updates with new interactive answers
-   ignore Git hooks during project update (#1066)
-   properly support diffs over updates with new answers
-   skip tasks in pretend mode (#970)
-   parse CLI data using question's answer parser
-   don't set YAML `!include` constructor globally (#947)
-   **cli**: use `--conflict` flag only in `copier update` subcommand
-   ignore template repo tags that aren't valid PEP 440 versions
-   --skip option was ignored (#966)
-   Remove useless is_dir check
-   don't attempt to render a file if its name is empty
-   warn users against using shallow clones as template source

### Refactor

-   **tests**: remove unknown timeout marker
-   deduplicate code
-   remove unused method argument
-   simplify casting boolean question settings
-   remove useless code related to not asking a question
-   **typing**: use `Mapping` instead of `ChainMap` type
-   move unrelated code out of try-except block
-   **inline**: smarter inline conflict markers algorithm

## v7.1.0a0 (2022-12-29)

### Feat

-   experimental inline conflict markers when updating
-   merge copier settings from multiple documents

### Fix

-   remove dependency on iteration_utilities

## v7.0.1 (2022-10-14)

### Fix

-   remove deprecated code scheduled for removal in Copier v7 (#843)

## v7.0.0 (2022-10-12)

### Feat

-   expand tilde in template source path (#835)

### Fix

-   delete temporary clones after execution automatically (#802)
-   **typing**: remove invalid migration task stage "task"

### Refactor

-   **typing**: use abstract container types where possible (#832)
-   use `dict` constructor as default factory
-   **typing**: remove unused types
-   remove unreachable code (#826)
-   model a task to execute using a dataclass
-   reduce module imports

## v6.2.0 (2022-09-18)

### Feat

-   add validator field to Question (#719)
-   support passing github or gitlab urls without the .git suffix (#677)

### Fix

-   compatibility with pydantic 1.10
-   git bundle support breaks with relative paths
-   prevent name collision for question var name "value"

### Refactor

-   add "flake8-simplify" plugin and simplify code

## v6.1.0 (2022-06-13)

### Feat

-   support getting template commit hash with `{{ _copier_conf.vcs_ref_hash }}`
-   simplify the format of the question prompt (#689)

### Fix

-   ignore non-PEP-440-compliant tags (#676)

## [6.0.0] - 2022-05-15

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
-   Copy dirty changes from a Git-tracked template to the project by default, to make
    testing easier.
-   Advertise clearly which version is being copied or updated in the CLI.
-   Add jinja variable `_copier_python` to provide Python `sys.executable`.

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
-   Removing files from templates will remove them too from the subprojects when they
    get updated.

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
    fake ordering when Git commit descriptions happen to be ordered in a non-predictable
    way.
-   Answers file will only remember answers to questions specified in the questionary.

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

-   Make Copier work fine with Git 2.28.
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

-   Assert minimum Copier version.
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
-   `prompt_bool` can now have an undefined default (and answer is mandatory in that
    case).
-   Reactivates the `copier.yml` and `copier.yaml` as configuration files.
-   The new `extra_paths` argument specifies additional paths to find templates to
    inherit from.

### [2.3.0] - 2019-04-17

-   Back to using a setup.py instead of a pyproject.toml.
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
