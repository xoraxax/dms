{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (ps: with ps; [ flask ]))
    imagemagick
    pdfsandwich
    poppler_utils
    which
    ghostscript
    netpbm

    (pkgs.writers.writeBashBin "run" ''
      cd ${toString ./.}
      DMSDATA=db FLASK_APP=dms.py flask run "$@"
    '')
  ];
}
