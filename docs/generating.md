# Generating a project

!!! warning

    Generate projects only from trusted templates as their tasks run with the
    same level of access as your user.

As seen in the quick usage section, you can generate a project from a template using the
`copier` command-line tool:

```bash
copier path/to/project/template path/to/destination
```

Or within Python code:

```python
copier.run_auto("path/to/project/template", "path/to/destination")
```

The "template" parameter can be a local path, an URL, or a shortcut URL:

-   GitHub: `gh:namespace/project`
-   GitLab: `gl:namespace/project`

Use the `--data` command-line argument or the `data` parameter of the
`copier.run_auto()` function to pass whatever extra context you want to be available in
the templates. The arguments can be any valid Python value, even a function.

Use the `--vcs-ref` command-line argument to checkout a particular git ref before
generating the project.

[All the available options][copier.cli] are described with the `--help-all` option.

## Templates versions

By default, copier will copy from the last release found in template git tags, sorted as
[PEP 440][], regardless of whether the template is from a URL or a local clone of a git
repository.

The exception to this is if you use a local clone of a template repository that has had
any modifications made, in this case Copier will use this modified working copy of the
template to aid development of new template features.

If you would like to override the version of template being installed, the
[`--vcs-ref`](../configuring/#vcs_ref) argument can be used to specify a branch, tag or
other reference to use.

For example to use the latest master branch from a public repository:

```
copier --vcs-ref master https://github.com/foo/copier-template.git ./path/to/destination
```

Or to work from the current checked out revision of a local template:

```
copier --vcs-ref HEAD path/to/project/template path/to/destination
```

## Regenerating a project

When you execute `copier copy $template $project` again over a preexisting `$project`,
Copier will just "recopy" it, ignoring previous history.

!!! warning

    This is not [the recommended approach for updating a project][updating-a-project],
    where you usually want Copier to respect the project evolution wherever it doesn't
    conflict with the template evolution.
