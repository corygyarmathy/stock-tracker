# shell.nix
let
  pkgs = import <nixpkgs> { };
in
pkgs.mkShell {
  name = "impureVenv";
  venvDir = "./.venv";
  buildInputs = with pkgs; [
    python3
    (pkgs.python3.withPackages (
      python-pkgs: with python-pkgs; [
        # select Python packages here
        venvShellHook
        pytest
        yfinance
        termgraph
      ]
    ))
  ];
  # postVenvCreation = ''
  #   if [ -f ./requirements.txt]; then
  #     pip install -r ${./requirements.txt}
  #   fi
  # '';
  shellHook = ''
    venvShellHook
  '';
}
