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
      # Can't use typical gitlab access method 'cause subgroup :/
      url =
        "git+https://gitlab.com/dreamer-labs/libraries/jinja2-ansible-filters";
      flake = false;
    };
    dunamai = {
      url = "github:mtkennerly/dunamai";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-utils, ... }@inputs:
    let
      pkgs = nixpkgs.legacyPackages."x86_64-linux";
      pyPackages = pkgs.python39Packages;
      pyBuild = pyPackages.buildPythonPackage;
      poetry-dynamic-versioning = pyBuild {
        pname = "poetry-dynamic-versioning";
        version = "0.13.1";
        src = inputs.poetry-dynamic-versioning;
        format = "pyproject";
        propagatedBuildInputs = with pkgs // pyPackages; [ poetry python jinja2 dunamai ];
      };
      iteration-utilities = pyBuild {
        pname = "iteration_utilities";
        version = "0.11.0";
        src = inputs.iteration-utilities;
        doCheck = false; # Dies on setuptoolsCheckPhase, idk why sooo... /shrug
      };
      jinja2-ansible-filters = pyBuild {
        pname = "jinja2-ansible-filters";
        version = "1.3.0";
        src = inputs.jinja2-ansible-filters;
        propagatedBuildInputs = with pyPackages; [ pyyaml jinja2 ];
      };
      dunamai = pyBuild {
        pname = "dunamai";
        version = "1.7.0";
        src = inputs.dunamai;
        format = "pyproject";
        propagatedBuildInputs = with pyPackages; [ poetry ];
      };
      copier = pyBuild rec {
        pname = "copier";
        version = "5.1.0";
        src = ./.;
        format = "pyproject";
        propagatedBuildInputs = with pyPackages; [
          poetry-core
          poetry-dynamic-versioning
          #poetry-dyn-ver
          cached-property
          colorama
          importlib-metadata
          iteration-utilities
          pathspec
          jinja2
          jinja2-ansible-filters
          pytest
          poetry
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
