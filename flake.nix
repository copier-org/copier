{
  inputs = {
    devshell.url = github:numtide/devshell;
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
    flake-utils.url = github:numtide/flake-utils;
    nixpkgs.url = "github:NixOS/nixpkgs/refs/pull/200205/merge"; # HACK
    poetry2nix.url = github:nix-community/poetry2nix/refs/pull/807/merge; # HACK
  };

  outputs = inputs:
    with inputs;
      flake-utils.lib.eachSystem ["x86_64-linux"] (system: let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [devshell.overlay poetry2nix.overlay];
        };
        precommix = import ./precommix.nix;
        lastRelease = (pkgs.lib.importTOML ./.cz.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+git${self.sourceInfo.shortRev or "dirty"}";
      in {
        devShells.default = pkgs.devshell.mkShell {
          imports = [precommix.devshellModules.${system}.default];
          commands = [{package = pkgs.python3;}];
        };
        packages.default = pkgs.poetry2nix.mkPoetryApplication {
          inherit version;
          name = "copier-${version}";
          POETRY_DYNAMIC_VERSIONING_BYPASS = version;
          projectDir = ./.;
        };
      });
}
