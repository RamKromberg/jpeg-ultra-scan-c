{ pkgs ? import <nixpkgs> {} }:

let
  butteraugli = pkgs.stdenv.mkDerivation rec {
    pname = "butteraugli";
    version = "2019-03-20";

    src = pkgs.fetchFromGitHub {
      owner = "google";
      repo = pname;
      rev = "71b18b636b9c7d1ae0c1d3730b85b3c127eb4511";
      sha256 = "1yb312chgvb2cg0z83vva9dhvrv7p6s3s3z604d1062zfxcyxwql";
    };

    sourceRoot = "source/butteraugli";

    buildInputs = with pkgs; [ zlib libpng libjpeg_turbo ];

    installPhase = ''
      install -Dm755 -t $out/bin butteraugli
    '';

    meta = with pkgs.lib; {
      description = "A tool for measuring perceived differences between images";
      homepage = "https://github.com/google/butteraugli";
      license = licenses.asl20;
      mainProgram = "butteraugli";
    };
  };

  jpegultrascan = pkgs.stdenv.mkDerivation rec {
    pname = "jpegultrascan";
    version = "unstable-2024-04-24";

    dontBuild = true;
    dontConfigure = true;

    src = pkgs.fetchFromGitHub {
      owner = "MegaByte";
      repo = pname;
      rev = "c35ab483a09f83656be36b8fde6c9fed78b85cec";
      sha256 = "sha256-lAG4XJLwCt1rzlGLworYP9tLGtiVJVowrt9GQTAjI78=";
    };

    patchPhase = ''
      patchShebangs jpegultrascan.pl
      patchShebangs jpegdropscan.pl
    '';

    installPhase = ''
      mkdir -p $out/share/jpegultrascan
      mv jpegultrascan.md $out/share/jpegultrascan/
      mv jpegdropscan.md $out/share/jpegultrascan/
      mkdir $out/bin
      mv jpegultrascan.pl $out/bin/jpegultrascan
      mv jpegdropscan.pl $out/bin/jpegdropscan
      chmod +x $out/bin/jpegultrascan
      chmod +x $out/bin/jpegdropscan
      wrapProgram $out/bin/jpegultrascan \
        --prefix PATH : "${pkgs.libjpeg_turbo}/bin:"
      wrapProgram $out/bin/jpegdropscan \
        --prefix PATH : "${pkgs.libjpeg_turbo}/bin:${butteraugli}/bin:"
    '';

    buildInputs = with pkgs; [ perl makeWrapper ];

    meta = with pkgs.lib; {
      description = "Exhaustively shrink any JPEG file losslessly";
      homepage = "https://github.cohttps://github.com/MegaByte/jpegultrascan/";
      license = licenses.asl20;
      platforms = platforms.all;
    };
  };
in

pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    pkg-config
    gnumake
  ];

  buildInputs = with pkgs; [
    libjpeg_turbo
    butteraugli
    jpegultrascan
    imagemagick # test harness
    exiftool # test harness
    clang-tools # $ make format
    python3 # test harness
    valgrind
    vbindiff
  ];

  shellHook = ''
    echo "Available tools: butteraugli, jpegultrascan, jpegdropscan, magick, exiftool, valgrind, vbindiff, python"
    echo "Run 'make' to compile the project."
  '';
}
