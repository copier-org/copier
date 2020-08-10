# Updating a project

The best way to update a project from its template is when all of these conditions are
true:

1. The template includes a valid `.copier-answers.yml` file.
2. The template is versioned with git (with tags).
3. The destination folder is versioned with git.

If that's your case, then just enter the destination folder, make sure `git status`
shows it clean, and run:

```bash
copier update
```

This will read all available git tags, will compare them using
[PEP 440](https://www.python.org/dev/peps/pep-0440/), and will check out the latest one
before updating. To update to the latest commit, add `--vcs-ref=HEAD`. You can use any
other git ref you want.

When updating, Copier will do its best to respect your project evolution by using the
answers you provided when copied last time. However, sometimes it's impossible for
Copier to know what to do with a diff code hunk. In those cases, you will find `*.rej`
files that contain the unresolved diffs. _You should review those manually_ before
committing.

You probably don't want `*.rej` files in your git history, but if you add them to
`.gitignore`, some important changes could pass unnoticed to you. That's why the
recommended way to deal with them is to _not_ add them to add a
[pre-commit](https://pre-commit.com/) (or equivalent) hook that forbids them, just like
this:

```yaml
# .pre-commit-config.yaml
repos:
    - repo: local
      hooks:
          - id: forbidden-files
            name: forbidden files
            entry: found copier update rejection files; review them and remove them
            language: fail
            files: "\\.rej$"
```
