"""Tools related to template management."""
from contextlib import suppress
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Set, Tuple

from packaging import version
from packaging.version import parse
from plumbum.cmd import git
from plumbum.machines import local
from pydantic.dataclasses import dataclass

from .errors import UnsupportedVersionError
from .types import AnyByStrDict, OptStr, StrSeq, VCSTypes
from .user_data import load_config_data
from .vcs import checkout_latest_tag, clone, get_repo

try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property

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

DEFAULT_TEMPLATES_SUFFIX = ".tmpl"


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


def verify_minimum_version(version_str: str) -> None:
    """Raise an error if the current Copier version is less than the given version."""
    # Importing __version__ at the top of the module creates a circular import
    # ("cannot import name '__version__' from partially initialized module 'copier'"),
    # so instead we do a lazy import here
    from . import __version__

    # Disable check when running copier as editable installation
    if __version__ == "0.0.0":
        return

    if version.parse(__version__) < version.parse(version_str):
        raise UnsupportedVersionError(
            f"This template requires Copier version >= {version_str}, "
            f"while your version of Copier is {__version__}."
        )


@dataclass
class Template:
    url: str
    ref: OptStr = None
    use_prereleases: bool = False

    @cached_property
    def _raw_config(self) -> AnyByStrDict:
        result = load_config_data(self.local_abspath)
        with suppress(KeyError):
            verify_minimum_version(result["_min_copier_version"])
        return result

    @cached_property
    def answers_relpath(self) -> Path:
        result = Path(self.config_data.get("answers_file", ".copier-answers.yml"))
        assert not result.is_absolute()
        return result

    @cached_property
    def commit(self) -> OptStr:
        if self.vcs == "git":
            with local.cwd(self.local_abspath):
                return git("describe", "--tags", "--always").strip()

    @cached_property
    def config_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[0]

    @cached_property
    def default_answers(self) -> AnyByStrDict:
        return {key: value.get("default") for key, value in self.questions_data.items()}

    @cached_property
    def envops(self) -> Mapping:
        # TODO Use Jinja defaults
        result = {
            "autoescape": False,
            "block_end_string": "%]",
            "block_start_string": "[%",
            "comment_end_string": "#]",
            "comment_start_string": "[#",
            "keep_trailing_newline": True,
            "variable_end_string": "]]",
            "variable_start_string": "[[",
        }
        result.update(self.config_data.get("envops", {}))
        return result

    @cached_property
    def exclude(self) -> Tuple[str, ...]:
        return tuple(self.config_data.get("exclude", DEFAULT_EXCLUDE))

    @cached_property
    def metadata(self) -> AnyByStrDict:
        result: AnyByStrDict = {"_src_path": self.url}
        if self.commit:
            result["_commit"] = self.commit
        return result

    def migration_tasks(self, stage: str, from_: str, to: str) -> Sequence[Mapping]:
        """Get migration objects that match current version spec.

        Versions are compared using PEP 440.
        """
        result: List[dict] = []
        if not from_ or not to:
            return result
        parsed_from = parse(from_)
        parsed_to = parse(to)
        extra_env = {
            "STAGE": stage,
            "VERSION_FROM": from_,
            "VERSION_TO": to,
        }
        migration: dict
        for migration in self._raw_config.get("_migrations", []):
            if parsed_to >= parse(migration["version"]) > parsed_from:
                extra_env = dict(extra_env, VERSION_CURRENT=str(migration["version"]))
                result += [
                    {"task": task, "extra_env": extra_env}
                    for task in migration.get(stage, [])
                ]
        return result

    @cached_property
    def questions_data(self) -> AnyByStrDict:
        return filter_config(self._raw_config)[1]

    @cached_property
    def secret_questions(self) -> Set[str]:
        result = set(self.config_data.get("secret_questions", {}))
        for key, value in self.questions_data.items():
            if value.get("secret"):
                result.add(key)
        return result

    @cached_property
    def skip_if_exists(self) -> StrSeq:
        return self.config_data.get("skip_if_exists", ())

    @cached_property
    def subdirectory(self) -> str:
        return self.config_data.get("subdirectory", "")

    @cached_property
    def tasks(self) -> Sequence:
        return self.config_data.get("tasks", [])

    @cached_property
    def templates_suffix(self) -> str:
        return self.config_data.get("templates_suffix", DEFAULT_TEMPLATES_SUFFIX)

    @cached_property
    def local_abspath(self) -> Path:
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
        return get_repo(self.url) or self.url

    @cached_property
    def vcs(self) -> Optional[VCSTypes]:
        if get_repo(self.url):
            return "git"
