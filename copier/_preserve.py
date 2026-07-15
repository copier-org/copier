"""Preserve user-owned regions across ``copier update``.

Templates often ship files with dummy content or ``TODO`` markers that the
developer is expected to replace right after generating a project. On a later
``copier update``, Copier's 3-way merge treats those regions like any other
template-owned content, so a change to the placeholder in the template can
clobber the developer's implementation (or raise a needless merge conflict).

This module lets a template author wrap such a region in a pair of *preserve
markers*. Everything **between** the markers becomes developer-owned: its
content is captured from the existing project before an update and written
back into every intermediate render, so the merge sees identical content on
all sides and leaves the developer's version untouched. The marker lines
themselves, and everything around them, keep updating from the template as
usual.

A marker is any line that *contains* the sentinel token, so it works
regardless of the host language's comment syntax::

    # copier:preserve:start greeting
    def greeting() -> str:
        return "Hello from the developer!"
    # copier:preserve:end greeting

The optional identifier after the token (``greeting`` above) lets Copier match
a region to its counterpart even if the region moves within the file between
template versions. Unidentified regions are matched by their order of
appearance instead.

See the ``updating.md`` documentation for the user-facing description.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "PRESERVE_END_TOKEN",
    "PRESERVE_START_TOKEN",
    "capture_preserved_regions",
    "find_marker_files",
    "restore_preserved_regions",
]

#: Sentinel token opening a preserved region.
PRESERVE_START_TOKEN = "copier:preserve:start"
#: Sentinel token closing a preserved region.
PRESERVE_END_TOKEN = "copier:preserve:end"

# The identifier (if any) follows the token after a ``:`` or whitespace and
# runs until the next whitespace, so it can be embedded in a comment.
_START_RE = re.compile(re.escape(PRESERVE_START_TOKEN) + r"(?:[:\s]+(?P<id>\S+))?")
_END_RE = re.compile(re.escape(PRESERVE_END_TOKEN) + r"(?:[:\s]+(?P<id>\S+))?")


class PreserveMarkerError(ValueError):
    """Raised when preserve markers in a file are unbalanced or nested."""


@dataclass(frozen=True)
class _Region:
    """A single preserved region parsed from a file."""

    identifier: str | None
    body: str
    start_line: int  # index of the start-marker line
    end_line: int  # index of the end-marker line


# A hashable key that maps a region to its counterpart in another render.
_RegionKey = str | tuple[str, int]


def _parse_regions(text: str) -> list[_Region]:
    """Parse all preserved regions from ``text``.

    Raises:
        PreserveMarkerError: If a start marker is nested inside another, or a
            start/end marker has no matching counterpart.
    """
    lines = text.splitlines(keepends=True)
    regions: list[_Region] = []
    open_identifier: str | None = None
    open_start: int | None = None
    open_body: list[str] = []
    for idx, line in enumerate(lines):
        if (match := _START_RE.search(line)) is not None:
            if open_start is not None:
                raise PreserveMarkerError(
                    f"nested preserve start marker at line {idx + 1}"
                )
            open_identifier = match.group("id")
            open_start = idx
            open_body = []
        elif _END_RE.search(line) is not None:
            if open_start is None:
                raise PreserveMarkerError(
                    f"preserve end marker without matching start at line {idx + 1}"
                )
            regions.append(
                _Region(
                    identifier=open_identifier,
                    body="".join(open_body),
                    start_line=open_start,
                    end_line=idx,
                )
            )
            open_start = None
            open_identifier = None
            open_body = []
        elif open_start is not None:
            open_body.append(line)
    if open_start is not None:
        raise PreserveMarkerError(
            f"preserve start marker at line {open_start + 1} is never closed"
        )
    return regions


def _keyed_regions(regions: list[_Region]) -> list[tuple[_RegionKey, _Region]]:
    """Pair each region with a key used to match it across renders.

    Named regions are keyed by their identifier; unnamed regions are keyed by
    their positional index among the unnamed regions.
    """
    keyed: list[tuple[_RegionKey, _Region]] = []
    anonymous_index = 0
    for region in regions:
        if region.identifier is not None:
            keyed.append((region.identifier, region))
        else:
            keyed.append((("", anonymous_index), region))
            anonymous_index += 1
    return keyed


def _read_text(path: Path) -> str | None:
    """Read ``path`` as UTF-8 text, or return ``None`` if that's not possible."""
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def find_marker_files(root: Path) -> set[Path]:
    """Return the paths (relative to ``root``) of files with preserve markers.

    Only regular, UTF-8-decodable files that contain the start token are
    returned; the ``.git`` directory is skipped. This is meant to be run
    against a *template render*, which bounds the scan to template-managed
    files instead of the whole (potentially huge) project tree.
    """
    found: set[Path] = set()
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        text = _read_text(path)
        if text is not None and PRESERVE_START_TOKEN in text:
            found.add(path.relative_to(root))
    return found


def capture_preserved_regions(
    root: Path, relpaths: Iterable[Path] | None = None
) -> dict[Path, dict[_RegionKey, str]]:
    """Capture the content of preserved regions under ``root``.

    Args:
        root: Directory holding the files to read (typically the existing
            project).
        relpaths: The candidate files to inspect, relative to ``root``. When
            ``None``, ``root`` is scanned recursively; callers that already
            know the template-managed files (see :func:`find_marker_files`)
            should pass them to avoid walking unrelated project content.

    Returns:
        A mapping from each file's path (relative to ``root``) to a mapping of
        region key to the region's current body. Only files that contain at
        least one well-formed preserved region are included. Files with
        malformed markers are skipped so they never break an update.
    """
    if relpaths is None:
        relpaths = find_marker_files(root)
    captured: dict[Path, dict[_RegionKey, str]] = {}
    for relpath in relpaths:
        text = _read_text(root / relpath)
        if text is None or PRESERVE_START_TOKEN not in text:
            continue
        try:
            regions = _parse_regions(text)
        except PreserveMarkerError:
            continue
        if regions:
            captured[relpath] = {
                key: region.body for key, region in _keyed_regions(regions)
            }
    return captured


def _apply_regions(text: str, bodies: dict[_RegionKey, str]) -> str:
    """Return ``text`` with each matching region body replaced from ``bodies``."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    cursor = 0
    for key, region in _keyed_regions(_parse_regions(text)):
        if key not in bodies:
            continue
        # Emit everything up to and including the start-marker line, then the
        # captured body, and resume from the end-marker line so the (possibly
        # updated) marker lines themselves are preserved from the template.
        result.extend(lines[cursor : region.start_line + 1])
        result.append(bodies[key])
        cursor = region.end_line
    result.extend(lines[cursor:])
    return "".join(result)


def restore_preserved_regions(
    root: Path, captured: dict[Path, dict[_RegionKey, str]]
) -> None:
    """Write captured region bodies back into the matching files under ``root``.

    Files, or individual regions, that are missing from a given render are left
    as-is, so brand-new regions introduced by the template still appear. Files
    with malformed markers are skipped.

    Args:
        root: Directory whose files should receive the captured content.
        captured: The mapping returned by :func:`capture_preserved_regions`.
    """
    for relpath, bodies in captured.items():
        target = root / relpath
        text = _read_text(target)
        if text is None or PRESERVE_START_TOKEN not in text:
            continue
        try:
            new_text = _apply_regions(text, bodies)
        except PreserveMarkerError:
            continue
        if new_text != text:
            target.write_text(new_text, encoding="utf-8")
