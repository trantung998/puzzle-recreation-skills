#!/usr/bin/env bash
# Dump IL2CPP metadata with Il2CppInspectorRedux (metadata v24-v39+, Unity 6; Il2CppDumper stops at v31)
# and write the Il2CppDumper file layout the other scripts read.
# Usage: bash run_il2cppinspector.sh <libil2cpp.so> <global-metadata.dat> <out-dir> [unity-version]
# Env: IL2CPPINSPECTOR_DIR = folder holding Il2CppInspector(.exe), the Legacy CLI (tools-env.sh sets it)
# Writes <out-dir>/dump.cs (Inspector C# with field offsets and method addresses), script.json,
# stringliteral.json, il2cpp.h, metadata.json (raw Inspector JSON), il2cppinspector.log.
set -euo pipefail
SO=$1; META=$2; OUT=$3; UV=${4:-}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DIR=${IL2CPPINSPECTOR_DIR:-}
EXE=""
for c in "$DIR/Il2CppInspector.exe" "$DIR/Il2CppInspector"; do
  [[ -n "$DIR" && -f "$c" ]] && { EXE=$c; break; }
done
[[ -n "$EXE" ]] || { echo "Il2CppInspector not found in IL2CPPINSPECTOR_DIR='$DIR': run recreate-puzzle-gameplay/scripts/ensure_tools.py (Legacy CLI release of github.com/LukeFZ/Il2CppInspectorRedux)" >&2; exit 2; }
[[ -x "$EXE" ]] || chmod +x "$EXE" 2>/dev/null || true
mkdir -p "$OUT"
rm -rf "$OUT/.cpp"
args=(-i "$SO" -m "$META" --select-outputs -c "$OUT/dump.cs" -o "$OUT/metadata.json" -h "$OUT/.cpp" -e none)
[[ -n "$UV" ]] && args+=(--unity-version "$UV")
"$EXE" "${args[@]}" </dev/null 2>&1 | tee "$OUT/il2cppinspector.log" | tail -12
python3 -I "$HERE/inspector_to_dumper.py" "$OUT"
rm -rf "$OUT/.cpp"
for f in dump.cs script.json il2cpp.h stringliteral.json; do
  [[ -s "$OUT/$f" ]] || { echo "FAILED: $OUT/$f missing - see $OUT/il2cppinspector.log" >&2; exit 1; }
done
echo "OK: $(grep -cE '// 0x[0-9A-F]+-0x' "$OUT/dump.cs") methods with address in $OUT/dump.cs" >&2
