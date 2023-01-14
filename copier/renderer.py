from collections import ChainMap
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

from jinja2 import Environment

from .subproject import Subproject
from .template import Template


@dataclass
class Renderer:
    template: Template
    subproject: Subproject
    _render_allowed: Callable
    pretend: bool
    jinja_env: Environment
    answers_relpath: Path
    _render_context: Mapping[str, Any]
    _items_key: Optional[str] = None
    _items_keys: Iterable[str] = field(default_factory=list)

    def render(self):
        dst_abspath = Path(self.subproject.local_abspath)
        if not self.pretend:
            dst_abspath.mkdir(parents=True, exist_ok=True)

        for file in self.template_copy_root.iterdir():
            if file.name in self._items_keys:
                continue
            if file.is_dir():
                self._render_folder(file)
            else:
                self._render_file(file)

    def _render_folder(self, src_abspath: Path) -> None:
        """Recursively render a folder.

        Args:
            src_abspath:
                Folder to be rendered. It must be an absolute path within
                the template.
        """
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self._render_path(src_relpath)
        if dst_relpath is None:
            return
        if not self._render_allowed(dst_relpath, is_dir=True):
            return
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        if not self.pretend:
            dst_abspath.mkdir(parents=True, exist_ok=True)
        for file in src_abspath.iterdir():
            if file.is_dir():
                self._render_folder(file)
            else:
                self._render_file(file)

    def _render_path(self, relpath: Path) -> Optional[Path]:
        """Render one relative path.

        Args:
            relpath:
                The relative path to be rendered. Obviously, it can be templated.
        """
        is_template = relpath.name.endswith(self.template.templates_suffix)
        templated_sibling = (
            self.template.local_abspath / f"{relpath}{self.template.templates_suffix}"
        )
        # With an empty suffix, the templated sibling always exists.
        if templated_sibling.exists() and self.template.templates_suffix:
            return None
        if self.template.templates_suffix and is_template:
            relpath = relpath.with_suffix("")
        rendered_parts = []
        for part in relpath.parts:
            # Skip folder if any part is rendered as an empty string
            part = self.render_string(part)
            if not part:
                return None
            # {{ _copier_conf.answers_file }} becomes the full path; in that case,
            # restore part to be just the end leaf
            if str(self.answers_relpath) == part:
                part = Path(part).name
            rendered_parts.append(part)
        result = Path(*rendered_parts)
        if not is_template:
            templated_sibling = (
                self.template.local_abspath
                / f"{result}{self.template.templates_suffix}"
            )
            if templated_sibling.exists():
                return None
        return result

    def _render_file(self, src_abspath: Path) -> None:
        """Render one file.

        Args:
            src_abspath:
                The absolute path to the file that will be rendered.
        """
        # TODO Get from main.render_file()
        assert src_abspath.is_absolute()
        src_relpath = src_abspath.relative_to(self.template.local_abspath).as_posix()
        src_renderpath = src_abspath.relative_to(self.template_copy_root)
        dst_relpath = self._render_path(src_renderpath)
        if dst_relpath is None:
            return
        if src_abspath.name.endswith(self.template.templates_suffix):
            try:
                tpl = self.jinja_env.get_template(src_relpath)
            except UnicodeDecodeError:
                if self.template.templates_suffix:
                    # suffix is not empty, re-raise
                    raise
                # suffix is empty, fallback to copy
                new_content = src_abspath.read_bytes()
            else:
                new_content = tpl.render(**self._render_context).encode()
        else:
            new_content = src_abspath.read_bytes()
        dst_abspath = Path(self.subproject.local_abspath, dst_relpath)
        src_mode = src_abspath.stat().st_mode
        if not self._render_allowed(dst_relpath, expected_contents=new_content):
            return
        if not self.pretend:
            dst_abspath.parent.mkdir(parents=True, exist_ok=True)
            dst_abspath.write_bytes(new_content)
            dst_abspath.chmod(src_mode)

    def render_string(self, string: str) -> str:
        """Render one templated string.

        Args:
            string:
                The template source string.
        """
        tpl = self.jinja_env.from_string(string)
        return tpl.render(**self._render_context)

    @cached_property
    def template_copy_root(self) -> Path:
        """Absolute path from where to start copying.

        It points to the cloned template local abspath + the rendered subdir, if any.
        """
        parts = [
            self.template.local_abspath,
        ]
        subdir = self.render_string(self.template.subdirectory)
        if subdir:
            parts.append(subdir)

        if self._items_key:
            parts.append(self._items_key)

        return Path(*parts)

    def with_item(self, items_key: str, items_value: Any) -> "Renderer":
        return Renderer(
            self.template,
            self.subproject,
            self._render_allowed,
            self.pretend,
            self.jinja_env,
            self.answers_relpath,
            ChainMap({"_item": items_value}, self._render_context),
            items_key,
            [],
        )
