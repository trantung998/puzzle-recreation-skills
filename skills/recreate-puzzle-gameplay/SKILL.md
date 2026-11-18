---
name: recreate-puzzle-gameplay
description: Use when asked to recreate, clone or rebuild the gameplay of an Android Unity puzzle game (APK, XAPK, APKS, APKM) in a Unity project for its first N levels with level switching, or to continue, resume or hand off such a run from its work directory (progress.json, decisions.md). Also for tái tạo gameplay game puzzle Unity từ APK, làm lại N level đầu, chuyển level, tiếp tục lần chạy bị ngắt, bàn giao.
---

# Recreate puzzle gameplay

Nine phases from APK to handoff, asking nothing mid-run. `<dir>`: the work directory;
`<skill>`: this skill's directory. Details: [run layout](references/run-layout.md).

## Inputs

Required: APK/XAPK/APKS/APKM path, level count N, Unity project path. Optional: reference
images/videos. Take missing values from an existing run first (run layout §5); ask once,
at invocation, for any still missing. Never ask later.

## First actions, every invocation

1. `python3 <skill>/scripts/progress.py init --apk <apk> --levels <N> --project <project> [--workdir <dir>] [--references <files>]`
   resumes a run or refuses changed inputs. Exit 2 or 1: stop, reporting `refused` or `error`.
2. Re-hash the recorded artifacts (run layout §5). One missing or changed:
   `progress.py reset --workdir <dir> --from <phase>`, redo. None recorded, or an expected
   output missing: `EVENT` line; only the phase needing it regenerates it, no cascade. All
   done but `handoff.md` lists BLOCKED/NOT RUN items whose condition is gone: `reset --from
   verify`; redo verify, game-notes, final handoff, each `complete`d. Else resume at `next_phase`.
3. Read `decisions.md`. Append only.

Never edit `progress.json` by hand.

## Run loop

From `next_phase`: load the phase skill, do the phase, then
`python3 <skill>/scripts/progress.py complete --workdir <dir> --phase <phase> --artifact <file>`.
Changed a done phase's artifact (a `verify` fix)? `complete` it again.

| Phase | Skill |
|---|---|
| intake, game-notes, handoff | this skill (run layout §3, §7, §8) |
| decompile | `unity-apk-decompile` |
| level-catalog, mechanics, visuals | `puzzle-evidence-extraction` |
| build | `puzzle-gameplay-build` |
| verify | `puzzle-gameplay-verification` |

Before `decompile`, `level-catalog`, `mechanics` and `visuals`, run
`python3 <skill>/scripts/ensure_tools.py --progress <dir>`. It picks the tool root and
installs only missing tools, pinned and hash-checked. Never pick versions, paths or
"latest". Exit 3: stop (run layout §6); each `detail` is the user's unblock step, never
run by you. Optional `level-decoders` failed: continue (run layout §4).

## Decide, record, continue

Evidence missing: choose the most reasonable value and append its `Inferred` line
([format](templates/decisions.md): reason, evidence searched) to `<dir>/decisions.md`
before using it. Recording later does not count.

## Stops

Stop early only for: encrypted metadata with no dump; a failed tool install; Unity cannot
open or compile the project; no level data. Finish phases that do not need it, then write
a PARTIAL handoff (never `complete` it) with the exact blocker and unblock step.

Pointer checks BLOCKED (dirty user scene, needed Editor restart): run the other checks,
continue, hand off the unblock step (run layout §6). BLOCKED is never PASS. Never
commit, stash or reset git, or save or discard user scenes.

## Sub-agents and waits

If your harness can spawn sub-agents, hand one a phase with `<dir>` and tell it not to run
`complete`; you check and run it. Otherwise work sequentially. Wait with the
harness's background or monitor mechanism, else one `wait_for_file.py` call; never sleep loops.

## Hand-off

Fill [the handoff template](templates/handoff.md) from the final run; summarize in chat. Harness setup: [compatibility](references/compatibility.md).

## Red flags

| Thought | Reality |
|---|---|
| "Here the brief is this file." | Append to `decisions.md` now. |
| "Missing evidence; redo earlier phases." | Only a failed artifact resets phases. |
| "Only decision: save Main first?" | Never ask; pointer checks BLOCKED. |
| "Already verified." | Only this run's final verification counts. |
| "`searched:` items carried over from earlier phases." | List only searches you ran or cite by file. |
| "Label it observed / inferred / unknown (decompile skill)." | Labels follow `puzzle-evidence-extraction`: a branch you read is `Proven`. |
