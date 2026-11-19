# Puzzle Gameplay Recreation — skill set

Agent skills that recreate the gameplay of an Android Unity puzzle game (APK / XAPK / APKS / APKM)
inside a Unity project: the first N base levels, original visuals and behaviour as far as evidence
allows, and fast level switching. Works in OpenCode, Codex and Claude Code, on Windows, macOS
(Intel and Apple Silicon) and Linux.

## Contents

```text
puzzle-recreation-skills/
|-- skills/
|   |-- recreate-puzzle-gameplay/      # entry point: orchestrates the 9 phases, tools, resume, handoff
|   |-- puzzle-evidence-extraction/    # levels, mechanic rules, visual/audio parameters, evidence labels
|   |-- puzzle-gameplay-build/         # build into Assets/<GameSlug>/, level switcher, asset import
|   |-- puzzle-gameplay-verification/  # model contracts, real pointer smoke, sample win, check_evidence.py
|   `-- unity-apk-decompile/           # decompile fork (tools located via UNITY_DECOMPILE_TOOLS)
|-- docs/
|   |-- design.md                      # design spec (Vietnamese)
|   |-- implementation-plan.md
|   `-- skill-tests/                   # scenarios, RED baseline, GREEN results, discovery check
`-- tools/validate_skills.py           # skill linter (dev only)
```

## Install

1. Copy the five folders in `skills/` into `~/.agents/skills/`
   (Windows: `%USERPROFILE%\.agents\skills\`). Do not overwrite an existing folder with the same
   name without checking it first.
2. OpenCode and Codex scan `~/.agents/skills` — nothing else to do.
3. Claude Code reads `~/.claude/skills` only. From `~/.agents/skills/recreate-puzzle-gameplay` run:

   ```bash
   python3 scripts/install_links.py --harness claude --dry-run   # preview
   python3 scripts/install_links.py --harness claude             # create junctions/symlinks
   ```

   It never replaces an existing entry. To undo, remove each link with `rmdir` (Windows) or
   `rm` on the link (macOS, Linux) — never a recursive delete.

On Windows use `python` or `py -3` where the docs say `python3`. On macOS `python3` from the
Xcode Command Line Tools (3.9) or Homebrew both work; every script supports Python 3.9+.

macOS quick install from a clone of this repo (copies only folders that are not there yet):

```bash
mkdir -p ~/.agents/skills
for s in skills/*/; do n=$(basename "$s"); [ -e ~/.agents/skills/$n ] || cp -R "$s" ~/.agents/skills/$n; done
python3 ~/.agents/skills/recreate-puzzle-gameplay/scripts/install_links.py --harness claude
```

## Use

Ask your agent, for example:

> Use the recreate-puzzle-gameplay skill. APK: `D:/games/MyPuzzle.xapk`, levels: 20,
> Unity project: `D:/Unity/MyPuzzleRecreation`.

Optional: add reference screenshots or gameplay video paths. The run is autonomous; it writes a
work directory `<APK folder>/<GameSlug>-recreation/` (progress, decisions, evidence, checks,
handoff) and can be resumed by invoking the skill again.

## Requirements

- Unity Editor already installed for the target project (never auto-installed).
- Decompile phase: Windows (Git Bash), macOS (stock `/bin/bash`, Intel or Apple Silicon) or
  Linux. `ensure_tools.py` picks the pinned archive for the OS and CPU (`macos-arm64` on
  Apple Silicon).
- Missing decompile tools (JDK, Ghidra, Il2CppInspectorRedux, AssetRipper, ILSpy, Python venv) are
  installed automatically with pinned versions and SHA-256 checks, into
  `$UNITY_DECOMPILE_TOOLS`, else `~/.cache/puzzle-recreation/tools`.
  The .NET 10 runtime (and Git Bash on Windows) are not auto-installed: the run stops with an exact,
  pinned, no-admin command for you to run. An existing `dotnet` (on macOS: official installer in
  `/usr/local/share/dotnet` or Homebrew) is detected and counts only if it has
  `Microsoft.NETCore.App` 10 or newer.
- macOS extra: Xcode Command Line Tools (`xcode-select --install`) — Ghidra's release has no
  macOS decompiler binary, so `ensure_tools.py` builds it locally (~40 s). For the optional
  `level-decoders` tool run `ensure_tools.py` with Python 3.10+ (Homebrew or python.org).

## Known limits

- C# files under `templates/csharp/` are unverified templates; they were statically reviewed but
  never compiled in this package's tests. The skills tell the agent to adapt and verify them.
- No full APK-to-handoff run has been performed on a real game yet; tests were planning
  scenarios (see `docs/skill-tests/`: RED 2/8 → GREEN 8/8) plus unit tests of all scripts.
- The optional `level-decoders` tool (UnityPy, brotli) has never been installed live; pip pins
  use `==` without `--require-hashes`.
- `unity-apk-decompile/scripts/tools-env.sh` falls back to `H:/UGame/ParkingLoop/tools` when
  `UNITY_DECOMPILE_TOOLS` is unset and that folder exists (origin machine); elsewhere set the
  variable or let `ensure_tools.py` install into the cache folder.
- Claude Code ignores `<project>/.agents/skills`, so a project-local copy of a skill only
  overrides the global one in OpenCode and Codex.

## Self-check after install

```bash
python3 -m unittest discover -s ~/.agents/skills/recreate-puzzle-gameplay/tests
python3 -m unittest discover -s ~/.agents/skills/puzzle-evidence-extraction/tests
python3 -m unittest discover -s ~/.agents/skills/puzzle-gameplay-verification/tests
bash ~/.agents/skills/unity-apk-decompile/tests/test_tools_env.sh   # Git Bash on Windows
bash ~/.agents/skills/unity-apk-decompile/tests/test_ghidra_decompile.sh
bash ~/.agents/skills/unity-apk-decompile/tests/test_in_env.sh
python3 tools/validate_skills.py ~/.agents/skills/recreate-puzzle-gameplay ~/.agents/skills/puzzle-evidence-extraction ~/.agents/skills/puzzle-gameplay-build ~/.agents/skills/puzzle-gameplay-verification
```
