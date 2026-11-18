# Harness compatibility: OpenCode, Codex, Claude Code

The skill set is five directories, each `<skill-id>/SKILL.md` with only `name` and
`description` in the frontmatter:

`recreate-puzzle-gameplay`, `unity-apk-decompile`, `puzzle-evidence-extraction`,
`puzzle-gameplay-build`, `puzzle-gameplay-verification`.

Canonical install: `~/.agents/skills/<skill-id>/` (Windows: `%USERPROFILE%\.agents\skills\`;
macOS: `/Users/<you>/.agents/skills/`, a hidden folder — `Cmd+Shift+.` shows it in Finder).

Checked on Windows on 2026-11-18 with Codex CLI 0.167.0 and Claude Code 2.1.325, by
listing the skills each harness could see and by reading the harnesses' current
documentation. Items marked "not verified on this machine" come from documentation only.

Checked on macOS (Darwin 25.6, Apple Silicon, `/bin/bash` 3.2, Python 3.9 and 3.14) on
2026-11-18: all unit tests and `test_tools_env.sh`; `ensure_tools.py` installing every pinned
tool (`macos-arm64` archives, SHA-256 matched) and building `ghidra-natives`; `tools-env.sh`
with the real tools; `ghidra_decompile.sh` on an arm64 ELF (`_index.tsv` OK);
`il2cppdumper`, `ilspycmd --version` and AssetRipper headless start. Harness skill listing,
a full APK run and the Unity batchmode routes were not run on macOS.

Il2CppDumper was later replaced by Il2CppInspectorRedux 2026.2 (Legacy CLI, .NET 10 runtime),
because Il2CppDumper cannot read metadata v39 (Unity 6). Checked on Windows 11 (Git Bash) on
2026-11-18: `ensure_tools.py` install (SHA-256 matched), `run_il2cppinspector.sh` on v39 arm64
(3 games), v39 armv7 and v31 arm64, then `select_targets.py` + `ghidra_decompile.sh`
(`_index.tsv` all OK on arm64 and armv7). The macOS and Linux archives are pinned from the
publisher API digests but were not run.

## Where each harness finds skills

| Harness | User (global) location | Project location | Precedence |
|---|---|---|---|
| OpenCode | `~/.agents/skills/` and also `~/.claude/skills/` (both are scanned; a skill present in both places is listed once) | `<project>/.agents/skills/` | A project skill wins over a global skill with the same ID. Checked for `unity-apk-decompile` inside `H:\UGame\ParkingLoop`: the project copy is listed there and the global copy everywhere else. |
| Codex (CLI, IDE extension, desktop app) | `$HOME/.agents/skills/`. Does not read `~/.claude/skills/`. Symlinked skill folders are followed (documented; not verified on this machine). | `.agents/skills/` in every directory from the launch directory up to the repository root (documented; not verified on this machine) | Two skills with the same `name` are not merged; both can be listed (documented; not verified on this machine) |
| Claude Code | `~/.claude/skills/<skill-id>/`. Does not read `~/.agents/skills/`. A skill entry may be a link to a directory elsewhere (documented); a junction worked here. | `<project>/.claude/skills/<skill-id>/`, also in parent directories up to the repository root | Enterprise over personal over project, per the Claude Code documentation (not verified on this machine) |

What the machine checks showed:

- OpenCode listed all five skills with paths under `C:\Users\melod\.agents\skills\`, before
  and after the Claude Code links were created, with no duplicate IDs.
- Codex listed all five skills with no link created, because it scans `~/.agents/skills/`.
  It did not list skills that exist only under `~/.claude/skills/`.
- Claude Code did not list a skill that exists only under `~/.agents/skills/`, so each of the
  five needs a link in `~/.claude/skills/`. With the links in place it listed all five.

## Linking (Claude Code, or any harness that needs it)

A link keeps one copy of each skill. Never copy over or replace an existing directory with
the same name: if `~/.claude/skills/<skill-id>` already exists and is not a link to the
canonical directory, leave it and report it.

The bundled script does this for every skill and every harness that needs it:

```text
python3 "<skill dir>/scripts/install_links.py" --harness claude --dry-run
python3 "<skill dir>/scripts/install_links.py" --harness claude
```

`--harness` is `claude`, `codex` or `all` (the default). `--dry-run` prints the plan and
changes nothing. The output is JSON with one entry per skill per harness and a status of
`created`, `ok` (already linked), `skipped-exists` (a different directory or link is in the
way, left untouched), `would-create` or `error`. For `codex` every skill reports `ok`
because Codex already scans `~/.agents/skills/`. `<skill dir>` is the absolute path of
`recreate-puzzle-gameplay`. It uses only the Python standard library. On Windows it creates
junctions with `_winapi.CreateJunction` (no shell), falling back to `mklink /J` with the
paths passed quoted, so `&`, `^` and `%` in a path are safe.

By hand, on Windows, a directory junction (no admin rights needed), from `cmd`:

```text
mklink /J "%USERPROFILE%\.claude\skills\recreate-puzzle-gameplay" "%USERPROFILE%\.agents\skills\recreate-puzzle-gameplay"
```

From PowerShell, wrap it: `cmd /c mklink /J "<link>" "<target>"`. Repeat for the other four
skill IDs. Create `%USERPROFILE%\.claude\skills` first if it is missing.

By hand, on Unix (Linux, macOS), a symbolic link:

```text
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/recreate-puzzle-gameplay ~/.claude/skills/recreate-puzzle-gameplay
```

Repeat for the other four. Codex needs no link while the skills live in `~/.agents/skills/`.

The per-game notes skill is written to `<project>/.agents/skills/<game-slug>-notes/`.
OpenCode and Codex find it when started inside the project. For Claude Code, the user may
link `<project>/.claude/skills/<game-slug>-notes` to it the same way; the run does not
create that link, because it is outside the folders the run may write.

## How a skill is invoked

| Harness | Implicit | Explicit |
|---|---|---|
| OpenCode | The agent sees each skill's name and description and loads a matching skill by ID through its skill-loading tool | Name the skill in the prompt ("Use the recreate-puzzle-gameplay skill") |
| Codex | Chosen when the task matches the `description` (documented) | Type `$recreate-puzzle-gameplay` in the prompt, or pick it from `/skills` (documented; not verified on this machine) |
| Claude Code | Chosen when the task matches the `description` (documented; the listing check showed the skills are visible) | `/recreate-puzzle-gameplay`, or name the skill in the prompt (documented; not verified on this machine) |

Skill text refers to other skills by ID only. When a referenced skill is not installed,
each skill states its fallback.

## Interpreters and scripts

- Skill prose writes `python3 <skill dir>/scripts/<name>.py`, with `<skill dir>` the skill
  directory's absolute path, so the working directory does not matter. On Windows the
  command may be `python` or `py -3`. Use whichever runs Python 3 (`python --version`).
  Quote paths that contain spaces or `+` (`"D:/games/Tile+Twister_312_APKPure.xapk"`).
- On macOS, `python3` may be the Xcode Command Line Tools interpreter (3.9) or Homebrew's;
  both work. Every script supports Python 3.9+.
- Bash scripts (`unity-apk-decompile`) run under Git Bash on Windows, for example
  `"C:/Program Files/Git/bin/bash.exe" -c 'source "<skill dir>/scripts/tools-env.sh" && ...'`,
  and under the stock `bash` on macOS (3.2 is enough) and Linux:
  `bash -c 'source "<skill dir>/scripts/tools-env.sh" && ...'`. Do not `source` it from zsh
  (the macOS default shell): it relies on `BASH_SOURCE`.
- Decompile phase: Windows, macOS (Intel and Apple Silicon) and Linux. `tools-env.sh` picks
  the platform layout itself (`unity-apk-decompile/INSTALLATION.md`, "Platform");
  `ensure_tools.py` downloads the matching pinned archive (`macos-arm64` on Apple Silicon).
- No script edits the system PATH or needs admin rights.

## Sub-agents and background waits

Skill bodies say "if your harness can spawn sub-agents ...; otherwise sequentially" and
"use the harness's background or monitor mechanism". What that means per harness:

| Harness | Sub-agents | Background work and waiting |
|---|---|---|
| OpenCode | Its agent-spawning tool starts a child session with its own context; give it the work directory, the phase skill ID and the files it may write | Shell commands can run in the background and notify on completion; wait on that notification |
| Codex | Current releases can spawn sub-agents. Codex does so when the prompt asks for it or when a skill or `AGENTS.md` instruction requests it (documented; not verified on this machine). Sub-agents inherit the parent's sandbox and approval settings. If none is available, run the pieces sequentially. | Not verified on this machine, and the documentation reviewed does not describe a background-wait mechanism. Run long commands in the foreground with a generous timeout. Wait for an asynchronous file (a pointer receipt) with one blocking `wait_for_file.py` call (below). |
| Claude Code | Its built-in agent tool spawns a sub-agent with its own context (documented; not verified on this machine) | Shell commands can run in the background and be watched with its monitor tool; sub-agents also start in the background by default (documented; not verified on this machine) |

In every harness: never poll with a sleep loop, and never start a sub-agent only to wait.
The allowed harness-neutral wait, when no background or monitor mechanism exists, is one
blocking call:
`python3 "<recreate-puzzle-gameplay skill dir>/scripts/wait_for_file.py" --path "<file>" --timeout <seconds> --min-size 1`.
It polls inside the script with a bound, prints JSON, and exits 0 when the file exists with a
size that is stable across two polls, or 4 on timeout. It uses only the Python standard library.
A sub-agent reads and writes files in the work directory. Its brief says: "do not run
`progress.py complete` or `reset`". The parent checks its outputs and runs `complete` itself.
