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
  };
  inputs = {
    devenv.url = "github:cachix/devenv/v0.5";
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
    flake-utils.url = github:numtide/flake-utils;
    nixpkgs.url = github:NixOS/nixpkgs;
    poetry2nix.url = github:nix-community/poetry2nix;
  };

  outputs = inputs:
    with inputs;
      flake-utils.lib.eachDefaultSystem (system: let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [poetry2nix.overlay];
        };
        lastRelease = (pkgs.lib.importTOML ./pyproject.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+nix-git-${self.sourceInfo.shortRev or "dirty"}";
        python = pkgs.python311;

        # Builders
        copierApp = pkgs.poetry2nix.mkPoetryApplication {
          inherit python version;
          name = "copier-${version}";
          POETRY_DYNAMIC_VERSIONING_BYPASS = version;
          projectDir = ./.;

          # Test configuration
          propagatedNativeBuildInputs = [pkgs.git];
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
              pytest --color=yes -m 'not impure'
          '';
        };
        copierModule = python.pkgs.toPythonModule copierApp;
      in rec {
        devShells.default = devenv.lib.mkShell {
          inherit inputs pkgs;
          modules = [
            {
              packages = with pkgs; [
                # Essential dev tools
                poetry
                python

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
