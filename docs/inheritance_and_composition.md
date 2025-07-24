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
    - A template that setups a CI/CD pipeline for building a Docker image and deploying it to a cloud provider starting from any python application;
    - A template that setups an ArgoCD application to run a service based on a Docker image in a Kubernetes cluster.

    The composition of these 3 templates would result in a new template that setups a web application with a CI/CD pipeline and an ArgoCD application to run it in a Kubernetes cluster.

### Operational Distinction between Inheritance and Composition

|                               | Inheritance | Composition |
| ----------------------------- | :---------: | :---------: |
| Number of parent templates    |      1      |  2 or more  |
| May add/averride parent parts |     Yes     |     No      |

## Why copier does not natively support inheritance and composition?

Copier is made to bootstrap projects based on a template and keep them updated. In the
Unix philosophy, that's the one thing it does well.

## Solutions

### Git submodules + jinja template inheritance

<!-- TODO: Add content-->

### Fork-like approach

<!-- TODO: Add content-->

### Delegated `copier copy` calls via tasks

<!-- TODO: Add content-->

### Meta-templates

<!-- TODO: Add content, see https://github.com/copier-org/copier/issues/934#issuecomment-1405492635-->

### Manually apply multiple templates

<!-- TODO: Add content, see https://copier.readthedocs.io/en/stable/configuring/#applying-multiple-templates-to-the-same-subproject -->
