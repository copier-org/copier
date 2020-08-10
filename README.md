# ![Copier](https://github.com/copier-org/copier/raw/master/img/copier-logotype.png)

[![codecov](https://codecov.io/gh/copier-org/copier/branch/master/graph/badge.svg)](https://codecov.io/gh/copier-org/copier)
![](https://github.com/copier-org/copier/workflows/CI/badge.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
![](https://img.shields.io/pypi/pyversions/copier)
![](https://img.shields.io/pypi/v/copier)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation Status](https://readthedocs.org/projects/copier/badge/?version=latest)](https://copier.readthedocs.io/en/latest/?badge=latest)

A library for rendering project templates.

- Works with **local** paths and **git URLs**.
- Your project can include any file and `Copier` can dynamically replace values in any
  kind of text file.
- It generates a beautiful output and takes care of not overwrite existing files unless
  instructed to do so.

![Sample output](https://github.com/copier-org/copier/raw/master/img/copier-output.png)

## Installation

1. Install Python 3.6.1 or newer (3.8 or newer if you're on Windows).
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
copy("https://github.com/copier-org/copier.git", "path/to/destination")

# You can also use "gh:" as a shortcut of "https://github.com/"
copy("gh:copier-org/copier.git", "path/to/destination")

# Or "gl:" as a shortcut of "https://gitlab.com/"
copy("gl:copier-org/copier.git", "path/to/destination")
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

## Credits

Special thanks go to [jpscaletti](https://github.com/jpscaletti) for originally creating
`Copier`. This project would not be a thing without him.

Many thanks to [pykong](https://github.com/pykong) who took over maintainership on the
project, promoted it, and laid out the bases of what the project is today.

Big thanks also go to [Yajo](https://github.com/Yajo) for his relentless zest for
improving `Copier` even further.

Thanks a lot, [pawamoy](https://github.com/pawamoy) for polishing very important rough
edges and improving the documentation and UX a lot.
