**Think this library is awesome? Vote with a 👍 to include it in the awesome-python
list: https://github.com/DoronCohen/awesome-python/pull/1**

# ![Copier](https://github.com/pykong/copier/raw/master/img/copier-logotype.png)

[![codecov](https://codecov.io/gh/pykong/copier/branch/master/graph/badge.svg)](https://codecov.io/gh/pykong/copier)
![](https://github.com/pykong/copier/workflows/CI/badge.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
![](https://img.shields.io/pypi/pyversions/copier)
![](https://img.shields.io/pypi/v/copier)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A library for rendering project templates.

- Works with **local** paths and **git URLs**.
- Your project can include any file and `Copier` can dynamically replace values in any
  kind of text file.
- It generates a beautiful output and takes care of not overwrite existing files unless
  instructed to do so.

![Sample output](https://github.com/pykong/copier/raw/master/img/copier-output.png)

## Installation

1. Install Git 2.24 or newer.
1. To use as a CLI app: `pipx install copier`
1. To use as a library: `pip install copier`

## Quick usage

- Use it in your Python code:

```python
from copier import copy

# Create a project from a local path
copy("path/to/project/template", "path/to/destination")

# Or from a git URL.
copy("https://github.com/pykong/copier.git", "path/to/destination")

# You can also use "gh:" as a shortcut of "https://github.com/"
copy("gh:pykong/copier.git", "path/to/destination")

# Or "gl:" as a shortcut of "https://gitlab.com/"
copy("gl:pykong/copier.git", "path/to/destination")
```

- Or as a command-line tool:

```bash
copier path/to/project/template path/to/destination
```

## Browse or tag public templates

You can browse public copier templates in GitHub using
[the `copier-template` topic](https://github.com/topics/copier-template). Use them as
inspiration!

If you want your template to appear in that list, just add the topic to it! 🏷

## Comparison with other project generators

### Cookiecutter

Cookiecutter and Copier are quite similar in functionality, except that:

- Cookiecutter uses a subdirectory to generate the project, while Copier can use either
  the root directory (default) or a subdirectory.
- Cookiecutter uses default Jinja templating characters: `{{`, `{%`, etc., while Copier
  uses `[[`, `[%`, etc., and can be configured to change those.
- Cookiecutter puts context variables in a namespace: `{{ cookiecutter.name }}`, while
  Copier sets them directly: `[[ name ]]`.
- You configure your template in `copier.yml` instead of `cookiecutter.json`.
- Prompts are enhanced in Copier:
  - Type-casting and verifications
  - YAML native types + `json` and `yaml`
  - Descriptions (help message for prompts)
  - Conditional prompts (_soon_)
- Copier has very useful features that are missing in Cookiecutter (or require extra
  software), like the ability to **update a generated project** when the original
  template changes, and to run **migrations** when updating.

## Credits

Special thanks go to [jpscaletti](https://github.com/jpscaletti) for originally creating
`Copier`. This project would not be a thing without him.

Big thanks also go to [Yajo](https://github.com/Yajo) for his relentless zest for
improving `Copier` even further.

Thanks a lot, [pawamoy](https://github.com/pawamoy) for polishing very important rough
edges and improving the documentation and UX a lot.
