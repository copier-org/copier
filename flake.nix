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
        system,
        ...
      }: {
        devenv.shells.default = {
          languages.python.enable = true;
          languages.python.package = pkgs.python311;
          languages.python.uv.enable = true;
          languages.python.uv.package = inputs'.nixpkgs-unstable.legacyPackages.uv;
          languages.python.uv.sync.enable = true;

          packages = [
            pkgs.alejandra
            pkgs.commitizen
            pkgs.mypy
            pkgs.nodePackages.prettier
            pkgs.ruff
            pkgs.taplo
          ];

          difftastic.enable = true;

          pre-commit.hooks = {
            alejandra.enable = true;
            commitizen.enable = true;
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
            ruff.enable = true;
            ruff-format.enable = true;
            taplo.enable = true;
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
