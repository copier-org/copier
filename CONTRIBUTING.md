# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and
credit will always be given.

## Use of AI

We require all use of AI in contributions to follow our
[AI policy](https://github.com/copier-org/copier/blob/master/AI_POLICY.md).

## Report Bugs

Report bugs at <https://github.com/copier-org/copier/issues>.

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

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

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are
    welcome. :)

## Discuss

Feel free to discuss with our community through
[our discussions channel](https://github.com/copier-org/copier/discussions). Be polite!

## Dev Environment Setup

The recommended way is:

1. Click on
    [![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/copier-org/copier)
1. Wait until the terminal that pops up is ready.

For local development with a similar experience, we also offer a
[VS Code dev container](https://code.visualstudio.com/docs/devcontainers/containers)
integration.

For local or more complex setups, continue reading.

We use [mise](https://mise.jdx.dev/), which you'll need to install into your host
environment, to provide a reproducible development environment.

### Without mise

For some reasons you might want to avoid installing mise in your system. Maybe you don't
have enough permissions or you just don't want to add yet another tool to your system.

You can use standard Python tooling such as [uv][] and a valid Python installation
installed in an imperative manner of your choice, e.g. using uv as well.

However, you won't be able to auto-lint or auto-format code without mise. If you don't
have mise installed but you have Docker or Podman, you can run `poe lint` and get
similar results. It will use a container to install mise, and mise to install the
formatters.

If you still don't have Docker or Podman, don't worry. You can push your changes without
formatting. As long as you give Copier maintainers permissions to change your PR, a bot
will kindly auto-format code for you and push it back to your branch.

[uv]: https://docs.astral.sh/uv/

## Get Started

Ready to contribute? Here's how to set up the project for local development.

1. Fork the Copier repo on GitHub.

1. Clone your fork locally:

    ```shell
    git clone git@github.com:my-user/copier.git
    cd copier
    ```

1. Use mise to set up a development environment:

    ```shell
    mise trust
    mise install
    prek install
    ```

    This will download all development tools, including [uv][], and then use it to
    create a virtualenv and install Copier with all its development dependencies too.

1. Create a branch for local development:

    ```shell
    git checkout -b name-of-your-bugfix-or-feature
    ```

    Now you can make your changes locally.

1. When you're done making changes, check that your changes pass all tests:

    ```shell
    mise run test
    uv run poe lint
    ```

    `mise run test` sets up the same environment as CI; `uv run poe test` works too.

    To test against the lower bounds of the runtime dependencies, install the `lowest`
    mise environment and run the tests against it:

    ```shell
    mise -E lowest install
    mise -E lowest run test
    ```

    !!! note

        If you get fails due to
        `pexpect.exceptions.TIMEOUT: <pexpect.popen_spawn.PopenSpawn object at 0x............>`,
        you can adjust the timeout to a longer one (default: `10`), or remove the
        timeout (`0`). Either add it as an argument in your command:

        ```shell
        uv run poe test --spawn-timeout 0
        ```

        Or modify pytest arguments in VS Code workspace settings:

        ```json title=".vscode/settings.json"
        {
          ...
          "python.testing.pytestArgs": [
            "--spawn-timeout=0"
          ]
        }
        ```

1. Optionally, use pyclean to remove Python bytecode and build artifacts, e.g.

    ```shell
    uvx pyclean . --debris --verbose
    ```

    or

    ```shell
    pipx run pyclean . --debris --verbose
    ```

1. Commit your changes and push your branch to GitHub:

    ```shell
    git add .
    git commit
    git push origin name-of-your-bugfix-or-feature
    ```

1. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request has code, it should include tests.
1. Check that all checks pass on GitHub CI.
1. If something significant changed, modify docs.

### Commit message guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.

We use [git-cliff](https://git-cliff.org/) to draft our [changelog](CHANGELOG.md)
following [Keep a Changelog] and determine the next Copier version. For security fixes,
add `CVE:` and/or `GHSA:` trailers with the advisory IDs. Removals, including removals
of deprecated features, are breaking changes and must be marked with `!` or a
`BREAKING CHANGE:` footer.

[Keep a Changelog]: https://keepachangelog.com/en/2.0.0/

### Maintainer notes

If you're a maintainer and you want to merge a PR that will produce a confusing
changelog, then please squash the PR on merge, and change the commit message to make it
meaningful. Remember to
[respect co-autorship](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)
when squashing, especially if multiple authors were involved.

If the last commit is pushed back by `github-actions[bot]` and named
`style: autoformat with prek`, it's most likely an automatic reformatting commit
done by the CI.
[Those kind of commits cannot trigger other workflows](https://docs.github.com/en/actions/using-workflows/triggering-a-workflow#triggering-a-workflow-from-a-workflow).
Thus, to be able to re-run CI, close and reopen the PR. Consider squashing on merge if
possible and practical.

## Tips

To run a subset of tests:

```shell
uv run poe test tests/the-tests-file.py
```

## How to create a new release

This section is for maintainers. Since we use the
[conventional commits](https://www.conventionalcommits.org/) standard, the easiest way
to create a new release is to open Copier repo locally and run:

```shell
# Make sure you're in the last commit
git checkout master
git pull --tags

# Prepend a new changelog section for the next version
mise run changelog

# Review the changelog and curate it, then commit and tag it
version="$(git-cliff --bumped-version)"
git commit -am "chore: release $version"
git tag -a "$version" -m "$version"

# Push it
git push --follow-tags
```

Include PR references in the generated changelog by exporting the environment variable
`GITHUB_TOKEN` with a GitHub PAT with permissions `Contents: Read`, `Metadata: Read`,
and `Pull requests: Read`.

Pushing the tag triggers the release workflow, which publishes to PyPI and then creates
the GitHub release, using the matching [CHANGELOG](CHANGELOG.md) section as the release
notes.
