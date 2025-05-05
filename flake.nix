{
  description = "Python development environment with Ruff and Pyright";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        python = pkgs.python3;
        pythonPackages = python.withPackages (
          ps: with ps; [
            pytest
            python-dotenv
            yfinance
            requests
            requests-cache
            requests-ratelimiter
            pyrate-limiter
            responses
            termgraph
            pytest-mock
            pandas
            pandas-stubs

            pip
            setuptools
            wheel
          ]
        );
      in
      {
        devShells.default = pkgs.mkShell {
          name = "python-dev-shell";

          buildInputs = [
            python
            pythonPackages
            pkgs.ruff
            pkgs.pyright
          ];

          shellHook = ''
            export PYTHON_DOTENV_LOAD_ALL=1
            export PYTHONPATH="${toString ./stock_tracker}:$PYTHONPATH"
            echo "🐍 Python flake dev shell ready"
          '';
        };
      }
    );
}
