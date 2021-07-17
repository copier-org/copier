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

## Regenerating a project

When you execute `copier copy $template $project` again over a preexisting `$project`,
Copier will just "recopy" it, ignoring previous history.

!!! warning

    This is not [the recommended approach for updating a project][updating-a-project],
    where you usually want Copier to respect the project evolution wherever it doesn't
    conflict with the template evolution.
