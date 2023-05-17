# Updating a project

The best way to update a project from its template is when all of these conditions are
true:

1. The template includes
   [a valid `.copier-answers.yml` file](configuring.md#the-copier-answersyml-file).
1. The template is versioned with Git (with tags).
1. The destination folder is versioned with Git.

If that's your case, then just enter the destination folder, make sure `git status`
shows it clean, and run:

```shell
copier update
```

This will read all available Git tags, will compare them using
[PEP 440](https://www.python.org/dev/peps/pep-0440/), and will check out the latest one
before updating. To update to the latest commit, add `--vcs-ref=HEAD`. You can use any
other Git ref you want.

When updating, Copier will do its best to respect your project evolution by using the
answers you provided when copied last time. However, sometimes it's impossible for
Copier to know what to do with a diff code hunk. In those cases, copier handles the
conflict in one of two ways, controlled with the `--conflict` option:

-   `--conflict rej` (default): Creates a separate `.rej` file for each file with
    conflicts. These files contain the unresolved diffs.
-   `--conflict inline` (experimental): Updates the file with conflict markers. This is
    quite similar to the conflict markers created when a `git merge` command encounters
    a conflict. For more information, see the "Checking Out Conflicts" section of the
    [`git` documentation](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging).

If the update results in conflicts, _you should review those manually_ before
committing.

You probably don't want to lose important changes or to include merge conflicts in your
Git history, but if you aren't careful, it's easy to make mistakes.

That's why the recommended way to prevent these mistakes is to add a
[pre-commit](https://pre-commit.com/) (or equivalent) hook that forbids committing
conflict files or markers. The recommended hook configuration depends on the `conflict`
setting you use.

## Preventing Commit of Merge Conflicts

If you use `--conflict rej` (the default):

```yaml title=".pre-commit-config.yaml"
repos:
    - repo: local
      hooks:
          # Prevent committing .rej files
          - id: forbidden-files
            name: forbidden files
            entry: found Copier update rejection files; review them and remove them
            language: fail
            files: "\\.rej$"
    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v4.3.0
      hooks:
          # Prevent committing inline conflict markers
          - id: check-merge-conflict
            args: [--assume-in-merge]
```

## Never change the answers file manually

!!! important

    **Never** update `.copier-answers.yml` manually.

    This will trick Copier, making it believe that those modified answers produced the
    current subproject, while it was produced by a different answers set. This will
    produce unpredictable behavior of the smart diff algorithm used for updates, which
    may work under certain circumstances, but not always.

    **This is an unsupported way to update**. Please do not open issues if you updated
    this way.

**The correct process to update a subproject** is:

1. Run `copier update`.
1. Answer the questions. They'll default to your answers on your last update.

If you want to just reuse all previous answers:

```shell
copier --force update
```

If you want to change just one question, and leave all others untouched, and don't want
to go through the whole questionary again:

```shell
copier --force --data updated_question="my new answer" update
```

## How the update works

To understand how the updating process works, take a look at this diagram:

```mermaid
graph TD

%% nodes ----------------------------------------------------------
template_repo("template repository")
template_current("/tmp/template<br>(current tag)")
template_latest("/tmp/template<br>(latest tag)")

project_regen("/tmp/project<br>(fresh, current version)")
project_current("current project")
project_half("half migrated<br>project")
project_updated("updated project")
project_applied("updated project<br>(diff applied)")
project_full("fully updated<br>and migrated project")

update["update current<br>project in-place<br>(prompting)<br>+ run tasks again"]
compare["compare to get diff"]
apply["apply diff"]

diff("diff")

%% edges ----------------------------------------------------------
        template_repo --> |git clone| template_current
        template_repo --> |git clone| template_latest

     template_current --> |generate and run tasks| project_regen
      project_current --> compare
      project_current --> |apply pre-migrations| project_half
        project_regen --> compare
         project_half --> update
      template_latest --> update
               update --> project_updated
              compare --> diff
                 diff --> apply
      project_updated --> apply
                apply --> project_applied
      project_applied --> |apply post-migrations| project_full

%% style ----------------------------------------------------------
classDef blackborder stroke:#000;
class compare,update,apply blackborder;
```

As you can see here, `copier` does several things:

-   It regenerates a fresh project from the current template version.
-   Then, it compares both version to get the diff from "fresh project" to "current
    project".
-   Now, it applies pre-migrations to your project, and updates the current project with
    the latest template changes (asking for confirmation).
-   Finally, it re-applies the previously obtained diff and then runs the
    post-migrations.

!!! important

    The diff obtained by comparing the fresh, regenerated project to your
    current project can cancel the modifications applied by the update from the latest
    template version. During the process, `copier` will ask for your confirmation to
    overwrite or skip modifications, but in the end, it is possible that nothing has
    changed (except for the version in `.copier-answers.yml` of course). This is not a
    bug: although it can be quite surprising, this behavior is correct.

## Migration across Copier major versions

When there's a new major release of Copier (for example from Copier 5.x to 6.x), there
are chances that there's something that changed. Maybe your template will not work as it
did before.

[As explained above][how-the-update-works], Copier needs to make a copy of the template
in its old state with its old answers so it can actually produce a diff with the new
state and answers and apply the smart update to the project. However, **how can I be
sure that Copier will produce the same "old state" if I copied the template with an
older Copier major release?** Good question.

We will do our best to respect older behaviors for at least one extra major release
cycle, but the simpler answer is that you can't be sure of that.

How to overcome that situation?

1. You can write good [migrations][].
1. Then you can test them on your template's CI on a matrix against several Copier
   versions.
1. Or you can just [recopy the project][regenerating-a-project] when you update to a
   newer Copier major release.

## When the update gets broken because while replaying old copy

This is uncommon, but it can happen sometimes. For example, maybe the last update was
relying on some external resources that are not longer available. Generally, you should
keep your templates as pure as possible to avoid those situations.

However, if this is happening to you, try the `copier recopy` command, which will
discard all the smart update algorithm explained here. It will behave just like if you
were applying the template for the 1st time, but it will keep your answers from the last
update.
