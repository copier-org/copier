"""Development helper tasks."""

import logging
from pathlib import Path

from plumbum import TEE, CommandNotFound, ProcessExecutionError, local

_logger = logging.getLogger(__name__)
HERE = Path(__file__).parent


def dev_setup() -> None:
    """Set up a development environment."""
    with local.cwd(HERE):
        local["direnv"]("allow")
        local["uv"]("sync", "--frozen")


def lint() -> None:
    """Lint and format the project."""
    args = [
        "--extra-experimental-features",
        "nix-command flakes",
        "--accept-flake-config",
        "develop",
        "--impure",
        HERE,
        "--command",
        "pre-commit",
        "run",
        "--color=always",
        "--all-files",
    ]
    try:
        local["nix"].with_cwd(HERE)[args] & TEE
    except CommandNotFound:
        _logger.warning("Nix not found; fallback to a container")
        runner = local.get("podman", "docker")
        try:
            (
                runner[
                    "container",
                    "create",
                    "--name=copier-lint-v1",
                    f"--volume={HERE}:{HERE}:rw,z",
                    f"--workdir={HERE}",
                    "docker.io/nixos/nix",
                    "nix",
                    args,
                ]
                & TEE
            )
        except ProcessExecutionError:
            _logger.info(
                "Couldn't create copier-lint-v1 container, probably because a previous one exists. "
                "Remove it if you want to recycle it. Otherwise, this is OK."
            )
        runner["container", "start", "--attach", "copier-lint-v1"] & TEE
    except ProcessExecutionError as error:
        raise SystemExit(error.errno)
