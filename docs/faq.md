# Frequently Asked Questions

## Can Copier be applied over a preexisting project?

Yes, of course. Copier understands this use case out of the box. That's actually what
powers features such as [updating](updating.md) or the ability of [applying multiple
templates to the same subproject][applying-multiple-templates-to-the-same-subproject].

!!! example

    ```shell
    copier copy https://github.com/me/my-template.git ./my-preexisting-git-project
    ```

## How to use Copier from Docker or Podman?

Copier doesn't provide an image by default. However, it does provide a nix package, so
you can use Nix to run Copier reproducibly from within a container:

```shell
# Change for docker if needed
engine=podman

# You can pin the version; example: github:copier-org/copier/v8.0.0
copier=github:copier-org/copier

$engine container run --rm -it docker.io/nixos/nix \
    nix --extra-experimental-features 'nix-command flakes' --accept-flake-config \
    run $copier -- --help
```

You can even generate a reproducible minimal docker image with just Copier inside, with:

```shell
nix bundle --bundler github:NixOS/bundlers#toDockerImage \
    github:copier-org/copier#packages.x86_64-linux.default
docker load < python*copier*.tar.gz
```

## How can I alter the context before rendering the project?

Similar questions:

-   **How can I add/remove variables to/from the rendering context?**
-   **How to infer context variables based on the users answers, without prompting
    users?**

Answer:

**Use the [`ContextHook` extension][context-hook].**

The [`ContextHook` extension][context-hook] lets you modify the context used to render
templates, so that you can add, change or remove variables.

[context-hook]:
    https://github.com/copier-org/copier-templates-extensions#context-hook-extension

In order for Copier to be able to load and use the extension when generating a project,
it must be installed alongside Copier itself. More details in the [`jinja_extensions`
docs][jinja_extensions].

You can then configure your Jinja extensions in Copier's configuration file:

```yaml title="copier.yaml"
_jinja_extensions:
    - copier_templates_extensions.TemplateExtensionLoader
    - extensions/context.py:ContextUpdater
```

Following this example, you are supposed to provide a `context.py` file in the
`extensions` folder at the root of your template to modify the context. If for example
your `copier.yaml` contains a multiple-choice variable like this:

```yaml title="copier.yaml"
flavor:
    type: str
    choices:
        - docker
        - instances
        - kubernetes
        - none
```

The `context.py` file contains your context hook which could look like:

```python title="extensions/context.py"
from copier_templates_extensions import ContextHook


class ContextUpdater(ContextHook):
    def hook(self, context):
        flavor = context["flavor"]  # user's answer to the "flavor" question
        return {
            "isDocker": flavor == "docker"
            "isK8s": flavor == "kubernetes"
            "isInstances": flavor == "instances"
            "isLite": flavor == "none"
            "isNotDocker": flavor != "docker"
            "isNotK8s": flavor != "kubernetes"
            "isNotInstances": flavor != "instances"
            "isNotLite": flavor != "none"
            "hasContainers": flavor in {"docker", "kubernetes"}
        }
```

Before rendering each templated file/folder, the context will be updated with this new
context object that you return from the hook. If you wish to update the context in-place
rather than update it, set the `update` class attribute to false:

```python title="extensions/context.py"
from copier_templates_extensions import ContextHook


class ContextUpdater(ContextHook):
    update = False

    def hook(self, context):
        flavor = context["flavor"]  # user's answer to the "flavor" question

        context["isDocker"] = flavor == "docker"
        context["isK8s"] = flavor == "kubernetes"
        context["isInstances"] = flavor == "instances"
        context["isLite"] = flavor == "none"

        context["isNotDocker"] = flavor != "docker"
        context["isNotK8s"] = flavor != "kubernetes"
        context["isNotInstances"] = flavor != "instances"
        context["isNotLite"] = flavor != "none"

        context["hasContainers"] = context["isDocker"] or context["isK8s"]

        # you can now actually remove items from the context
        del context["flavor"]
```

Now you can use these added variables in your Jinja templates, and in files and folders
names!

## Why Copier consumes a lot of resources?

If the repository containing the template is a shallow clone, the git process called by
Copier might consume unusually high resources. To avoid that, use a fully-cloned
repository.

## While developing, why the template doesn't include dirty changes?

Copier follows [a specific algorithm][templates-versions] to choose what reference to
use from the template. It also [includes dirty changes in the `HEAD` ref while
developing locally][copying-dirty-changes].

However, did you make sure you are selecting the `HEAD` ref for copying?

Imagine this is the status of your dirty template in `./src`:

```shell
$ git -C ./src status --porcelain=v1
?? new-file.txt

$ git -C ./src tag
v1.0.0
v2.0.0
```

Now, if you copy that template into a folder like this:

```shell
$ copier copy ./src ./dst
```

... you'll notice there's no `new-file.txt`. Why?

Well, Copier indeed included that into the `HEAD` ref. However, it still selected
`v2.0.0` as the ref to copy, because that's what Copier does.

However, if you do this:

```shell
$ copier copy -r HEAD ./src ./dst
```

... then you'll notice `new-file.txt` does exist. You passed a specific ref to copy, so
Copier skips its autodetection and just goes for the `HEAD` you already chose.
