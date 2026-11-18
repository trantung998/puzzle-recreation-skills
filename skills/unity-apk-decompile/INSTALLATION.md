# unity-apk-decompile - global fork notes

This is the global copy of the skill, installed at `~/.agents/skills/unity-apk-decompile`.

## Fork origin

- Forked from the ParkingLoop project copy `H:\UGame\ParkingLoop\.agents\skills\unity-apk-decompile`.
- Upstream: https://github.com/trantung998/unity-apk-decompile
- Upstream revision: `025bff05a56ae7cc842e92a2518c4abb5ad1ac48`
- Changes against the project copy: tool root resolution and platform layout in `scripts/tools-env.sh`,
  `-I` instead of `-P` for `unity_yaml.py` (works on Python 3.9),
  the three `scripts/bin/` wrappers (`python3`, `il2cppdumper`, `ilspycmd`),
  `SKILL.md` line 24 (source path), this file, and `tests/test_tools_env.sh`.

## Tool directory resolution

`scripts/tools-env.sh` picks the tool root in this order:

1. `$UNITY_DECOMPILE_TOOLS` (if set but missing, it is an error; there is no fallthrough)
2. `H:/UGame/ParkingLoop/tools`, if it exists
3. `~/.cache/puzzle-recreation/tools`

If none resolves it prints `unity-apk-decompile: no tool directory; run
recreate-puzzle-gameplay/scripts/ensure_tools.py` and returns 1. On success it
exports `UNITY_DECOMPILE_TOOLS` plus `SK`, `PATH`, `JAVA_HOME`, `GHIDRA_INSTALL_DIR`,
`ANALYZE_HEADLESS`, `GHIDRA_HEADLESS_MAXMEM`, `IL2CPPDUMPER_DIR`, `ASSETRIPPER`
and `DOTNET_ROLL_FORWARD`. The `bin/` wrappers require `UNITY_DECOMPILE_TOOLS`,
so source `tools-env.sh` first. System PATH is never changed.

Expected subfolders: `decompile-python`, `jdk-25`, `ghidra-12.2`,
`Il2CppDumper-6.7.46`, `AssetRipper_2.0.0`, `ilspycmd-9.1.0`.

## Platform

Decompile phase runs on Windows (Git Bash), macOS (Intel and Apple Silicon, stock
`/bin/bash` 3.2) and Linux. `scripts/tools-env.sh` detects the platform with `uname -s` and
picks the layout:

| | Windows (Git Bash) | macOS | Linux |
|---|---|---|---|
| venv interpreter | `decompile-python/Scripts/python.exe` | `decompile-python/bin/python` | `decompile-python/bin/python` |
| `JAVA_HOME` | `jdk-25` (via `cygpath -m`) | `jdk-25/Contents/Home` | `jdk-25` |
| `ASSETRIPPER` | `AssetRipper.GUI.Free.exe` | `AssetRipper.GUI.Free` | `AssetRipper.GUI.Free` |
| user-scope .NET | `<root>/dotnet/dotnet.exe` | `<root>/dotnet/dotnet` | `<root>/dotnet/dotnet` |

It also exports `UNITY_DECOMPILE_PLATFORM` (`windows`/`macos`/`linux`), puts
`<root>/dotnet` first on PATH and sets `DOTNET_ROOT` when that folder exists, and on
macOS/Linux restores the exec bit on `scripts/bin/*` (bash ignores PATH entries without it,
and copies made on Windows or by a skill installer can lose it).

## Drift

The project copy and this global copy are independent and can drift. Inside
`H:\UGame\ParkingLoop` the project copy wins only in OpenCode and Codex, which read
`<project>/.agents/skills`. Claude Code ignores `<project>/.agents/skills`, so it uses
this global copy (through its `~/.claude/skills` link) everywhere, including inside
`H:\UGame\ParkingLoop`. Re-sync deliberately if upstream fixes matter.

## Installing missing tools

`recreate-puzzle-gameplay/scripts/ensure_tools.py` installs missing tools into
the resolved tool directory (pinned versions, no admin, no PATH edits).

## Test

```bash
"C:/Program Files/Git/bin/bash.exe" tests/test_tools_env.sh   # Windows; expects PASS 8/8
bash tests/test_tools_env.sh                                   # macOS / Linux; expects PASS 8/8
```