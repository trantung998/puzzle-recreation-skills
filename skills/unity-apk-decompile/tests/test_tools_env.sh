#!/usr/bin/env bash
# Run: bash tests/test_tools_env.sh   (Git Bash on Windows, /bin/bash on macOS, bash on Linux)
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENVSH="$HERE/../scripts/tools-env.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fails=""; total=10
ok() { pass=$((pass+1)); }
bad() { fails="$fails $1"; }
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1;; *) WIN=0;; esac

mkdir -p "$TMP/t1/ghidra-12.2"
out=$( (unset UNITY_DECOMPILE_TOOLS; export UNITY_DECOMPILE_TOOLS="$TMP/t1"; source "$ENVSH" 2>/dev/null; echo "$GHIDRA_INSTALL_DIR") )
case "$out" in */t1/ghidra-12.2) ok;; *) bad case1;; esac

if [ -d "H:/UGame/ParkingLoop/tools" ]; then
  out=$( (unset UNITY_DECOMPILE_TOOLS; source "$ENVSH" 2>/dev/null; echo "$UNITY_DECOMPILE_TOOLS") )
  want=$(cygpath -m "H:/UGame/ParkingLoop/tools")
  if [ "$(printf '%s' "$out" | tr A-Z a-z)" = "$(printf '%s' "$want" | tr A-Z a-z)" ]; then ok; else bad case2; fi
else
  ok
fi

err=$( (export UNITY_DECOMPILE_TOOLS=/nonexistent; source "$ENVSH") 2>&1 >/dev/null )
(export UNITY_DECOMPILE_TOOLS=/nonexistent; source "$ENVSH" >/dev/null 2>&1); rc=$?
case "$err" in *"no tool directory"*) [ $rc -ne 0 ] && ok || bad case3;; *) bad case3;; esac

# case4: python3 resolves to the venv interpreter of this platform's layout
if [ $WIN = 1 ]; then venv="decompile-python/Scripts/python.exe"; else venv="decompile-python/bin/python"; fi
mkdir -p "$TMP/t4/$(dirname "$venv")"
printf '#!/usr/bin/env bash\necho fake-python\n' > "$TMP/t4/$venv"
chmod +x "$TMP/t4/$venv"
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t4"; source "$ENVSH" 2>/dev/null; python3) 2>/dev/null )
[ "$out" = "fake-python" ] && ok || bad case4

# case5: macOS Temurin bundle layout -> JAVA_HOME is jdk-25/Contents/Home, java on PATH
mkdir -p "$TMP/t5/jdk-25/Contents/Home/bin"
printf '#!/usr/bin/env bash\necho fake-java\n' > "$TMP/t5/jdk-25/Contents/Home/bin/java"
chmod +x "$TMP/t5/jdk-25/Contents/Home/bin/java"
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t5"; source "$ENVSH" 2>/dev/null; echo "$JAVA_HOME|$(java)") 2>/dev/null )
case "$out" in */t5/jdk-25/Contents/Home\|fake-java) ok;; *) bad case5;; esac

# case6: flat JDK layout (Windows, Linux) -> JAVA_HOME is jdk-25
mkdir -p "$TMP/t6/jdk-25/bin"
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t6"; source "$ENVSH" 2>/dev/null; echo "$JAVA_HOME") )
case "$out" in */t6/jdk-25) ok;; *) bad case6;; esac

# case7: AssetRipper binary name follows the platform (.exe on Windows only)
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t1"; source "$ENVSH" 2>/dev/null; echo "$ASSETRIPPER") )
if [ $WIN = 1 ]; then want="*/AssetRipper_2.0.0/AssetRipper.GUI.Free.exe"; else want="*/AssetRipper_2.0.0/AssetRipper.GUI.Free"; fi
case "$out" in $want) ok;; *) bad case7;; esac

# case8: a user-scope .NET in <root>/dotnet is put first on PATH and exported as DOTNET_ROOT
if [ $WIN = 1 ]; then dn="dotnet.exe"; else dn="dotnet"; fi
mkdir -p "$TMP/t8/dotnet"
printf '#!/usr/bin/env bash\necho fake-dotnet\n' > "$TMP/t8/dotnet/$dn"
chmod +x "$TMP/t8/dotnet/$dn"
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t8"; source "$ENVSH" 2>/dev/null; echo "$DOTNET_ROOT|$(dotnet)") 2>/dev/null )
case "$out" in */t8/dotnet\|fake-dotnet) ok;; *) bad case8;; esac

# case9: Il2CppInspectorRedux folder is exported for run_il2cppinspector.sh
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t1"; source "$ENVSH" 2>/dev/null; echo "$IL2CPPINSPECTOR_DIR") )
case "$out" in */t1/Il2CppInspectorRedux-2026.2) ok;; *) bad case9;; esac

# case10: without <root>/dotnet, DOTNET_ROOT follows the dotnet on PATH (apphosts ignore PATH)
mkdir -p "$TMP/t10/tools" "$TMP/t10/sdk"
printf '#!/usr/bin/env bash\necho path-dotnet\n' > "$TMP/t10/sdk/$dn"
chmod +x "$TMP/t10/sdk/$dn"
out=$( (unset DOTNET_ROOT; export UNITY_DECOMPILE_TOOLS="$TMP/t10/tools" PATH="$TMP/t10/sdk:$PATH"; source "$ENVSH" 2>/dev/null; echo "$DOTNET_ROOT") )
case "$out" in */t10/sdk) ok;; *) bad case10;; esac

if [ $pass -eq $total ]; then echo "PASS $total/$total"; exit 0; fi
echo "FAIL$fails"; exit 1
