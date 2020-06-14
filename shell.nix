{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  buildInputs = with pkgs; [
    (pkgs.python3.withPackages (ps: with ps; [ flask ]))
    pkgs.imagemagickBig
    (pkgs.pdfsandwich.override { imagemagick = pkgs.imagemagickBig; })
    pkgs.poppler_utils
    pkgs.which
    pkgs.netpbm
    pkgs.gawk

    (pkgs.writers.writeBashBin "run" ''
      cd ${toString ./.}
      DMSDATA=db FLASK_APP=dms.py flask run "$@"
    '')
  ];
}
