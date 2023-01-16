{
  inputs = {
    devenv.url = "github:cachix/devenv";
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
            extras = [];
            overrides = pkgs.poetry2nix.overrides.withDefaults (final: prev: {
              # HACK https://github.com/nix-community/poetry2nix/pull/943
              plumbum = prev.plumbum.overrideAttrs (old: {
                buildInputs = old.buildInputs ++ [final.hatchling final.hatch-vcs];
              });
            });
          };
        mkCopierModule = py: pkgs.${py}.pkgs.toPythonModule (mkCopierApp py);
      in rec {
        devShells =
          pkgs.lib.genAttrs pythons (py:
            devenv.lib.mkShell {
              inherit inputs pkgs;
              modules = [
                {
                  # Essential dev tools
                  packages = [
                    (pkgs.${py}.withPackages (ps:
                      with ps; [
                        poetry
                        poetry-dynamic-versioning
                      ]))
                  ];
                  difftastic.enable = true;
                  devcontainer.enable = true;
                  pre-commit.hooks = {
                    alejandra.enable = true;
                    black.enable = true;
                    commitizen.enable = true;
                    editorconfig-checker.enable = true;
                    flake8.enable = true;
                    isort.enable = true;
                    prettier.enable = true;
                  };
                }
              ];
            })
          // {default = devShells.${pythonLast};};
        packages =
          pkgs.lib.genAttrs pythons mkCopierModule
          # FIXME Fix python 3.11 build and make it default (using pythonLast)
          // {default = packages.python310;};
      });
}
