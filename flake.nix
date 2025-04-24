{
  description = "Source code project lifecycle management tool";

  nixConfig = {
    # HACK https://github.com/NixOS/nix/issues/6771
    # TODO Leave only own cache settings when fixed
    extra-trusted-public-keys = [
      "copier.cachix.org-1:sVkdQyyNXrgc53qXPCH9zuS91zpt5eBYcg7JQSmTBG4="
      "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw="
    ];
    extra-substituters = [
      "https://copier.cachix.org"
      "https://devenv.cachix.org"
    ];

    # HACK https://github.com/renovatebot/renovate/issues/29721
    # TODO Remove these comments when fixed
    # github:NixOS/nixpkgs/nixpkgs-24.05
  };

  inputs = {
    devenv.url = "github:cachix/devenv";
    flake-compat.url = "https://flakehub.com/f/edolstra/flake-compat/1.*.tar.gz";
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/*.tar.gz";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = inputs @ {
    flake-parts,
    devenv,
    nixpkgs,
    nixpkgs-unstable,
    ...
  }:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.devenv.flakeModule
      ];
      systems = nixpkgs.lib.systems.flakeExposed;

      perSystem = {
        config,
        self',
        inputs',
        pkgs,
        lib,
        system,
        ...
      }: let
        python = pkgs.python311;
        uv = inputs'.nixpkgs-unstable.legacyPackages.uv;
      in {
        devenv.shells.default = {
          languages.python = {
            enable = true;
            package = python;

            uv = {
              enable = true;
              package = uv;
              sync.enable = true;
            };
          };

          env = {
            # Force uv to use nixpkgs' Python interpreter
            UV_PYTHON = python;
            # Prevent uv from managing Python downloads
            UV_PYTHON_DOWNLOADS = "never";
          };

          tasks = {
            # Patch binaries to make them runnable on NixOS
            # E.g.: https://github.com/astral-sh/ruff/issues/1699
            "venv:patchelf" = {
              exec = ''
                for exe in ruff taplo; do
                  ${lib.getExe pkgs.patchelf} --set-interpreter ${pkgs.stdenv.cc.bintools.dynamicLinker} $(uv run which $exe)
                done;
              '';
              after = ["devenv:python:uv"];
              before = ["devenv:enterShell"];
            };
          };

          packages = [
            pkgs.git
            pkgs.alejandra
            pkgs.nodePackages.prettier
          ];

          difftastic.enable = true;

          pre-commit.gitPackage = pkgs.git;
          pre-commit.hooks = {
            alejandra.enable = true;
            commitizen = {
              enable = true;
              package = null;
              entry = "uv run cz check --allow-abort --commit-msg-file";
            };
            editorconfig-checker.enable = true;
            editorconfig-checker.excludes = [
              "\.md$"
              "\.noeof\."
              "\.bundle$"
            ];
            prettier.enable = true;
            prettier.excludes = [
              # Some API reference identifiers are dotted paths involving
              # internal modules prefixed with `_` which are converted by
              # Prettier to `\_`, making them invalid.
              "^docs/reference/.+\.md$"
              # Those files have wrong syntax and would fail
              "^tests/demo_invalid/copier.yml$"
              "^tests/demo_transclude_invalid(_multi)?/demo/copier.yml$"
              # HACK https://github.com/prettier/prettier/issues/9430
              "^tests/demo"
            ];
            ruff = {
              enable = true;
              package = null;
              entry = "uv run ruff check --fix";
            };
            ruff-format = {
              enable = true;
              package = null;
              entry = "uv run ruff format";
            };
            taplo = {
              enable = true;
              package = null;
              entry = "uv run taplo fmt";
            };
          };

          enterTest = ''
            env \
              GIT_AUTHOR_EMAIL=copier@example.com \
              GIT_AUTHOR_NAME=copier \
              GIT_COMMITTER_EMAIL=copier@example.com \
              GIT_COMMITTER_NAME=copier \
              PYTHONOPTIMIZE= \
              uv run poe test
          '';
        };
      };
    };
}
