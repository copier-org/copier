"""Development helper tasks."""
import logging
import shutil
from pathlib import Path

from plumbum import TEE, CommandNotFound, ProcessExecutionError, local

_logger = logging.getLogger(__name__)
HERE = Path(__file__).parent


def clean():
    """Clean build, test or other process artifacts from the project workspace."""
    build_artefacts = (
        "build/",
        "dist/",
        "*.egg-info",
        "pip-wheel-metadata",
    )
    python_artefacts = (
        ".pytest_cache",
        "htmlcov",
        ".coverage",
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
    )
    project_dir = Path(".").resolve()
    for pattern in build_artefacts + python_artefacts:
        for matching_path in project_dir.glob(pattern):
            print(f"Deleting {matching_path}")
            if matching_path.is_dir():
                shutil.rmtree(matching_path)
            else:
                matching_path.unlink()


def dev_setup():
    """Set up a development environment."""
    with local.cwd(HERE):
        local["direnv"]("allow")
        local["poetry"]("install")


def lint(recycle_container=False):
    """Lint and format the project."""
    args = [
        "--extra-experimental-features",
        "nix-command flakes",
        "--extra-substituters",
        "https://copier.cachix.org https://devenv.cachix.org",
        "--extra-trusted-public-keys",
        "copier.cachix.org-1:sVkdQyyNXrgc53qXPCH9zuS91zpt5eBYcg7JQSmTBG4= devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=",
        "develop",
        "--impure",
        ".",
        "--command",
        "pre-commit",
        "run",
        "--color=always",
        "--all-files",
    ]
    try:
        local["nix"].with_cwd(HERE)[args] & TEE
    except CommandNotFound:
        _logger.warn("Nix not found; fallback to a container")
        runner = local.get("docker", "podman")
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
