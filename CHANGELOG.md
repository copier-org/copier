# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)


### Version 2.4 (UNRELEASED)
- `prompt_bool` can now have an undefined default (ans answer is mandatory in that case).
- The new `extra_paths` argument specifies additional paths to find templates to inherit from.

### Version 2.3 (2019-04)
- Drop the ruamel.yaml dependency.
- Back to using a setup.py intead of a pyproject.toml.
- The recommended configuration file is now `copier.toml`.


### Version 2.2 (2019-04)
- The `copier` command-line script now accepts "help" and "version" as commands.


### Version 2.1 (2019-02)

- Task runner 🎉.
- Use `_exclude`, `_include`, and `_tasks` keys in `copier.yml` as the default
  values for the `.copy()` arguments `exclude`, `include`, and `tasks`.


### Version 2.0 (2019-02)

- Rebranded from `Voodoo` to `Copier`!
- Dropped support for Python 2.x, the minimal version is now Python 3.5.
- Cleanup and 100% test coverage.
- The recommended configuration file is now `copier.yaml`, but a `copier.json`
  can be used as well. The old `voodoo.json` is also supported *for now* but is
  deprecated and will be removed in version 2.2.
- Python package format updated to the latest standard (no `setup.py` 😵).
- Renamed the `render_skeleton()` function to `copy()`. The function signature remains
  almost the same, the only changes are:
  - `filter_this` parameter is now called `exclude`.
  - `ignore_this` parameter is now called just `ignore`.
- Dropped the idea of storing the templates in a hidden `$HOME` folder.
