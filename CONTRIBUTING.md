# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and
credit will always be given.

## Report Bugs

Report bugs at <https://github.com/copier-org/copier/issues>.

If you are reporting a bug, please include:

-   Your operating system name and version.
-   Any details about your local setup that might be helpful in troubleshooting.
-   Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever
wants to implement it.

## Implement Features

Look through the GitHub issues for features. Anything tagged with "Feature request" is
open to whoever wants to implement it.

## Write Documentation

The project could always use more documentation, whether as part of the official project
docs, or even on the web in blog posts, articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/copier-org/copier/issues>.

If you are proposing a feature:

-   Explain in detail how it would work.
-   Keep the scope as narrow as possible, to make it easier to implement.
-   Remember that this is a volunteer-driven project, and that contributions are welcome
    :)

## Discuss

Feel free to discuss with our community through
[our discussions channel](https://github.com/copier-org/copier/discussions). Be polite!

## Dev environment setup

We use some tools as part of our development workflow which you'll need to install into
your host environment:

-   [poetry](https://python-poetry.org/) for packaging and dependency management
-   [poethepoet](https://github.com/nat-n/poethepoet) for running development tasks

Or you can use
[![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/copier-org/copier)
to start hacking with one click!

## Get Started!

Ready to contribute? Here's how to set up the project for local development.

1.  Fork the copier repo on GitHub.
2.  Clone your fork locally:

```bash
git clone git@github.com:copier-org/copier.git
```

3.  Use poetry to setup a virtualenv to develop in

```bash
poetry install -E docs # create's a virtualenv with all dependencies from pyproject.toml
poetry shell   # creates a new shell with the virtualenv activated
```

5.  Create a branch for local development:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

6.  When you're done making changes, check that your changes pass all tests

```bash
poe test
poe lint
```

To have multiple Python versions on the same machine for running `tox`, I recommend
using [pyenv](https://github.com/pyenv/pyenv) (_do not_ confuse it with `pipenv`,).

7.  Commit your changes and push your branch to GitHub:

```
git add .
git commit -m "Detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

8.  Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1.  The pull request has code, it should include tests.
2.  Check that all checks pass on GitHub CI

## Tips

To run a subset of tests:

    $  poe test tests/the-tests-file.py
