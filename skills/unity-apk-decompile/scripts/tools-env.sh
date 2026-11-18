#!/usr/bin/env bash
# Source from Git Bash. Tool paths stay local to this shell.
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
export UNITY_DECOMPILE_TOOLS
export SK="$_DECOMPILE_SCRIPTS"
export PATH="$_DECOMPILE_SCRIPTS/bin:$UNITY_DECOMPILE_TOOLS/decompile-python/Scripts:$UNITY_DECOMPILE_TOOLS/jdk-25/bin:$PATH"
export JAVA_HOME
JAVA_HOME=$(cygpath -m "$UNITY_DECOMPILE_TOOLS/jdk-25")
export GHIDRA_INSTALL_DIR="$UNITY_DECOMPILE_TOOLS/ghidra-12.2"
export ANALYZE_HEADLESS="$GHIDRA_INSTALL_DIR/support/analyzeHeadless"
export GHIDRA_HEADLESS_MAXMEM=4G
export IL2CPPDUMPER_DIR="$UNITY_DECOMPILE_TOOLS/Il2CppDumper-6.7.46"
export ASSETRIPPER
ASSETRIPPER=$(cygpath -m "$UNITY_DECOMPILE_TOOLS/AssetRipper_2.0.0/AssetRipper.GUI.Free.exe")
export DOTNET_ROLL_FORWARD=LatestMajor
unset _DECOMPILE_SCRIPTS