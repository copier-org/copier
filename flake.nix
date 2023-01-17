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
        pythons = [
          "python37"
          "python38"
          "python39"
          "python310"
          "python311"
        ];
        pythonLast = pkgs.lib.last pythons;
        lastRelease = (pkgs.lib.importTOML ./.cz.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+nix-git-${self.sourceInfo.shortRev or "dirty"}";

        # Builders
        mkCopierApp = py:
          pkgs.poetry2nix.mkPoetryApplication {
            inherit version;
            name = "copier-${version}";
            POETRY_DYNAMIC_VERSIONING_BYPASS = version;
            projectDir = ./.;
            python = pkgs.${py};
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
                POETRY_VIRTUALENVS_PATH=$NIX_BUILD_TOP/virtualenvs \
                PATH=$out/bin:$PATH \
                GIT_AUTHOR_NAME=copier \
                GIT_AUTHOR_EMAIL=copier@example.com \
                GIT_COMMITTER_NAME=copier \
                GIT_COMMITTER_EMAIL=copier@example.com \
                pytest -m 'not impure'
            '';
          };
        mkCopierModule = py: pkgs.${py}.pkgs.toPythonModule (mkCopierApp py);
      in rec {
        devShells =
          pkgs.lib.genAttrs pythons (py:
            devenv.lib.mkShell {
              inherit inputs pkgs;
              modules = [
                # Python version-specific interpreter
                {packages = [pkgs.${py}];}
                # Extra tools, always the same
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
            })
          // {default = devShells.${pythonLast};};
        packages =
          pkgs.lib.genAttrs pythons mkCopierModule
          # FIXME Fix python 3.11 build and make it default (using pythonLast)
          // {default = packages.python310;};
        apps =
          builtins.mapAttrs
          (name: value: flake-utils.lib.mkApp {drv = value;})
          packages;
      });
}
