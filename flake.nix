{
  inputs = {
    devshell.url = github:numtide/devshell;
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
    flake-utils.url = github:numtide/flake-utils;
    nixpkgs.url = "github:NixOS/nixpkgs/refs/pull/200205/head"; # HACK
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
        pythons = ["python37" "python38" "python39" "python310" "python311"];
        lastRelease = (pkgs.lib.importTOML ./.cz.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+git${self.sourceInfo.shortRev or "dirty"}";
      in rec {
        devShells =
          pkgs.lib.genAttrs pythons (py:
            pkgs.devshell.mkShell {
              imports = [precommix.devshellModules.${system}.default];
              commands = [{package = py;}];
            })
          // {default = devShells.python311;};
        packages.default = pkgs.poetry2nix.mkPoetryApplication {
          inherit version;
          name = "copier-${version}";
          POETRY_DYNAMIC_VERSIONING_BYPASS = version;
          projectDir = ./.;
        };
      });
}
