# Comparing Copier to other project generators

The subject of
[code scaffolding](<https://en.wikipedia.org/wiki/Scaffold_(programming)>) has been
around for some time, and there are long established good projects.

Here's a simple comparison. If you find something wrong, please open a PR and fix these
docs! We don't want to be biased, but it's easy that we tend to be:

!!! important

    Although Copier was born as a code scaffolding tool, it is today a code lifecycle
    management tool. This makes it somehow unique. Most tools below are only scaffolders
    and the comparison is not complete due to that.

<!-- Use https://www.tablesgenerator.com/markdown_tables to maintain this table -->

| Feature                                  | Copier                           | Cookiecutter                    | Yeoman        |
| ---------------------------------------- | -------------------------------- | ------------------------------- | ------------- |
| Can template file names                  | Yes                              | Yes                             | Yes           |
| Can generate file structures in loops    | Yes                              | No                              | No            |
| Configuration                            | Single YAML file[^1]             | Single JSON file                | JS module     |
| Migrations                               | Yes                              | No                              | No            |
| Programmed in                            | Python                           | Python                          | NodeJS        |
| Requires handwriting JSON                | No                               | Yes                             | Yes           |
| Requires installing templates separately | No                               | No                              | Yes           |
| Requires programming                     | No                               | No                              | Yes, JS       |
| Requires templates to have a suffix      | Yes by default, configurable[^3] | No, not configurable            | You choose    |
| Task hooks                               | Yes                              | Yes                             | Yes           |
| Context hooks                            | Yes[^5]                          | Yes                             | ?             |
| Template in a subfolder                  | Not required, but you choose     | Yes, required                   | Yes, required |
| Template package format                  | Git repo[^2], Git bundle, folder | Git or Mercurial repo, Zip file | NPM package   |
| Template updates                         | **Yes**[^4]                      | No[^6]                          | No            |
| Templating engine                        | [Jinja][]                        | [Jinja][]                       | [EJS][]       |

[jinja]: https://jinja.palletsprojects.com/
[ejs]: https://ejs.co/

[^1]: The file itself can [include other YAML files][include-other-yaml-files].

[^2]:
    Git repo is recommended to be able to use advanced features such as template tagging
    and smart updates.

[^3]:
    A suffix is required by default. Defaults to `.jinja`, but can be configured to use
    a different suffix, or to use none.

[^4]:
    Only for Git templates, because Copier uses Git tags to obtain available versions
    and extract smart diffs between them.

[^5]: Context hooks are provided through the [`ContextHook` extension][context-hook].

[^6]: Updates are possible through [Cruft][cruft].

[context-hook]:
    https://github.com/copier-org/copier-templates-extensions#context-hook-extension
[cruft]: https://github.com/cruft/cruft
