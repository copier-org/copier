# Comparing Copier to other project generators

The subject of project scaffolding has been around for some time, and Copier is just a
new one in a list of long established good projects. Here's a simple comparison. If you
find something wrong, please open a PR and fix it! We don't want to be biased, but it's
easy that we tend to be:

<!-- Use https://www.tablesgenerator.com/markdown_tables to maintain this table -->

| Feature                                  | Copier                                   | Cookiecutter                    | Yeoman        |
| ---------------------------------------- | ---------------------------------------- | ------------------------------- | ------------- |
| Can template file names                  | Yes                                      | Yes                             | Yes           |
| Configuration                            | Single or multiple YAML files            | Single JSON file                | JS module     |
| Migrations                               | Yes                                      | No                              | No            |
| Programmed in                            | Python                                   | Python                          | NodeJS        |
| Requires handwriting JSON                | No                                       | Yes                             | Yes           |
| Requires installing templates separately | No                                       | No                              | Yes           |
| Requires programming                     | No                                       | No                              | Yes, JS       |
| Requires templates to have a suffix      | Yes<sup>3</sup>                          | No, not configurable            | You choose    |
| Task hooks                               | Yes                                      | Yes                             | Yes           |
| Template in a subfolder                  | Not required, but you choose             | Yes, required                   | Yes, required |
| Template package format                  | Git repo<sup>2</sup>, Git bundle, folder | Git or Mercurial repo, Zip file | NPM package   |
| Template updates                         | Yes<sup>4</sup>                          | No                              | No            |
| Templating engine                        | [Jinja][]<sup>1</sup>                    | [Jinja][]                       | [EJS][]       |

[jinja]: https://jinja.palletsprojects.com/
[ejs]: https://ejs.co/

---

<sup>1</sup> Copier configures Jinja to use `[[ brackets ]]` instead of
`{{ curly braces }}` by default, but that can be changed per template if needed.

<sup>2</sup> Git repo is recommended to be able to use advanced features such as
template tagging and smart updates.

<sup>3</sup> A suffix is required. Defaults to `.tmpl`, but can be configured.

<sup>4</sup> Only for git templates, because Copier uses git tags to obtain available
versions and extract smart diffs between them.
