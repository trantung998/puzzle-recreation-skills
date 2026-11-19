#!/usr/bin/env bash
# Run: bash tests/test_ghidra_decompile.sh   (Git Bash on Windows, /bin/bash on macOS, bash on Linux)
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT="$HERE/../scripts/ghidra_decompile.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fails=""; total=5
ok() { pass=$((pass+1)); }
bad() { fails="$fails $1"; }

# Fake Ghidra install: support/analyzeHeadless records its args and writes _index.tsv per STUB_MODE.
GH="$TMP/gh"
mkdir -p "$GH/support" "$GH/Ghidra/Features/Decompiler/os/mac_x86_64"
cat > "$GH/support/analyzeHeadless" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
out=; prev=
for a in "$@"; do
  [ "$prev" = DecompileIl2cppTargets.java ] && out=$a
  prev=$a
done
mkdir -p "$1/$2.rep"
case "$STUB_MODE" in
  ok)   printf 'A\t0x1\tOK\n' > "$out/_index.tsv" ;;
  fail) printf 'UIOKButton\t0x2\tFAIL\n' > "$out/_index.tsv" ;;
  none) exit 1 ;;
esac
exit 0
STUB
chmod +x "$GH/support/analyzeHeadless"
printf '#!/usr/bin/env bash\nexit 0\n' > "$GH/Ghidra/Features/Decompiler/os/mac_x86_64/decompile"
chmod +x "$GH/Ghidra/Features/Decompiler/os/mac_x86_64/decompile"

export ANALYZE_HEADLESS="$GH/support/analyzeHeadless"
export STUB_LOG="$TMP/stub.log"
W="$TMP/work"; mkdir -p "$W"
printf 'Foo\tbar\n' > "$W/targets.tsv"
python3 -I -c 'import sys;h=bytearray(20);h[4]=2;h[18]=183;open(sys.argv[1],"wb").write(bytes(h))' "$TMP/a.so"
cp "$TMP/a.so" "$TMP/b.so"; printf 'x' >> "$TMP/b.so"   # differs from a.so in content
sha12() { python3 -I -c 'import sys,hashlib;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()[:12])' "$1" | tr -d '\r'; }
HA=$(sha12 "$TMP/a.so"); HB=$(sha12 "$TMP/b.so")
run() { STUB_MODE=$1 bash "$SCRIPT" "$2" "$W" >>"$TMP/run.out" 2>&1; }

: > "$STUB_LOG"
run ok "$TMP/a.so"; rc=$?
if [ $rc -eq 0 ] && grep -q -- '-import' "$STUB_LOG" && grep -q "il2cpp-$HA" "$STUB_LOG"; then ok; else bad case1; fi

: > "$STUB_LOG"
run ok "$TMP/a.so"; rc=$?
if [ $rc -eq 0 ] && grep -q -- '-process' "$STUB_LOG"; then ok; else bad case2; fi

: > "$STUB_LOG"
run ok "$TMP/b.so"
if grep -q -- '-import' "$STUB_LOG" && grep -q "il2cpp-$HB" "$STUB_LOG" && [ "$HA" != "$HB" ]; then ok; else bad case3; fi

run fail "$TMP/b.so"; rc=$?
[ $rc -eq 1 ] && ok || bad case4

run ok "$TMP/b.so"   # leaves an all-OK _index.tsv behind
run none "$TMP/b.so"; rc=$?
[ $rc -eq 1 ] && ok || bad case5

if [ $pass -eq $total ]; then echo "PASS $pass/$total"; else echo "FAIL$fails"; exit 1; fi
