"""Tools related to template management."""
import re
import sys
from collections import ChainMap
from contextlib import suppress
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Set, Tuple
from warnings import warn

import dunamai
import yaml
from iteration_utilities import deepflatten
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass
from yamlinclude import YamlIncludeConstructor

from .errors import (
    InvalidConfigFileError,
    MultipleConfigFilesError,
    OldTemplateWarning,
    UnknownCopierVersionWarning,
    UnsupportedVersionError,
)
from .tools import copier_version
from .types import AnyByStrDict, OptStr, StrSeq, VCSTypes
from .vcs import checkout_latest_tag, clone, get_repo

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property

from .types import Literal

# Default list of files in the template to exclude from the rendered project
DEFAULT_EXCLUDE: Tuple[str, ...] = (
    "copier.yaml",
    "copier.yml",
    "~*",
    "*.py[co]",
    "__pycache__",
    ".git",
    ".DS_Store",
    ".svn",
)

DEFAULT_TEMPLATES_SUFFIX = ".jinja"

# TODO Remove usage of this on Copier v7
COPIER_JINJA_BREAK = SpecifierSet("<=6.0.0a5", prereleases=True)


def filter_config(data: AnyByStrDict) -> Tuple[AnyByStrDict, AnyByStrDict]:
    """Separates config and questions data."""
    conf_data: AnyByStrDict = {"secret_questions": set()}
    questions_data = {}
    for k, v in data.items():
        if k == "_secret_questions":
            conf_data["secret_questions"].update(v)
        elif k.startswith("_"):
            conf_data[k[1:]] = v
        else:
            # Transform simplified questions format into complex
            if not isinstance(v, dict):
                v = {"default": v}
            questions_data[k] = v
            if v.get("secret"):
                conf_data["secret_questions"].add(k)
    return conf_data, questions_data


def load_template_config(conf_path: Path, quiet: bool = False) -> AnyByStrDict:
    """Load the `copier.yml` file.

    This is like a simple YAML load, but applying all specific quirks needed
    for [the `copier.yml` file][the-copieryml-file].

    For example, it supports the `!include` tag with glob includes, and
    merges multiple sections.

    Params:
        conf_path: The path to the `copier.yml` file.
        quiet: Used to configure the exception.

    Raises:
        InvalidConfigFileError: When the file is formatted badly.
    """
    YamlIncludeConstructor.add_to_loader_class(
        loader_class=yaml.FullLoader, base_dir=conf_path.parent
    )

    try:
        with open(conf_path) as f:
            flattened_result = deepflatten(
                yaml.load_all(f, Loader=yaml.FullLoader),
                depth=2,
                types=(list,),
            )
            return dict(ChainMap(*reversed(list(flattened_result))))
    except yaml.parser.ParserError as e:
        raise InvalidConfigFileError(conf_path, quiet) from e


def verify_copier_version(version_str: str) -> None:
    """Raise an error if the current Copier version is less than the given version.

    Args:
        version_str:
            Minimal copier version for the template.
    """
    installed_version = copier_version()

    # Disable check when running copier as editable installation
    if installed_version == Version("0.0.0"):
        warn(
            "Cannot check Copier version constraint.",
            UnknownCopierVersionWarning,
        )
        return
    parsed_min = Version(version_str)
    if installed_version < parsed_min:
        raise UnsupportedVersionError(
            f"This template requires Copier version >= {version_str}, "
            f"while your version of Copier is {installed_version}."
        )
    if installed_version.major > parsed_min.major:
        warn(
            f"This template was designed for Copier {version_str}, "
            f"but your version of Copier is {installed_version}. "
            f"You could find some incompatibilities.",
            OldTemplateWarning,
        )


@dataclass
class Template:
    """Object that represents a template and its current state.

    See [configuring a template][configuring-a-template].

    Attributes:
        url:
            Absolute origin that points to the template.

            It can be:

            - A local path.
            - A Git url. Note: if something fails, prefix the URL with `git+`.

        ref:
            The tag to checkout in the template.

            Only used if `url` points to a VCS-tracked template.

            If `None`, then it will checkout the latest tag, sorted by PEP440.
            Otherwise it will checkout the reference used here.

            Usually it should be a tag, or `None`.

        use_prereleases:
            When `True`, the template's *latest* release will consider prereleases.

            Only used if:

            - `url` points to a VCS-tracked template
            - `ref` is `None`.

            Helpful if you want to test templates before doing a proper release, but you
            need some features that require a proper PEP440 version identifier.
    """

    url: str
    ref: OptStr = None
    use_prereleases: bool = False

    @cached_property
    def _raw_config(self) -> AnyByStrDict:
        """Get template configuration, raw.

        It reads [the `copier.yml` file][the-copieryml-file].
        """
        conf_paths = [
            p
            for p in self.local_abspath.glob("copier.*")
            if p.is_file() and re.match(r"\.ya?ml", p.suffix, re.I)
        ]
        if len(conf_paths) > 1:
            raise MultipleConfigFilesError(conf_paths)
        elif len(conf_paths) == 1:
            return load_template_config(conf_paths[0])
        return {}

    @cached_property
    def answers_relpath(self) -> Path:
        """Get the answers file relative path, as specified in the template.

        If not specified, returns the default `.copier-answers.yml`.

        See [answers_file][].
        """
        result = Path(self.config_data.get("answers_file", ".copier-answers.yml"))
        assert not result.is_absolute()
        return result

    @cached_property
    def commit(self) -> OptStr:
        """If the template is VCS-tracked, get its commit description."""
        if self.vcs == "git":
            with local.cwd(self.local_abspath):
                return git("describe", "--tags", "--always").strip()

    @cached_property
    def config_data(self) -> AnyByStrDict:
        """Get config from the template.

        It reads [the `copier.yml` file][the-copieryml-file] to get its
        [settings][available-settings].
        """
        result = filter_config(self._raw_config)[0]
        with suppress(KeyError):
            verify_copier_version(result["min_copier_version"])
        return result

    @cached_property
    def default_answers(self) -> AnyByStrDict:
        """Get default answers for template's questions."""
        return {key: value.get("default") for key, value in self.questions_data.items()}

    @cached_property
    def envops(self) -> Mapping:
        """Get the Jinja configuration specified in the template, or default values.

        See [envops][].
        """
        result = self.config_data.get("envops", {})
        if "keep_trailing_newline" not in result:
            # NOTE: we want to keep trailing newlines in templates as this is what a
            #       user will most likely expects as a default.
            #       See https://github.com/copier-org/copier/issues/464
            result["keep_trailing_newline"] = True

        # TODO Copier v7+ will not use any of these altered defaults
        old_defaults = {
            "autoescape": False,
            "block_end_string": "%]",
            "block_start_string": "[%",
            "comment_end_string": "#]",
            "comment_start_string": "[#",
            "keep_trailing_newline": True,
            "variable_end_string": "]]",
            "variable_start_string": "[[",
        }
        if self.min_copier_version and self.min_copier_version in COPIER_JINJA_BREAK:
            warned = False
            for key, value in old_defaults.items():
                if key not in result:
                    if not warned:
                        warn(
                            "On future releases, Copier will switch to standard Jinja "
                            "defaults and this template will not work unless updated.",
                            FutureWarning,
                        )
                        warned = True
                    result[key] = value
        return result

    @cached_property
    def exclude(self) -> Tuple[str, ...]:
        """Get exclusions specified in the template, or default ones.

        See [exclude][].
        """
        return tuple(self.config_data.get("exclude", DEFAULT_EXCLUDE))

    @cached_property
    def jinja_extensions(self) -> Tuple[str, ...]:
        """Get Jinja2 extensions specified in the template, or `()`.

        See [jinja_extensions][].
        """
        return tuple(self.config_data.get("jinja_extensions", ()))

    @cached_property
    def metadata(self) -> AnyByStrDict:
        """Get template metadata.

        This data, if any, should be saved in the answers file to be able to
        restore the template to this same state.
        """
        result: AnyByStrDict = {"_src_path": self.url}
        if self.commit:
            result["_commit"] = self.commit
        return result

    def migration_tasks(
        self, stage: Literal["task", "before", "after"], from_template: "Template"
    ) -> Sequence[Mapping]:
        """Get migration objects that match current version spec.

        Versions are compared using PEP 440.

        See [migrations][].

        Args:
            stage: A valid stage name to find tasks for.
            from_template: Original template, from which we are migrating.
        """
        result: List[dict] = []
        if not (self.version and from_template.version):
            return result
        extra_env = {
            "STAGE": stage,
            "VERSION_FROM": str(from_template.commit),
            "VERSION_TO": str(self.commit),
            "VERSION_PEP440_FROM": str(from_template.version),
            "VERSION_PEP440_TO": str(self.version),
        }
        migration: dict
        for migration in self._raw_config.get("_migrations", []):
            current = parse(migration["version"])
            if self.version >= current > from_template.version:
                extra_env = dict(
                    extra_env,
                    VERSION_CURRENT=migration["version"],
                    VERSION_PEP440_CURRENT=str(current),
                )
                result += [
                    {"task": task, "extra_env": extra_env}
                    for task in migration.get(stage, [])
                ]
        return result

    @cached_property
    def min_copier_version(self) -> Optional[Version]:
        """Gets minimal copier version for the template and validates it.

        See [min_copier_version][].
        """
        try:
            return Version(self.config_data["min_copier_version"])
        except KeyError:
            return None

    @cached_property
    def questions_data(self) -> AnyByStrDict:
        """Get questions from the template.

        See [questions][].
        """
        return filter_config(self._raw_config)[1]

    @cached_property
    def secret_questions(self) -> Set[str]:
        """Get names of secret questions from the template.

        These questions shouldn't be saved into the answers file.
        """
        result = set(self.config_data.get("secret_questions", {}))
        for key, value in self.questions_data.items():
            if value.get("secret"):
                result.add(key)
        return result

    @cached_property
    def skip_if_exists(self) -> StrSeq:
        """Get skip patterns from the template.

        These files will never be rewritten when rendering the template.

        See [skip_if_exists][].
        """
        return self.config_data.get("skip_if_exists", ())

    @cached_property
    def subdirectory(self) -> str:
        """Get the subdirectory as specified in the template.

        The subdirectory points to the real template code, allowing the
        templater to separate it from other template assets, such as docs,
        tests, etc.

        See [subdirectory][].
        """
        return self.config_data.get("subdirectory", "")

    @cached_property
    def tasks(self) -> Sequence:
        """Get tasks defined in the template.

        See [tasks][].
        """
        return self.config_data.get("tasks", [])

    @cached_property
    def templates_suffix(self) -> str:
        """Get the suffix defined for templates.

        By default: `.jinja`.

        See [templates_suffix][].
        """
        result = self.config_data.get("templates_suffix")
        if result is None:
            # TODO Delete support for .tmpl default in Copier 7
            if (
                self.min_copier_version
                and self.min_copier_version in COPIER_JINJA_BREAK
            ):
                warn(
                    "In future Copier releases, the default value for template suffix "
                    "will change from .tmpl to .jinja, and this template will "
                    "fail unless updated.",
                    FutureWarning,
                )
                return ".tmpl"
            return DEFAULT_TEMPLATES_SUFFIX
        return result

    @cached_property
    def local_abspath(self) -> Path:
        """Get the absolute path to the template on disk.

        This may clone it if `url` points to a VCS-tracked template.
        Dirty changes for local VCS-tracked templates will be copied.
        """
        result = Path(self.url)
        if self.vcs == "git":
            result = Path(clone(self.url_expanded, self.ref))
            if self.ref is None:
                checkout_latest_tag(result, self.use_prereleases)
        if not result.is_dir():
            raise ValueError("Local template must be a directory.")
        return result.absolute()

    @cached_property
    def url_expanded(self) -> str:
        """Get usable URL.

        `url` can be specified in shortcut
        format, which wouldn't be understood by the underlying VCS system. This
        property returns the expanded version, which should work properly.
        """
        return get_repo(self.url) or self.url

    @cached_property
    def version(self) -> Optional[Version]:
        """PEP440-compliant version object."""
        if self.vcs != "git" or not self.commit:
            return None
        try:
            with local.cwd(self.local_abspath):
                # Leverage dunamai by default; usually it gets best results
                return Version(
                    dunamai.Version.from_git().serialize(style=dunamai.Style.Pep440)
                )
        except ValueError:
            # A fully descripted commit can be easily detected converted into a
            # PEP440 version, because it has the format "<tag>-<count>-g<hash>"
            if re.match(r"^.+-\d+-g\w+$", self.commit):
                base, count, git_hash = self.commit.rsplit("-", 2)
                return Version(f"{base}.post{count}+{git_hash}")
        # If we get here, the commit string is a tag, so we can safely expect
        # it's a valid PEP440 version
        return Version(self.commit)

    @cached_property
    def vcs(self) -> Optional[VCSTypes]:
        """Get VCS system used by the template, if any."""
        if get_repo(self.url):
            return "git"
