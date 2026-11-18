#!/usr/bin/env bash
# Run: bash tests/test_tools_env.sh
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENVSH="$HERE/../scripts/tools-env.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fails=""
ok() { pass=$((pass+1)); }
bad() { fails="$fails $1"; }

mkdir -p "$TMP/t1/ghidra-12.2"
out=$( (unset UNITY_DECOMPILE_TOOLS; export UNITY_DECOMPILE_TOOLS="$TMP/t1"; source "$ENVSH" 2>/dev/null; echo "$GHIDRA_INSTALL_DIR") )
case "$out" in */t1/ghidra-12.2) ok;; *) bad case1;; esac

if [ -d "H:/UGame/ParkingLoop/tools" ]; then
  out=$( (unset UNITY_DECOMPILE_TOOLS; source "$ENVSH" 2>/dev/null; echo "$UNITY_DECOMPILE_TOOLS") )
  want=$(cygpath -m "H:/UGame/ParkingLoop/tools")
  if [ "${out,,}" = "${want,,}" ]; then ok; else bad case2; fi
else
  ok
fi

err=$( (export UNITY_DECOMPILE_TOOLS=/nonexistent; source "$ENVSH") 2>&1 >/dev/null ); rc=$?
(export UNITY_DECOMPILE_TOOLS=/nonexistent; source "$ENVSH" >/dev/null 2>&1); rc=$?
case "$err" in *"no tool directory"*) [ $rc -ne 0 ] && ok || bad case3;; *) bad case3;; esac

mkdir -p "$TMP/t4/decompile-python/Scripts"
printf '#!/usr/bin/env bash\necho fake-python\n' > "$TMP/t4/decompile-python/Scripts/python.exe"
chmod +x "$TMP/t4/decompile-python/Scripts/python.exe"
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t4"; source "$ENVSH" 2>/dev/null; python3) 2>/dev/null )
[ "$out" = "fake-python" ] && ok || bad case4

if [ $pass -eq 4 ]; then echo "PASS 4/4"; exit 0; fi
echo "FAIL$fails"; exit 1