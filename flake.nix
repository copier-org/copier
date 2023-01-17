{
  inputs = {
    devenv.url = "github:cachix/devenv/v0.5";
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
    flake-utils.url = github:numtide/flake-utils;
    nixpkgs.url = github:NixOS/nixpkgs/nixos-22.11;
    poetry2nix.url = github:nix-community/poetry2nix;
  };

  outputs = inputs:
    with inputs;
      flake-utils.lib.eachDefaultSystem (system: let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [poetry2nix.overlay];
        };
        lastRelease = (pkgs.lib.importTOML ./.cz.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+nix-git-${self.sourceInfo.shortRev or "dirty"}";

        # Builders
        copierApp = pkgs.poetry2nix.mkPoetryApplication {
          inherit version;
          name = "copier-${version}";
          POETRY_DYNAMIC_VERSIONING_BYPASS = version;
          projectDir = ./.;
          overrides = pkgs.poetry2nix.overrides.withDefaults (final: prev: {
            pydantic = prev.pydantic.overrideAttrs (old: {
              buildInputs = old.buildInputs ++ [pkgs.libxcrypt];
            });
          });

          # Test configuration
          checkInputs = [pkgs.git];
          pythonImportsCheck = ["copier"];
          doCheck = true;
          installCheckPhase = ''
            patchShebangs tests
            env \
              GIT_AUTHOR_EMAIL=copier@example.com \
              GIT_AUTHOR_NAME=copier \
              GIT_COMMITTER_EMAIL=copier@example.com \
              GIT_COMMITTER_NAME=copier \
              PATH=$out/bin:$PATH \
              POETRY_VIRTUALENVS_PATH=$NIX_BUILD_TOP/virtualenvs \
              PYTHONOPTIMIZE= \
              pytest -m 'not impure'
          '';
        };
        copierModule = pkgs.python3.pkgs.toPythonModule copierApp;
      in rec {
        devShells.default = devenv.lib.mkShell {
          inherit inputs pkgs;
          modules = [
            {
              packages = with pkgs; [
                # Essential dev tools
                (pkgs.python3.withPackages (ps:
                  with ps; [
                    poetry
                    poetry-dynamic-versioning
                  ]))

                # IDE integration tools
                alejandra
                black
                commitizen
                isort
                mypy
                nodePackages.prettier
              ];
              difftastic.enable = true;
              pre-commit.hooks = {
                alejandra.enable = true;
                black.enable = true;
                commitizen.enable = true;
                editorconfig-checker.enable = true;
                editorconfig-checker.excludes = [
                  "\.md$"
                  "\.noeof\."
                  "\.bundle$"
                ];
                flake8.enable = true;
                isort.enable = true;
                prettier.enable = true;
                prettier.excludes = [
                  # Those files have wrong syntax and would fail
                  "^tests/demo_invalid/copier.yml$"
                  "^tests/demo_transclude_invalid(_multi)?/demo/copier.yml$"
                  # HACK https://github.com/prettier/prettier/issues/9430
                  "^tests/demo"
                ];
              };
            }
          ];
        };
        packages.default = copierModule;
        apps =
          builtins.mapAttrs
          (name: value: flake-utils.lib.mkApp {drv = value;})
          packages;
        checks =
          packages
          // {
            devenv-ci = devShells.default.ci;
          };
      });
}
