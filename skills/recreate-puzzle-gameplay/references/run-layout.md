# Run layout, phases and resume

Examples use the fictional game "Tile Twister" (slug `TileTwister`, APK
`D:/games/Tile_Twister_312_APKPure.xapk`, work directory `D:/games/TileTwister-recreation/`).
`<dir>` is the work directory; `<skill>` is this skill's directory.

## 1. Work directory

Default: `<directory containing the APK>/<GameSlug>-recreation/` (`progress.py` derives
the slug and the path; pass `--workdir` only to override). Every file below has one writer.

```text
<GameSlug>-recreation/
|-- progress.json            # progress.py (init, complete, reset) and ensure_tools.py (--progress "tools") only
|-- decisions.md             # every phase, append only (templates/decisions.md)
|-- intake.md                # this skill, phase intake (section 3)
|-- build-boundary.txt       # puzzle-gameplay-build: SHA-256 of Packages/manifest.json and
|                            #   ProjectSettings/*, Editor state before the phase
|-- decompile/               # unity-apk-decompile, with W=<dir>/decompile
|   |-- triage.json, paths.env   # unity_triage.py: backend, ABI, metadata version, ROUTE
|   |-- unpacked/                # base and split APKs unpacked
|   |-- il2cpp-out/              # dump.cs, script.json, stringliteral.json, il2cpp.h (IL2CPP)
|   |-- work/                    # targets.tsv, native-code/*.c, _index.tsv, ghidra-project/
|   `-- export/ExportedProject/Assets   # AssetRipper export
|-- evidence/                # puzzle-evidence-extraction
|   |-- levels/manifest.json     # the N selected base levels, path IDs, encoding chain, hashes
|   |-- levels/<name>.json       # decoded level data, original field names, bytes as decoded
|   |-- mechanics.md             # one labelled entry per mechanic
|   |-- visuals.md               # visual and audio inventory
|   `-- native/*.c               # pseudocode of every method read for a rule
|-- checks/<run-id>/         # puzzle-gameplay-verification, a new directory per run
|   |-- sources.sha256           # hashed source list at run start
|   |-- model.txt, model.log     # model contracts
|   |-- pointer-portrait.txt, pointer-landscape.txt        # receipts (line 1 PASS|FAIL|ABORTED)
|   |-- pointer-<orientation>-evidence/   # report.txt, console.txt, moves.txt, level-<n>-<o>-<W>x<H>.png
|   |-- scene-build.log          # puzzle-gameplay-build, batchmode scene route only
|   `-- verification-report.md
`-- handoff.md               # this skill, phase handoff (templates/handoff.md)
```

Writes outside the work directory, all logged in `decisions.md`:

| Path | Writer | Rule |
|---|---|---|
| `<project>/Assets/<GameSlug>/` (or `<GameSlug>Recreation/`) | build, verify | the only Unity folder you own |
| `<project>/Packages/manifest.json`, `ProjectSettings/ProjectSettings.asset` | build | only a required change, with a `CHANGE` line |
| `<project>/.agents/skills/<game-slug>-notes/SKILL.md` | this skill, game-notes | spec §2 output |
| the tool root (`ensure_tools.py` prints it), incl. `level-decoders-venv/` | `ensure_tools.py` | pinned installs only. With the ParkingLoop fallback root (`H:/UGame/ParkingLoop/tools`, used when it exists and `UNITY_DECOMPILE_TOOLS` is unset), `level-decoders-venv/` and any other missing tool land in that tree |
| `<project>/` as a new, empty Unity project | this skill, intake (section 3 step 4) | only when the given path is not a Unity project; spec §2 normally expects an existing project |

Nothing else in the project is created, changed, moved or deleted.

## 2. Phases

Run in this order. `next_phase` from `progress.py` names where to start.

| Phase | Skill to load | Reads | Writes | `complete --artifact` |
|---|---|---|---|---|
| `intake` | this skill (section 3) | APK, project | `intake.md`, `decisions.md` RECORD lines | `<dir>/intake.md` |
| `decompile` | `unity-apk-decompile` (section 4) | APK | `decompile/` | `<dir>/decompile/triage.json` and `dump.cs` (IL2CPP) or the ILSpy `.csproj` (Mono) |
| `level-catalog` | `puzzle-evidence-extraction` | `decompile/` | `evidence/levels/` | `<dir>/evidence/levels/manifest.json` |
| `mechanics` | `puzzle-evidence-extraction` | levels, `decompile/` | `evidence/mechanics.md`, `evidence/native/` | `<dir>/evidence/mechanics.md` |
| `visuals` | `puzzle-evidence-extraction` | export, references | `evidence/visuals.md` | `<dir>/evidence/visuals.md` |
| `build` | `puzzle-gameplay-build` | `evidence/` | `Assets/<GameSlug>/`, `build-boundary.txt` | `<project>/Assets/<GameSlug>/PROVENANCE.md` |
| `verify` | `puzzle-gameplay-verification` | project, `evidence/` | `checks/<run-id>/` | `<dir>/checks/<run-id>/verification-report.md` |
| `game-notes` | this skill (section 7) | all of the above | notes skill | `<project>/.agents/skills/<game-slug>-notes/SKILL.md` |
| `handoff` | this skill (section 8) | all of the above | `handoff.md` | `<dir>/handoff.md` |

Command shape, run after the phase's outputs exist:

```text
python3 <skill>/scripts/progress.py complete --workdir "<dir>" --phase <phase> --artifact "<file>" ["<file>" ...]
```

`complete` refuses an artifact that does not exist and records its SHA-256. Run it only
when the phase skill's own completion condition holds. `verify` completes when items 4 and 7
are PASS and the others are PASS, BLOCKED or NOT RUN with reasons; any FAIL goes back to
`build`, and item 4 or 7 NOT RUN or BLOCKED is the "Unity cannot open or compile" stop
(section 6): `verify` is not completed and the handoff is PARTIAL.

## 3. Intake

1. `progress.py init` has already hashed the APK and created the layout.
2. Read the project without changing it: `ProjectSettings/ProjectVersion.txt`; render
   pipeline and Input System (`Packages/manifest.json`, `activeInputHandler` in
   `ProjectSettings/ProjectSettings.asset`); packages; whether an Editor has the project
   open, and its loaded scenes with their dirty state; installed Editors that match the
   version; `git status --porcelain` (read only) if it is a repository; references given.
3. Write those values to `intake.md` and one `RECORD` line each to `decisions.md`.
   A dirty user scene is recorded here; it is never a question to the user.
4. Not a Unity project (no `ProjectSettings/ProjectVersion.txt`): spec §2 normally expects
   an existing project, so this is the exception. If the path is missing or an empty
   folder, and an installed Editor with `unity-cli` (or batchmode `-createProject`) can
   create a project there, do so and log a `CHANGE` line. A non-empty folder that is not a
   Unity project is never written into. Otherwise intake still completes and the run stops
   before `build` (section 6).

## 4. Tools and decompile

Tools, before every phase that uses decompile tools (`decompile`, `level-catalog`,
`mechanics`, `visuals`), also on resume:

- `python3 <skill>/scripts/ensure_tools.py --progress "<dir>"`. Root order is built in:
  `UNITY_DECOMPILE_TOOLS`, then an existing known tool directory, then
  `~/.cache/puzzle-recreation/tools`. Each tool is detected first; only missing tools are
  installed, from the pinned URL or `==` pins in `scripts/tools-manifest.json`, and an
  archive is kept only if its SHA-256 matches. Do not pick versions, URLs or folders
  yourself, and never use "latest". `--check` detects without installing (for planning).
- Then, in the shell that runs the decompile scripts, set `UNITY_DECOMPILE_TOOLS` to the
  `root` it printed. On Windows, the Bash scripts run in the Git Bash whose path `git-bash`
  printed; on macOS and Linux they run in `bash` (through `in_env.sh`; never `source tools-env.sh` by hand).
  `tools-env.sh` puts `<root>/dotnet` first on PATH when it exists. If the `dotnet` path
  `ensure_tools.py` printed is elsewhere and not on that shell's PATH, prepend its directory
  in that shell only.
- Exit 3 means a required tool is `failed` or `manual`. That is a stop (section 6): the
  `detail` is the exact unblock step, handed to the user. A `manual` detail starts with
  `stop: hand to the user —` and names a pinned, user-scope, no-admin install (.NET 10.0.15
  through `dotnet-install.ps1`/`dotnet-install.sh` into `<root>/dotnet`; PortableGit 2.56.1
  with its SHA-256 into `<root>/PortableGit`). Never run it yourself (spec §7.1). On macOS
  and Linux the system Git is acceptable; `git-bash` is checked on Windows only.
- macOS only: `ghidra-natives` (required) builds Ghidra's decompiler binary inside
  `<root>/ghidra-12.2` with Ghidra's own Gradle wrapper (Gradle 9.8.0, SHA-256 pinned, cache
  in `<root>/gradle-home`), because the Ghidra release has no macOS binary. It needs the Xcode
  Command Line Tools; without them it is `manual` (`xcode-select --install`, by the user).
- `level-decoders` needs Python 3.10+ to create its venv. On macOS, run `ensure_tools.py`
  with Homebrew's or python.org's `python3` when `/usr/bin/python3` is 3.9; otherwise it is
  `failed` with that instruction (optional tool, exit code stays 0).
- ilspycmd and PyYAML come from the tool root through `ensure_tools.py` (and
  `tools-env.sh`); never run `dotnet tool install -g` or an unpinned `pip install`.
- Decompile runs on Windows (Git Bash), macOS (Intel and Apple Silicon) and Linux;
  `tools-env.sh` selects the layout. On macOS, a tool that fails with `Permission denied`,
  `killed: 9` or a Gatekeeper dialog is fixed per `unity-apk-decompile`
  `references/troubleshooting.md` (macOS section) before it counts as a stop.
- Accepted deviation, disclosed in the handoff's Limits: pip pins use `==` without
  `--require-hashes`; `level-decoders` has never been installed live; `tpk-ar` builds from
  source during that install.
- `level-decoders` is optional (`required: false`): a venv in `<root>/level-decoders-venv/`
  with UnityPy, brotli and their dependencies, all pinned. Its failure leaves the exit code
  at 0. When it is `present` or `installed`, run `decode_probe.py` and any UnityPy reader
  with its interpreter (`Scripts/python.exe` on Windows, `bin/python` elsewhere) so the
  brotli step and raw object reads are available. When it `failed`, continue: append an
  `EVENT` line; the probe then reports `brotli-unavailable`, and a header-only export
  becomes a recorded gap or a stop as `puzzle-evidence-extraction` decides.

Decompile phase:

- Reuse: an existing decompile output is reused only when a record next to it names the
  same APK SHA-256 as `inputs.apk_sha256` (a `progress.json` of an earlier work directory,
  for example). A similar name, version string or date is not enough.
- Run triage with `<dir>/decompile` as its output directory, so `W=<dir>/decompile`.
- This phase covers triage, ROUTE, the metadata dump (or ILSpy for Mono) and the AssetRipper
  export. Targeted Ghidra decompiles of single methods belong to `mechanics` and `visuals`,
  which call `unity-apk-decompile` again for their method lists.

## 5. Resume

On every invocation, before any phase work:

1. **Find the run and its inputs before asking anything.**
   - Work directory given: `progress.py status --workdir <dir>` gives `inputs.apk`,
     `inputs.levels` and `inputs.project`.
   - Only an APK given: its default work directory is
     `<directory containing the APK>/<GameSlug>-recreation/`. Look for
     `<APK directory>/*-recreation/progress.json`; if one has `inputs.apk` equal to this APK,
     run `status` on it and take N and the project from it.
   - Only what is still missing after that is asked, once, at invocation.
2. **Re-check inputs.** `progress.py init --apk <apk> --levels <N> --project <project> [--workdir <dir>]`
   (or `resume --workdir <dir> --apk <apk> --levels <N> --project <project>`). It re-hashes
   the APK and compares N and the project path (normalized absolute forms).
   - Exit 2 (`refused`: `apk_sha256`, `levels` or `project`): stop and report the field and
     message; do not reuse the directory.
   - Exit 1 (`error`, for example the APK is not found or `progress.json` is unreadable):
     stop and report the message.
3. **Re-hash recorded artifacts.** `progress.py status` lists statuses only, not artifacts;
   this prints one line per artifact recorded in `phases.<phase>.artifacts`:

   ```text
   python3 -c "import json,hashlib,os,sys;d=json.load(open(os.path.join(sys.argv[1],'progress.json'),encoding='utf-8'));[print(p,'OK' if os.path.isfile(a) and hashlib.sha256(open(a,'rb').read()).hexdigest()==h else 'MISSING-OR-CHANGED',a) for p,s in d['phases'].items() for a,h in s['artifacts'].items()]" "<dir>"
   ```

   Apply this one rule, the same as in SKILL.md:

   | Finding | Action |
   |---|---|
   | A recorded artifact is missing or changed | Append an `EVENT` line. `python3 <skill>/scripts/progress.py reset --workdir "<dir>" --from <earliest such phase>`, then redo from the new `next_phase`, completing each phase in order. |
   | A done phase has no recorded artifacts, or an expected output of section 2 is missing | Append an `EVENT` line. Nothing is reset. Only the phase that actually needs that output regenerates it, as a targeted fix with the owning skill, when it gets there. No cascade. |
   | Everything else | Resume at `next_phase`. Do not redo or re-audit done phases. |

   `reset` sets that phase and every later phase to `pending` with no `completed_at`, note
   or artifacts, so an interrupted redo resumes at the right phase. An unknown phase name
   exits 2 and changes nothing.
4. **Read `decisions.md` in full.** Earlier `Inferred` lines stay in force. Append only.
5. **Continue at `next_phase`.** Its own outputs may be absent; that is expected.

A content gap you notice in a done phase's output (fewer levels than N, a cut-off file)
falls under the second row: an `EVENT` line and a targeted fix by the phase that needs
it; `verify` checks every level of N in the end.

After you change a done phase's artifact on purpose (an evidence row corrected, a
`PROVENANCE.md` row added while fixing a `verify` FAIL in `build`), run `complete` for that
phase again at once, so its hashes match.

A run whose phases are all done: the handoff stands only as long as the artifacts match.
One rule, the same as SKILL.md First actions step 2 and section 6: if `handoff.md` lists
BLOCKED or NOT RUN items whose condition is gone, run
`python3 <skill>/scripts/progress.py reset --workdir "<dir>" --from verify`, then rerun
`verify` (a new `checks/<run-id>/`), then `game-notes`, then the final handoff, running
`complete` for each.

## 6. Stops and partial handoff (spec §7)

Stop early only for:

| Blocker | Typical phase | Before stopping |
|---|---|---|
| Metadata encrypted or protected, no dump possible (`unity-apk-decompile` troubleshooting) | decompile | keep the triage output |
| A tool missing and its install failed or is `manual` (`stop: hand to the user —`) | decompile | keep the `ensure_tools.py` JSON; its `detail` is the unblock step |
| Unity cannot open or compile the project (no matching Editor, licence, compile errors not caused by your code) | build | finish `level-catalog`, `mechanics`, `visuals`: they need no Unity |
| No level data found | level-catalog | append an `EVENT` line listing every place searched |

Then: do not `complete` the blocked phase; append an `EVENT` line; write `handoff.md` from
the template with state PARTIAL and the stop point (phase, exact blocker with the command
and message, exact unblock step, resume command); give the chat summary. Never run
`complete --phase handoff` on a PARTIAL handoff: only the final handoff completes, so a
later invocation still resumes at the blocked phase.

Not a stop: pointer checks BLOCKED because a loaded user scene is dirty, or because enabling
the Input System needs an Editor restart over a dirty user scene. Run every other check,
record the pointer items as BLOCKED in the report, `complete` verify, write the notes and the
handoff, and `complete` both. BLOCKED is never reported as PASS. Never save, discard or
replace the scene, and do not ask about it. The unblock step in the handoff is exact:

1. The user saves or discards `<scene>` in the Editor (and, for the Input System case,
   restarts the Editor).
2. Invoke `recreate-puzzle-gameplay` again, or run
   `python3 <skill>/scripts/progress.py reset --workdir "<dir>" --from verify`.
3. The run then does `verify` (a new `checks/<run-id>/`), `game-notes`, and a re-rendered
   `handoff.md`, completing each phase.

On that new invocation the agent applies the section 5 rule itself: the handoff lists
BLOCKED or NOT RUN items whose condition is gone, so it runs `reset --from verify`, reruns
`verify`, then `game-notes`, then the final handoff with `complete`.

## 7. Game notes

Render `templates/game-notes/SKILL.md.txt` to
`<project>/.agents/skills/<game-slug>-notes/SKILL.md`. The rendering notes at the top of the
template give the slug conversion (`TileTwister` -> `tile-twister`, `2048Puzzle` ->
`2048-puzzle`). Fill it only from this run's files, then remove the rendering block.

## 8. Hand-off

Fill `templates/handoff.md` into `<dir>/handoff.md` from the final
`checks/<run-id>/verification-report.md`, `decisions.md`, `evidence/` and the build boundary
check. Then `complete --phase handoff --artifact <dir>/handoff.md` and post the chat summary.
