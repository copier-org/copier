{
  inputs = {
    devshell.url = github:numtide/devshell;
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
    flake-utils.url = github:numtide/flake-utils;
    nixpkgs.url = "nixpkgs";
  };

  outputs = inputs:
    with inputs;
      flake-utils.lib.eachDefaultSystem (system: let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [devshell.overlay];
        };
        precommix = import ./precommix.nix;
      in {
        devShells.default = pkgs.devshell.mkShell {
          imports = [precommix.devshellModules.${system}.default];
        };
      });
}
