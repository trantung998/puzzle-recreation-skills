#!/usr/bin/env bash
# Source from bash: Git Bash on Windows, /bin/bash (3.2+) on macOS, bash on Linux.
# Tool paths stay local to this shell.
# Tool root: $UNITY_DECOMPILE_TOOLS, else H:/UGame/ParkingLoop/tools, else ~/.cache/puzzle-recreation/tools.
_DECOMPILE_SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -n "${UNITY_DECOMPILE_TOOLS:-}" ]; then
  if [ ! -d "$UNITY_DECOMPILE_TOOLS" ]; then
    echo "unity-apk-decompile: no tool directory; run recreate-puzzle-gameplay/scripts/ensure_tools.py" >&2
    unset _DECOMPILE_SCRIPTS
    return 1
  fi
elif [ -d "H:/UGame/ParkingLoop/tools" ]; then
  UNITY_DECOMPILE_TOOLS="H:/UGame/ParkingLoop/tools"
elif [ -d "$HOME/.cache/puzzle-recreation/tools" ]; then
  UNITY_DECOMPILE_TOOLS="$HOME/.cache/puzzle-recreation/tools"
else
  echo "unity-apk-decompile: no tool directory; run recreate-puzzle-gameplay/scripts/ensure_tools.py" >&2
  unset _DECOMPILE_SCRIPTS
  return 1
fi

# Platform layout. Windows (Git Bash/MSYS/Cygwin): venv in Scripts/, .exe tools, native paths
# via cygpath. macOS: the Temurin JDK keeps its bundle layout (jdk-25/Contents/Home).
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) UNITY_DECOMPILE_PLATFORM=windows ;;
  Darwin)               UNITY_DECOMPILE_PLATFORM=macos ;;
  *)                    UNITY_DECOMPILE_PLATFORM=linux ;;
esac
_decompile_native() {
  if [ "$UNITY_DECOMPILE_PLATFORM" = windows ] && command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1"
  else
    printf '%s\n' "$1"
  fi
}
if [ "$UNITY_DECOMPILE_PLATFORM" = windows ]; then
  _DECOMPILE_VENV_BIN="$UNITY_DECOMPILE_TOOLS/decompile-python/Scripts"
  _DECOMPILE_EXE=.exe
else
  _DECOMPILE_VENV_BIN="$UNITY_DECOMPILE_TOOLS/decompile-python/bin"
  _DECOMPILE_EXE=
fi
# bash skips PATH entries without the exec bit; copies made on Windows or by a skill
# installer can lose it, so restore it on the wrappers (best effort, read-only installs ignored).
if [ "$UNITY_DECOMPILE_PLATFORM" != windows ]; then
  for _w in "$_DECOMPILE_SCRIPTS"/bin/*; do
    [ -f "$_w" ] && [ ! -x "$_w" ] && chmod +x "$_w" 2>/dev/null
  done
  unset _w
fi
_DECOMPILE_JDK="$UNITY_DECOMPILE_TOOLS/jdk-25"
[ -d "$_DECOMPILE_JDK/Contents/Home" ] && _DECOMPILE_JDK="$_DECOMPILE_JDK/Contents/Home"

export UNITY_DECOMPILE_TOOLS UNITY_DECOMPILE_PLATFORM
export SK="$_DECOMPILE_SCRIPTS"
export PATH="$_DECOMPILE_SCRIPTS/bin:$_DECOMPILE_VENV_BIN:$_DECOMPILE_JDK/bin:$PATH"
# A user-scope .NET installed by dotnet-install into <root>/dotnet (ensure_tools manual hint).
if [ -f "$UNITY_DECOMPILE_TOOLS/dotnet/dotnet$_DECOMPILE_EXE" ]; then
  export PATH="$UNITY_DECOMPILE_TOOLS/dotnet:$PATH"
  export DOTNET_ROOT
  DOTNET_ROOT=$(_decompile_native "$UNITY_DECOMPILE_TOOLS/dotnet")
fi
export JAVA_HOME
JAVA_HOME=$(_decompile_native "$_DECOMPILE_JDK")
export GHIDRA_INSTALL_DIR="$UNITY_DECOMPILE_TOOLS/ghidra-12.2"
export ANALYZE_HEADLESS="$GHIDRA_INSTALL_DIR/support/analyzeHeadless"
export GHIDRA_HEADLESS_MAXMEM=4G
export IL2CPPDUMPER_DIR="$UNITY_DECOMPILE_TOOLS/Il2CppDumper-6.7.46"
export ASSETRIPPER
ASSETRIPPER=$(_decompile_native "$UNITY_DECOMPILE_TOOLS/AssetRipper_2.0.0/AssetRipper.GUI.Free$_DECOMPILE_EXE")
export DOTNET_ROLL_FORWARD=LatestMajor
unset _DECOMPILE_SCRIPTS _DECOMPILE_VENV_BIN _DECOMPILE_EXE _DECOMPILE_JDK
unset -f _decompile_native
