## API

### copier.copy()

```python
copier.copy(
    src_path,
    dst_path,

    data=DEFAULT_DATA,
    *,
    exclude=DEFAULT_FILTER,
    skip_if_exists=[],
    tasks=[],

    envops={},
    extra_paths=[],

    pretend=False,
    force=False,
    skip=False,
    quiet=False,
    cleanup_on_error=True,
    subdirectory=None,
)
```

Uses the template in _src_path_ to generate a new project at _dst_path_.

**Arguments**:

-   **src_path** (str):<br> Absolute path to the project skeleton, which can also be a
    version control system URL.

-   **dst_path** (str):<br> Absolute path to where to render the skeleton.

-   **data** (dict):<br> Data to be passed to the templates in addition to the user data
    from a `copier.yml`.

-   **exclude** (list):<br> A list of names or gitignore-style patterns matching files
    or folders that must not be copied.

-   **skip_if_exists** (list):<br> A list of names or gitignore-style patterns matching
    files or folders, that are skipped if another with the same name already exists in
    the destination folder. (It only makes sense if you are copying to a folder that
    already exists).

-   **tasks** (list):<br> Optional lists of commands to run in order after finishing the
    copy. Like in the templates files, you can use variables on the commands that will
    be replaced by the real values before running the command. If one of the commands
    fails, the rest of them will not run.

-   **envops** (dict):<br> Extra options for the Jinja template environment. See
    available options in
    [Jinja's docs](https://jinja.palletsprojects.com/en/2.10.x/api/#jinja2.Environment).

    Copier uses these defaults that are different from Jinja's:

    ```yml
    # copier.yml
    _envops:
        block_start_string: "[%"
        block_end_string: "%]"
        comment_start_string: "[#"
        comment_end_string: "#]"
        variable_start_string: "[["
        variable_end_string: "]]"
        keep_trailing_newline: true
    ```

    You can use default Jinja syntax with:

    ```yml
    # copier.yml
    _envops:
        block_start_string: "{%"
        block_end_string: "%}"
        comment_start_string: "{#"
        comment_end_string: "#}"
        variable_start_string: "{{"
        variable_end_string: "}}"
        keep_trailing_newline: false
    ```

-   **extra_paths** (list):<br> Additional paths, from where to search for templates.
    This is intended to be used with shared parent templates, files with macros, etc.
    outside the copied project skeleton.

-   **pretend** (bool):<br> Run but do not make any changes.

-   **force** (bool):<br> Overwrite files that already exist, without asking.

-   **skip** (bool):<br> Skip files that already exist, without asking.

-   **quiet** (bool):<br> Suppress the status output.

-   **cleanup_on_error** (bool):<br> Remove the destination folder if the copy process
    or one of the tasks fails. True by default.

-   **subdirectory** (str):<br> Path to a sub-folder to use as the root of the template
    when generating the project. If not specified, the root of the git repository is
    used.
