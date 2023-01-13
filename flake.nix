{
  inputs = {
    devshell.url = github:numtide/devshell;
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
          overlays = [devshell.overlay poetry2nix.overlay];
        };
        precommix = import ./precommix.nix;
        pythons = [
          "python37"
          "python38"
          "python39"
          "python310"
          # "python311" # FIXME Make it work and enable it
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
            pkgs.devshell.mkShell {
              imports = [precommix.devshellModules.${system}.default];
              commands = [{package = py;}];
            })
          // {default = devShells.${pythonLast};};
        packages =
          pkgs.lib.genAttrs pythons mkCopierModule
          // {default = packages.${pythonLast};};
      });
}
