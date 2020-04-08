# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and
credit will always be given.

You can contribute in many ways:

### Report Bugs

Report bugs at <https://github.com/jpscaletti/copier/issues>.

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever
wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "Feature request" is
open to whoever wants to implement it.

### Write Documentation

The project could always use more documentation, whether as part of the official project
docs, or even on the web in blog posts, articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/jpscaletti/copier/issues>.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome
  :)

## Get Started!

Ready to contribute? Here's how to set up the project for local development.

1.  Fork the copier repo on GitHub.
2.  Clone your fork locally:

```bash
git clone git@github.com:jpscaletti/copier.git
```

3.  Install your local copy into a virtualenv.

```bash
python -m virtualenv .venv
source .venv/bin/activate
make install
```

5.  Create a branch for local development:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

6.  When you're done making changes, check that your changes pass all tests

```bash
pytest -x .
flake8 .
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
2.  Run `tox` and make sure that the tests pass for all supported Python versions.

## Tips

To run a subset of tests:

    $  pytest tests/the-tests-file.py
