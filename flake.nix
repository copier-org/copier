{
  description = "A library for rendering project templates";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs";
    poetry-dynamic-versioning = {
      url = "github:mtkennerly/poetry-dynamic-versioning";
      flake = false;
    };
    iteration-utilities = {
      url = "github:MSeifert04/iteration_utilities";
      flake = false;
    };
    jinja2-ansible-filters = {
      # Can't use typical gitlab access method cause subgroup :/
      url =
        "git+https://gitlab.com/dreamer-labs/libraries/jinja2-ansible-filters";
      flake = false;
    };

  };

  outputs = { self, nixpkgs, flake-utils, ... }@inputs:
    let
      pkgs = nixpkgs.legacyPackages."x86_64-linux";
      pyPackages = pkgs.python39Packages;
      pyBuild = pyPackages.buildPythonPackage;
      poetry-dyn-ver = pkgs.poetry2nix.mkPoetryApplication rec {
        src = pkgs.fetchFromGitHub {
          owner = "mtkennerly";
          repo = "poetry-dynamic-versioning";
          rev = "v0.8.1";
          sha256 = "sha256-YSdJ84ci3yd4P7q+Ux5bSafNXMmAh9/qgIUF6d8y8R8=";
        };

        pyproject = "${src}/pyproject.toml";
        poetrylock = "${src}/poetry.lock";
      };
      # poetry-dynamic-versioning = pyBuild {
      #   pname = "poetry-dynamic-versioning";
      #   version = "0.13.1";
      #   src = poetry-dynamic-versioning;
      #   format = "pyproject";
      # };
      iteration-utilities = pyBuild {
        pname = "iteration_utilities";
        version = "0.11.0";
        src = iteration-utilities;
      };
      copier = pyBuild rec {
        pname = "copier";
        version = "5.1.0";
        src = ./.;
        format = "pyproject";
        propagatedBuildInputs = with pyPackages; [
          poetry-core
          #poetry-dynamic-versioning
          poetry-dyn-ver
          cached-property
          colorama
          importlib-metadata
          iteration-utilities
          pathspec
          jinja2
          jinja2-ansible-filters
        ];
        meta = with nixpkgs.lib; {
          description = ''
            A library for rendering project templates.
          '';
          homepage = "https://github.com/copier-org/copier";
          license = licenses.mit;
        };
      };
    in {
      # Nixpkgs overlay providing the application
      overlay = (final: prev: { inherit copier; });
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlay ];
        };
      in rec {
        apps = { copier = pkgs.copier; };

        defaultApp = apps.copier;
      }));
}
