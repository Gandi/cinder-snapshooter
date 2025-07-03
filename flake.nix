{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { utils, nixpkgs, ... }:
    utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShell = pkgs.mkShell {
          buildInputs = [ pkgs.uv pkgs.python39 pkgs.gettext ];
          # For greenlet
          LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH";
          shellHook = ''
            echo
            echo Welcome to the cinder-snapshooter development shell
            echo ----------------------------------------------------------
            echo
            echo To install all dependencies:
            echo '$ uv sync'
            echo
            echo To run tests:
            echo '$ uv run pytest'
            echo
          '';
        };
      });
}
