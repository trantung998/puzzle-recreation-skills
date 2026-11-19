#!/usr/bin/env bash
# Run: bash tests/test_in_env.sh   (Git Bash on Windows, /bin/bash on macOS, bash on Linux)
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WRAP="$HERE/../scripts/in_env.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fails=""; total=6
ok() { pass=$((pass+1)); }
bad() { fails="$fails $1"; }

mkdir -p "$TMP/t1/ghidra-12.2" "$TMP/My Work"
printf "W='%s'\nSO='/x/lib il2cpp.so'\n" "$TMP/My Work" > "$TMP/My Work/paths.env"
export UNITY_DECOMPILE_TOOLS="$TMP/t1"
want="$TMP/My Work|/x/lib il2cpp.so"
CMD='printf "%s|%s" "$W" "$SO"'

out=$(bash "$WRAP" "$TMP/My Work" "$CMD" 2>/dev/null)
[ "$out" = "$want" ] && ok || bad case1

if command -v zsh >/dev/null 2>&1; then
  out=$(zsh -c 'bash "$1" "$2" "$3"' zsh "$WRAP" "$TMP/My Work" "$CMD" 2>/dev/null)
  [ "$out" = "$want" ] && ok || bad case2
else
  ok
fi

bash "$WRAP" "$TMP/My Work" 'exit 7' >/dev/null 2>&1; rc=$?
[ $rc -eq 7 ] && ok || bad case3

err=$(UNITY_DECOMPILE_TOOLS=/nonexistent bash "$WRAP" "$TMP/My Work" 'echo hi' 2>&1 >/dev/null)
UNITY_DECOMPILE_TOOLS=/nonexistent bash "$WRAP" "$TMP/My Work" 'echo hi' >/dev/null 2>&1; rc=$?
case "$err" in *"no tool directory"*) [ $rc -ne 0 ] && ok || bad case4;; *) bad case4;; esac

mkdir -p "$TMP/Fresh"
out=$(bash "$WRAP" "$TMP/Fresh" 'printf "%s|%s|%s" "$W" "$SO" "$SK"' 2>/dev/null)
sk="$(cd "$HERE/../scripts" && pwd)"
case "$out" in "$TMP/Fresh||"*) [ "$(cd "${out#"$TMP/Fresh||"}" 2>/dev/null && pwd)" = "$sk" ] && ok || bad case5;; *) bad case5;; esac

bash "$WRAP" "$TMP/My Work" >/dev/null 2>&1; rc=$?
[ $rc -eq 2 ] && ok || bad case6

if [ $pass -eq $total ]; then echo "PASS $total/$total"; exit 0; fi
echo "FAIL$fails"; exit 1
