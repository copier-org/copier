# Updating a project

The best way to update a project from its template is when all of these conditions are
true:

1. The template includes [a valid `.copier-answers.yml`
   file][the-copier-answersyml-file].
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

## How the update works

To understand how the updating process works, take a look at this diagram:

<!-- prettier-ignore-start -->
<div class="mermaid">
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

update["upate current<br>project in-place<br>(prompting)<br>+ run tasks again"]
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
classDef grey fill:#e8e8e8;
class compare,update,apply grey;
</div>

<!-- prettier-ignore-end -->

As you can see here, `copier` does several things:

-   it regenerates a fresh project from the current template version
-   then it compares both version, to get the diff from "fresh project" to "current
    project"
-   now it applies pre-migrations to your project, and updates the current project with
    the latest template changes (asking confirmation)
-   finally, it re-applies the previously obtained diff, and then run the
    post-migrations

!!! important

    The diff obtained by comparing the fresh, regenerated project to your
    current project can cancel the modifications applied by the update from the latest
    template version. During the process, `copier` will ask you confirmation to overwrite or
    skip modifications, but in the end, it is possible that nothing has changed (except for
    the version in `.copier-answers.yml` of course). This is not a bug: although it can be
    quite surprising, this behavior is correct.
