# Running the checks: Unity control, receipts, evidence

Examples use a fictional game "Tile Twister" (slug and namespace `TileTwister`, `<Id>` in the
build skill). Entry points below are the adapted templates, in namespace `<Id>.EditorTools`.
Every command shape here is unverified: read the installed control skill's current command
descriptions before using it, because flag names change between versions.

## 1. Choose the control route

1. `unity-pipeline` skill: an Editor has the project open. Compile, run an Editor method,
   enter Play Mode, read the console, set the Game View size, capture.
2. `unity-cli` skill: the same, through the Unity command line tool.
3. Batchmode, only when no Editor has the project open (a second process cannot open the same
   project, and that is no reason to close the user's Editor):
   `<Unity> -batchmode -projectPath <project> -executeMethod <Id>.EditorTools.ModelContractRunner.RunBatch -checksDir <workdir>/checks/<run-id> -logFile <workdir>/checks/<run-id>/model.log -quit`
   A licence is required. Exit code 0 means nothing failed; still read `model.txt`. Compile
   errors show as `error CS` in the log; with them the method never ran.
   `<Unity>` is the Editor executable for the project's `m_EditorVersion`, under Unity Hub's
   default install folders:

   | OS | `<Unity>` | Interactive Editor log |
   |---|---|---|
   | Windows | `C:\Program Files\Unity\Hub\Editor\<version>\Editor\Unity.exe` | `%LOCALAPPDATA%\Unity\Editor\Editor.log` |
   | macOS | `/Applications/Unity/Hub/Editor/<version>/Unity.app/Contents/MacOS/Unity` (the binary inside the bundle, never `open Unity.app`, which drops the arguments and returns at once) | `~/Library/Logs/Unity/Editor.log` |
   | Linux | `~/Unity/Hub/Editor/<version>/Editor/Unity` | `~/.config/unity3d/Editor.log` |

   A custom Hub install location moves the Editor folder; `unity-cli` lists installed Editors.

Use the exact project path when choosing an Editor: a neighbouring project with a similar name
is a different Editor.

## 2. Preserve the session

Before changing anything, record: Play Mode, Game View size, auto-tick or run-in-background,
open scenes with `isDirty`, active scene, `EditorSceneManager.playModeStartScene`. Restore
each at the end and write both values into the report. The user's open scene is never saved,
closed, reloaded, discarded or replaced (`puzzle-gameplay-build` project integration).
`PointerSmoke` plays the gameplay scene through `playModeStartScene` and puts the previous
value back when the run ends (also after ABORTED or `Cancel()`). It refuses to start while any
loaded scene is dirty: `Start` throws a message saying the pointer checks are blocked. That is
BLOCKED in the report, with the unblock step "the user saves or discards the open scene, then
the run is repeated". Do not ask mid-run, and do not save the scene yourself.

## 3. Entry points

| Entry point | Purpose |
|---|---|
| `ModelContractRunner.Run(dir)` | Edit Mode, no scene; writes `model.txt` (always, even if building the contract list throws); returns `contracts=<n> failed=<m> data=<k> coverage=<c>` |
| `ModelContractRunner.Run()` | Same; directory from `-checksDir` or `PUZZLE_CHECKS_DIR`, else a fresh temp directory whose path is printed (copy `model.txt` into `checks/<run-id>/`) |
| `ModelContractRunner.RunBatch()` | Same for `-executeMethod`; exit code 0 only when `failed=0` |
| `PointerSmoke.Start(receipt)` | Asynchronous Play Mode run; writes the receipt last; refuses a dirty scene |
| `PointerSmoke.Cancel()` | Ends a stuck or unwanted run: ABORTED receipt, state restored, phase cleared |
| `PointerSmoke.StartFromCommandLine()` | Batchmode variant, see section 6 |
| `python3 <skill dir>/scripts/check_evidence.py --strict --receipt <path> ...` | Judges a receipt, `model.txt` and the sources from files (flags: SKILL.md Procedure step 5) |

In the summary, `contracts` counts only claim-row contracts. Level data lines are `data`,
`coverage.*` lines are `coverage`, and `failed` counts failed lines of every kind, so judge by
`failed=0` and by `contracts` being at least the number of claim rows you wrote (zero contracts
is itself a FAIL line). `check_evidence.py --model` checks the same file for FAIL lines, a contract line
and a PASS `level-<n>-data` line for every level 1..N (with `--expect-levels`).

Example shape, with a fresh directory (create the parent first and confirm the receipt does
not exist):

```csharp
return TileTwister.EditorTools.PointerSmoke.Start("D:/games/TileTwister-recreation/checks/20261117T120000/pointer-portrait.txt");
```

## 4. Compile and lifecycle

1. Leave Play Mode before editing or recompiling runtime C#.
2. Request the recompile through the control skill, wait for its completion notification, and
   read the result (`compilationFailed`, diagnostics). A submitted request is not a compile.
3. Start a fresh Play session for each pointer run. A domain reload inside Play Mode ends the
   run as ABORTED (the template detects it). Fix the lifecycle, not the production code: do not
   add fallbacks for stale runtime references.
4. If the Editor restarted, check readiness, Play state and auto-tick again before the next run.

## 5. Asynchronous receipts

`PointerSmoke.Start` returns immediately; a returned string or a zero exit code means only
that the run began.

- Use the harness's background or monitor mechanism. Arm a watcher on the receipt path
  before starting the run. Do not poll in a sleep loop, and do not start a worker only to wait.
- No background or monitor mechanism (Codex, for example): after starting the run, make one
  blocking call, `python3 <recreate-puzzle-gameplay skill dir>/scripts/wait_for_file.py --path
  "<receipt>" --timeout <bound in seconds> --min-size 1`. It polls inside the script and
  returns once: exit 0 and `"status": "found"` when the file exists with a stable size, exit 4
  on timeout (then the timeout rule below applies). It is one tool call, not a sleep loop in
  your turn.
- If a run is active after your context was compacted, keep its receipt path and wait on it.
  Do not start a duplicate: `Start` refuses while one is active.
- Read the receipt, then `report.txt`, then run `check_evidence.py`. PASS comes from that
  script's JSON, not from the file existing. FAIL and ABORTED are not PASS.
- No receipt after the time you allowed (give it a generous bound, for example 3 times the
  expected duration) means NOT RUN with the reason. It is never PASS. Before reporting that,
  call `PointerSmoke.Cancel()` (an ABORTED receipt, so the stuck phase does not block the next
  `Start`), then read `report.txt` for the earliest FAIL.
- Compile errors stop Play Mode from starting: the template writes an ABORTED receipt when the
  Editor returns to Edit Mode while the run is still "starting" (compile errors, a cancelled
  dialog, Stop). Fix the compile errors first.

## 6. Pointer smoke needs an Editor that ticks

`PointerSmoke` advances on `EditorApplication.update` and needs `Time.frameCount` to move.

Interactive Editor (normal route):

- A Game View exists and is visible. Set its size through the control skill (portrait first,
  then landscape) and run once per size, each with its own receipt. The PNG names carry the size.
- The Editor must keep ticking while unfocused: use the control skill's auto-tick or
  keep-alive option, or keep the Editor focused. The template also sets
  `Application.runInBackground` and relaxes the Input System background and Game View focus
  behavior for the run, and writes the originals back afterwards. Property names differ by
  package version.
- Input System update mode (`InputSystem.settings.updateMode`): in `ProcessEventsManually` the
  driver calls `InputSystem.Update()` after each queued event, because nothing is processed
  otherwise. In `ProcessEventsInFixedUpdate` it waits `Time.fixedDeltaTime` plus one frame
  between press and release so both are not processed in one fixed step. Dynamic update (the
  default) needs only the frame waits. Check which mode the project uses.
- Do not touch the real mouse during the run: it can become `Mouse.current`.
- The first failure to read is the earliest FAIL line. A `TimeoutException` mentioning
  `Time.frameCount` means the Editor is not ticking. Fix that condition. Do not call the run
  flaky, add retries or loosen an assertion.

Dirty scene, or Input System not active, or enabling it needs a restart (all BLOCKED):

- Any loaded scene with unsaved changes makes `PointerSmoke.Start` throw before anything
  changes. Run what does not need Play Mode, report the pointer items as BLOCKED, and put the
  unblock step in the handoff.

- The Input System is required. If `activeInputHandler` was changed it takes effect after an
  Editor restart. Never quit an Editor holding a dirty scene you did not create. Run what does
  not need the restart (compile, model contracts, screenshots by other means) and report the
  pointer items as BLOCKED with the reason "Editor restart required; the open scene has unsaved
  user changes" and the exact unblock step. Do not ask the user mid-run.

Batchmode pointer smoke (unproven):

- `<Unity> -batchmode -projectPath <project> -executeMethod <Id>.EditorTools.PointerSmoke.StartFromCommandLine -pointerSmokeReceipt <path> -logFile <log>`
  Omit `-quit` (the run is asynchronous; the template exits the process after the receipt) and
  omit `-nographics` (screenshots need a graphics device). Only when no Editor has the project open.
- If Play Mode does not start, frames do not advance, or no receipt appears within the bound,
  the pointer checks are NOT RUN. Say so; never substitute a model-only result.

## 7. Console ground truth

Collect, after the final run, from the control skill: whether compilation failed, the
console error count and the warning count with the warning text. Without a console command:
the Editor log (per-OS path in §1), or the batchmode `-logFile`, searched for `error CS`, `Exception` and `Error`.

Two sources are reported separately: per-run errors (`console` line and `console.txt`) and the
current console. Retained older entries that differ from the current counts are named and
explained, not hidden. A real final-run error is never explained away.

## 8. Visual evidence

- Capture at the actual Game View size and record it. A generic capture once returned the
  wrong size, so read the PNG's dimensions.
- `PointerSmoke` hides the level switcher (a recreation tool) before each capture and
  restores it. A screenshot request does not mean pixels were flushed: the template treats a PNG
  as ready only when its size is the same across two polls and it starts with the PNG signature.
- `check_evidence.py --require-images` checks signature, size and header, not content. Open
  the images: blank, black or stale frames pass the script.
- With a reference photo or video: crop the matching frame, put it beside the capture, keep
  both full images, note any normalization. Raw pixel scores are diagnostics only.
- Without one: render the original prefab, mesh or sprite with its original material in an
  Editor preview scene (for example `PreviewRenderUtility`) and put that beside the capture.
  Label it "original asset rendered in Unity", never "original game screenshot".
- Keep any in-memory fixture (forced colors or positions) labelled as QA setup. Never write it
  into the delivered level JSON.
- After a rendering change, redo every affected capture. Reuse only checks whose inputs did not change.

## 9. Freshness cutoff

`<paths>` (SKILL.md step 1) are absolute, so the working directory does not matter:

- `<project>/Assets/<GameSlug>/` (code, scene, assets, and the level resources when they live
  there; add any level resource path outside it), and `<project>/Packages/manifest.json`.
- `<project>/ProjectSettings/ProjectSettings.asset` (input handler) and
  `<project>/ProjectSettings/EditorBuildSettings.asset`, each only if the build changed it and
  `build-boundary.txt` lists it. Not the whole `ProjectSettings/`: Unity rewrites other
  settings files on its own (Editor open, version upgrade, Game View), which would fail the
  manifest and mtime checks without any change of ours.

`--since` has one definition: the newest mtime under `<paths>`, recomputed when you judge,
not before the run. An edit made during the run moves it, and the run's older screenshots
and receipts then fail. Print it:

```text
python3 -c "import os,sys,datetime as d;fs=[os.path.join(r,f) for p in sys.argv[1:] for r,_,n in (os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p),0,[os.path.basename(p)])]) for f in n];print(d.datetime.fromtimestamp(max(map(os.path.getmtime,fs))).astimezone().isoformat())" "D:/projects/Puzzles/Assets/TileTwister" "D:/projects/Puzzles/Packages/manifest.json"
```

(Use `python` instead of `python3` on Windows.) Run `check_evidence.py` with `--since <that value>`
and with `--sources <paths>`, which fails when any source is newer than the receipt. A deleted
file changes no mtime, so `--write-sources-manifest` at run start and `--sources-manifest` when
judging compare the hashed file list and fail on any added, removed or changed file. Any edit
afterwards, even a comment, means the checks are redone. The report records the cutoff and the
run start.

## 10. Finish

Restore what you changed: Play Mode, Game View size, auto-tick, `playModeStartScene`, the
Input System settings the template relaxed. Report what passed, what was blocked or not run
and why, and the evidence directory. Editor smoke does not prove a standalone Player,
touch hardware, device notches, exact original shader output or every puzzle's solvability.
