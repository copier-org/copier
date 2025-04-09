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

    # HACK https://github.com/renovatebot/renovate/issues/29721
    # TODO Remove these comments when fixed
    # github:NixOS/nixpkgs/nixpkgs-24.05
  };
  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/*.tar.gz";

    flake-compat.url = "https://flakehub.com/f/edolstra/flake-compat/1.*.tar.gz";

    devenv.url = "github:cachix/devenv";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    devenv,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    ...
  } @ inputs: let
    inherit (nixpkgs) lib;
    forAllSystems = lib.genAttrs lib.systems.flakeExposed;

    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};

    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };

    pythonSets = forAllSystems (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (pkgs) stdenv;

        python = pkgs.python312;

        lastRelease = (pkgs.lib.importTOML ./pyproject.toml).tool.commitizen.version;
        version = "${lastRelease}.dev${self.sourceInfo.lastModifiedDate}+nix-git-${self.sourceInfo.shortRev or "dirty"}";

        pyprojectOverrides = final: prev: {
          copier = prev.copier.overrideAttrs (old: {
            # Trick `hatch-vcs` into using our version
            env =
              (old.env or {})
              // {
                SETUPTOOLS_SCM_PRETEND_VERSION = version;
              };

            passthru =
              old.passthru
              // {
                tests = let
                  # Create a virtual environment with only the dependency group "dev" enabled.
                  virtualenv = final.mkVirtualEnv "copier-pytest-env" {
                    copier = ["dev"];
                  };
                in
                  (old.tests or {})
                  // {
                    pytest = stdenv.mkDerivation {
                      name = "${final.copier.name}-pytest";
                      inherit (final.copier) src;
                      nativeBuildInputs = [
                        virtualenv
                        pkgs.git
                      ];
                      dontConfigure = true;
                      dontInstall = true;
                      buildPhase = ''
                        mkdir $out
                        patchShebangs tests
                        env \
                          GIT_AUTHOR_EMAIL=copier@example.com \
                          GIT_AUTHOR_NAME=copier \
                          GIT_COMMITTER_EMAIL=copier@example.com \
                          GIT_COMMITTER_NAME=copier \
                          PATH=$out/bin:$PATH \
                          PYTHONOPTIMIZE= \
                          pytest --color=yes -m 'not impure'

                          # Make sure version is properly patched in Nix build
                          test "$(copier --version)" != "copier 0.0.0"
                      '';
                    };
                  };
              };
          });
        };
      in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        })
        .overrideScope
        (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]
        )
    );
  in rec {
    packages = forAllSystems (
      system: let
        pythonSet = pythonSets.${system};
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (pkgs.callPackages pyproject-nix.build.util {}) mkApplication;
      in {
        default = mkApplication {
          venv = pythonSet.mkVirtualEnv "copier-env" workspace.deps.default;
          package = pythonSet.copier;
        };
      }
    );

    apps = forAllSystems (
      system: let
        pythonSet = pythonSets.${system};
        package = packages.${system};
      in {
        default = {
          type = "app";
          program = "${package.default}/bin/copier";
        };
      }
    );

    checks = forAllSystems (
      system: let
        pythonSet = pythonSets.${system};
      in
        pythonSet.copier.passthru.tests
    );

    devShells = forAllSystems (
      system: let
        pythonSet = pythonSets.${system};
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        default = let
          # Create an overlay enabling editable mode for all local dependencies.
          editableOverlay = workspace.mkEditablePyprojectOverlay {
            root = "$REPO_ROOT";
          };

          # Override previous set with our overrideable overlay.
          editablePythonSet = pythonSet.overrideScope (
            lib.composeManyExtensions [
              editableOverlay

              # Apply fixups for building an editable package of your workspace packages
              (final: prev: {
                copier = prev.copier.overrideAttrs (old: {
                  # Filter the sources going into an editable build to reduce unnecessary rebuilds.
                  src = lib.fileset.toSource {
                    root = old.src;
                    fileset = lib.fileset.unions [
                      (old.src + "/pyproject.toml")
                      (old.src + "/README.md")
                      (old.src + "/copier/__init__.py")
                    ];
                  };

                  # Hatchling (our build system) has a dependency on the `editables` package when building editables.
                  #
                  # In normal Python flows this dependency is dynamically handled, and doesn't need to be explicitly declared.
                  # This behaviour is documented in PEP-660.
                  #
                  # With Nix the dependency needs to be explicitly declared.
                  nativeBuildInputs =
                    old.nativeBuildInputs
                    ++ final.resolveBuildSystem {
                      editables = [];
                    };
                });
              })
            ]
          );

          # Build virtual environment, with local packages being editable.
          #
          # Enable all optional dependencies for development.
          virtualenv = editablePythonSet.mkVirtualEnv "copier-dev-env" workspace.deps.all;
        in
          devenv.lib.mkShell {
            inherit inputs pkgs;
            modules = [
              {
                packages = with pkgs; [
                  # Virtual environment for development
                  virtualenv

                  # Essential dev tools
                  pkgs.uv

                  # IDE integration tools
                  pkgs.alejandra
                  pkgs.commitizen
                  pkgs.mypy
                  pkgs.nodePackages.prettier
                  pkgs.ruff
                  pkgs.taplo
                ];

                env = {
                  # Don't create venv using uv
                  UV_NO_SYNC = "1";

                  # Force uv to use Python interpreter from venv
                  UV_PYTHON = "${virtualenv}/bin/python";

                  # Prevent uv from downloading managed Python's
                  UV_PYTHON_DOWNLOADS = "never";
                };

                enterShell = ''
                  # Undo dependency propagation by nixpkgs.
                  unset PYTHONPATH

                  # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
                  export REPO_ROOT=$(git rev-parse --show-toplevel)
                '';

                difftastic.enable = true;

                pre-commit.hooks = {
                  alejandra.enable = true;
                  commitizen.enable = true;
                  editorconfig-checker.enable = true;
                  editorconfig-checker.excludes = [
                    "\.md$"
                    "\.noeof\."
                    "\.bundle$"
                  ];
                  prettier.enable = true;
                  prettier.excludes = [
                    # Those files have wrong syntax and would fail
                    "^tests/demo_invalid/copier.yml$"
                    "^tests/demo_transclude_invalid(_multi)?/demo/copier.yml$"
                    # HACK https://github.com/prettier/prettier/issues/9430
                    "^tests/demo"
                  ];
                  ruff.enable = true;
                  ruff-format.enable = true;
                  taplo.enable = true;
                };
              }
            ];
          };
      }
    );
  };
}
