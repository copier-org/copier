# Generating a project

**Warning:** Generate projects only from trusted templates as their tasks run with the
same level of access as your user.

As seen in the quick usage section, you can generate a project from a template using the
`copier` command-line tool:

```bash
copier path/to/project/template path/to/destination
```

Or within Python code:

```python
copier.copy("path/to/project/template", "path/to/destination")
```

The "template" parameter can be a local path, an URL, or a shortcut URL:

-   GitHub: `gh:namespace/project`
-   GitLab: `gl:namespace/project`

Use the `--data` command-line argument or the `data` parameter of the `copier.copy()`
function to pass whatever extra context you want to be available in the templates. The
arguments can be any valid Python value, even a function.

Use the `--vcs-ref` command-line argument to checkout a particular git ref before
generating the project.

All the available options are described with the `--help-all` option.
