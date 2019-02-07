# Copier Changelog

### Version 2.0.0

- Rebranded from `Voodoo` to `Copier`!
- Dropped support for Python 2.x, the minimal version is now Python 3.5.
- Cleanup and 100% test coverage.
- The reccomended configuration file is now `copier.yaml`, but a `copier.json`
  can be used as well. The old `voodoo.json` is also supported *for now* but is
  deprecated and will be removed in version 2.2.
- Python package format updated to the latest standard (no `setup.py` 😵).
- Renamed the `render_skeleton()` function to `copy()`. The function signature remains
  almost the same, the only changes are:
  - `filter_this` parameter is now called `exclude`.
  - `ignore_this` parameter is now called just `ignore`.
- Dropped the idea of storing the templates in a hidden `$HOME` folder.
