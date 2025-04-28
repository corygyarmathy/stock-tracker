# shell.nix
let
  pkgs = import <nixpkgs> { };
in
pkgs.mkShell {
  name = "impureVenv";
  # venvDir = "./.venv";
  buildInputs = with pkgs; [
    python3
    (pkgs.python3.withPackages (
      python-pkgs: with python-pkgs; [
        # select Python packages here
        venvShellHook
        pytest
        python-dotenv
        yfinance
        requests # API requests
        requests-cache
        requests-ratelimiter
        pyrate-limiter
        responses # Mock requests
        termgraph
        pytest-mock
        pandas
        pandas-stubs

        pip
        setuptools
        wheel
      ]
    ))
  ];
  shellHook = ''
    # Setup python-dotenv
    export PYTHON_DOTENV_LOAD_ALL=1  # Enable loading all variables from .env
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$out/lib  # Ensure libraries are found
    export PYTHONPATH="${toString ./stock_tracker}:$PYTHONPATH"
    echo "🐍 Python dev shell ready"
  '';
}
