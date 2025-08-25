# Template Inheritance and Composition

## What is Inheritance, what is Composition?

Template inheritance is a way to create a new (child) template based on an existing
(parent) template. It allows you to reuse code and structure from the parent template
while adding or overriding specific parts in the child template. This is useful for
creating variations of a template without duplicating code.

???+ example "Example of Inheritance"

    You have a (parent) template that instantiate a web application using the Flask framework.

    As a child template, you create a template that comes with a pre-built website designed for personal blog posting.

Template composition, on the other hand, is a way to combine multiple templates,
independent of each other, into a single new template. In this way you can join the
functionalities of multiple templates, by adding some "glue code", and avoid repetition.

???+ example "Example of Composition"

    You have 3 independent templates:

    - A template that setups the skeleton of a web application using the Flask framework;
    - A template that setups a CI/CD pipeline for building and pushing a Docker image of a python application;
    - A template that setups an ArgoCD application of a webapp, given a Docker image.

    The composition of these 3 templates would result in a new template that setups a web application with a CI/CD pipeline and an ArgoCD application to deploy it on a Kubernetes cluster.

### Operational Distinction between Inheritance and Composition

|                                  | Inheritance | Composition |
| -------------------------------- | :---------: | :---------: |
| Number of parent templates       |      1      |  2 or more  |
| May add/override parent(s) parts |     Yes     |     No      |

## Why copier does not natively support inheritance and composition?

Copier is made to bootstrap projects based on a template and keep them updated. In the
Unix philosophy, that's the one thing it does well.

## Solutions

Note: In the following we will focus mostly on the Inheritance problem, as it is the
most challenging. Composition will most likely emerge from the Inheritance solutions.

| Pro                                  | Git submodules + jinja template inheritance | Fork-like approach | Via `_tasks` and `_migrations` | Meta-templates | Manually apply multiple templates |
| ------------------------------------ | ------------------------------------------- | ------------------ | ------------------------------ | -------------- | --------------------------------- |
| Add questions to parent              | -                                           | -                  | Yes                            | -              | -                                 |
| Avoid repeat parent question         | -                                           | -                  | Yes                            | -              | -                                 |
| Override parent files                | -                                           | -                  | Yes                            | -              | -                                 |
| Handle parent updates                | -                                           | -                  | Yes                            | -              | -                                 |
| Approach can be used for composition | -                                           | -                  | Yes                            | -              | Yes                               |

| Contra             | Git submodules + jinja template inheritance | Fork-like approach | Via `_tasks` and `_migrations` | Meta-templates | Manually apply multiple templates |
| ------------------ | ------------------------------------------- | ------------------ | ------------------------------ | -------------- | --------------------------------- |
| Requires `--trust` | -                                           | -                  | Yes                            | -              | -                                 |

### Git submodules + Jinja template inheritance

<!-- TODO: Add content-->

### Fork-like approach

<!-- TODO: Add content-->

### Via `_tasks` and `_migrations`

[Look at the demo for the details :material-cursor-default-click:](https://github.com/francesco086/copier-inheritance-via-task-and-migration-demo-child#){
.md-button }

The basic idea is that the child template uses `_tasks` and `_migrations` to add the
parent's content. `_tasks` is used for `copier copy/recopy` commands, whereas
`_migrations` is leveraged to handle the `copier update` commands.

Attention must be paid to the overlapping files, which must be manually excluded from
the parent's to allow the child to override them.

The child template controls the parent's version, and can choose to update it or not (it
is not possible for the user).

#### TODOs

-   Mechanism to allow parent upgrade without need for `git stash`

### Meta-templates

<!-- TODO: Add content, see https://github.com/copier-org/copier/issues/934#issuecomment-1405492635-->

### Manually apply multiple templates

<!-- TODO: Add content, see https://copier.readthedocs.io/en/stable/configuring/#applying-multiple-templates-to-the-same-subproject -->
