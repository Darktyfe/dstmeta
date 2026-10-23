"""Download a portable MinGW-w64 compiler into tools/mingw64 (Windows x64).

Only needed when no C++ compiler is installed and ``engine.dll`` has to be
rebuilt from ``food_calc/native/engine.cpp``.  The toolchain is a single
WinLibs release zip, extracted next to this script; it needs no installer and
no admin rights.  Modelled after the download used to build the committed
``engine.dll`` (GCC 16.2, UCRT runtime).
"""

import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP_PATH = ROOT / "winlibs.zip"
GPP = ROOT / "mingw64" / "bin" / "g++.exe"

# WinLibs release: GCC 16.2.0 + MinGW-w64 14.0.0 (UCRT), portable zip.
URL = (
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "16.2.0posix-23.1.3-14.0.0-ucrt-r3/"
    "winlibs-x86_64-posix-seh-gcc-16.2.0-mingw-w64ucrt-14.0.0-r3.zip"
)


def main():
    if GPP.exists():
        print(f"Compiler already installed: {GPP}")
        return 0
    if not ZIP_PATH.exists():
        print(f"Downloading {URL}")
        print("This is one large file (~280 MB); it fetches once.")
        urllib.request.urlretrieve(URL, ZIP_PATH)

    print(f"Extracting {ZIP_PATH.name} into {ROOT}")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(ROOT)
    ZIP_PATH.unlink()

    if GPP.exists():
        print(f"Done: {GPP}")
        return 0
    print("Extraction finished, but g++.exe was not found where expected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
