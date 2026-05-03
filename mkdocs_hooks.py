"""MkDocs plugin hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page


def on_page_markdown(
    markdown: str,
    page: Page,  # noqa: ARG001
    config: MkDocsConfig,  # noqa: ARG001
    files: Files,  # noqa: ARG001
) -> str | None:
    """Modify markdown content before it's converted to HTML."""
    # Rewrite links from `CHANGELOG.md` to `changelog.md` to match the filename of the
    # MkDocs page.
    return markdown.replace("CHANGELOG.md)", "changelog.md)")
