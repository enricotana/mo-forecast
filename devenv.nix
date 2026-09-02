{ pkgs, ... }:
{
  packages = with pkgs; [
    basedpyright
    cmake
    gfortran15
    pre-commit
    ruff
    zlib
  ];

  languages.python = {
    enable = true;
    version = "3.12";
    venv.enable = true;
    uv.enable = true;
  };

  enterShell = ''
    python --version
  '';

  enterTest = ''
    pytest
  '';
}
