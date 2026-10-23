"""Build the native plan-search library used by the calculator.

Finds a g++ toolchain (the portable copy in tools/mingw64 or one on the PATH)
and compiles ``food_calc/native/engine.cpp`` into the shared library next to
the source, which is where ``food_calc/code/cpp_engine.py`` loads it from.

On Windows the output is ``engine.dll``; everywhere else it is
``libengine.so`` / ``libengine.dylib`` and the Python loader expects it.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "food_calc" / "native" / "engine.cpp"

if sys.platform == "win32":
    OUTPUT = ROOT / "food_calc" / "native" / "engine.dll"
else:
    name = "engine.dylib" if sys.platform == "darwin" else "libengine.so"
    OUTPUT = ROOT / "food_calc" / "native" / name

CANDIDATES = [
    Path(__file__).resolve().parent / "mingw64" / "bin" / "g++.exe",
    "g++",
]


def find_compiler():
    for candidate in CANDIDATES:
        if shutil.which(str(candidate)) is not None and Path(candidate).exists():
            return str(candidate)
        if shutil.which(candidate) is not None:
            return candidate
    return None


def main():
    compiler = find_compiler()
    if compiler is None:
        print("No g++ found. Either install one or run py tools/fetch_compiler.py")
        return 1

    command = [
        compiler,
        "-std=c++17", "-O2", "-s", "-shared",
        "-static-libstdc++", "-static-libgcc",
    ]
    if sys.platform == "win32":
        # -static bundles libstdc++, libgcc and winpthread into the DLL, so
        # only the system CRT remains as a dependency.
        command.append("-static")
    else:
        command.append("-fPIC")
    command += ["-o", str(OUTPUT), str(SOURCE)]

    print("Building", OUTPUT.name)
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode == 0:
        print(f"Built {OUTPUT}")
        return 0
    print("Build failed.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
