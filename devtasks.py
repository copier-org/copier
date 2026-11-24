"""Development helper tasks."""

import logging
from pathlib import Path

from plumbum import TEE, CommandNotFound, ProcessExecutionError, local

_logger = logging.getLogger(__name__)
HERE = Path(__file__).parent


def dev_setup() -> None:
    """Set up a development environment."""
    with local.cwd(HERE):
        local["mise"]("trust")
        local["mise"]("install")
        local["uv"]("sync", "--frozen")
        local["uv"]("run", "pre-commit", "install")


def lint() -> None:
    """Lint and format the project."""
    args = [
        "exec",
        "--",
        "uv",
        "run",
        "pre-commit",
        "run",
        "--color=always",
        "--all-files",
    ]
    try:
        local["mise"].with_cwd(HERE)[args] & TEE
    except CommandNotFound:
        _logger.warning("mise not found; fallback to a container")
        runner = local.get("podman", "docker")
        try:
            (
                runner[
                    "container",
                    "create",
                    "--name=copier-lint-v2",
                    f"--volume={HERE}:{HERE}:rw,z",
                    f"--workdir={HERE}",
                    "ghcr.io/jdx/mise:2026.11.12-debian",
                    "bash",
                    "-c",
                    'mise trust && mise install && exec mise "$@"',
                    "--",
                ][args]
                & TEE
            )
        except ProcessExecutionError:
            _logger.info(
                "Couldn't create copier-lint-v2 container, probably because a previous one exists. "
                "Remove it if you want to recycle it. Otherwise, this is OK."
            )
        runner["container", "start", "--attach", "copier-lint-v2"] & TEE
    except ProcessExecutionError as error:
        raise SystemExit(error.errno)
