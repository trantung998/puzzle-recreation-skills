---
name: puzzle-gameplay-verification
description: Use when proving a recreated Unity puzzle game is done or re-running its checks - model contracts, real Input System pointer smoke, sample level won, level switching, portrait and landscape screenshots, console state - or when asked whether an earlier PASS, receipt, README or report still counts. Also for kiểm chứng gameplay, chạy lại kiểm thử, smoke test bằng input thật, chụp ảnh so sánh, báo cáo kết quả kiểm chứng.
---

# Puzzle gameplay verification

## Overview

Phase `verify`: decides whether the recreation in `Assets/<GameSlug>/` is done. Only the result
of the **last run, on the final code and assets** counts. The C# in `templates/csharp/` is
unverified template text: adapt and verify it first. Commands and Editor handling: [Unity control](references/unity-control.md).

## Inputs

- `progress.json` (`slug`, `inputs.levels` = N), `evidence/mechanics.md` (claim rows), `evidence/levels/manifest.json`, and optional reference photos or video.
- Build output: `LevelCatalog`, `IGameSession`, `LevelSwitcherOverlay` (fixed names). Code indices are 0-based; check ids are `level-<index+1>`.
- Every run goes into a fresh `checks/<run-id>/`. Never reuse one. `<skill dir>`: this skill's folder.

## What "done" means

All seven, on the final run:

- [ ] 1. Every level of the N loads without error; count, kind, position and attributes of its elements match the original data (semantic comparison after decode, not a byte hash).
- [ ] 2. Every mechanic that appears in a level is interacted with at least once by **real input**: Unity Input System pointer events through the real raycast or collider. A direct method call is setup, not interaction.
- [ ] 3. One sample level is played to the win screen by real input. The moves come from the video if there is one; otherwise you find a solution and record the move list.
- [ ] 4. Every mechanic has an independent model contract, including rejected cases and boundaries. Expected results come from the original evidence, not from the code you just wrote.
- [ ] 5. A screenshot of every level, portrait and landscape. With a reference photo or video, put them side by side; without one, compare against the original prefab or asset rendered in Unity.
- [ ] 6. Level switching: select any level, next, previous (wrapping at both ends), retry. State resets cleanly: pending input, per-level booster and inventory.
- [ ] 7. The project compiles cleanly and the final console has no errors; warnings are listed.

## Statuses

Every item ends as exactly one of PASS, FAIL, BLOCKED or NOT RUN
([report template](templates/verification-report.md)). BLOCKED and NOT RUN are not PASS and not
FAIL, and carry a reason and an unblock step. Pointer checks are BLOCKED when a loaded scene is
dirty (the run refuses to start; it never saves or discards a user scene) or an Editor restart
would be needed over one. A pointer smoke the Editor cannot tick is NOT RUN.

## Never count

- A PASS from an earlier run, a README, a report or another session. It may appear only under "Earlier runs (not counted)" with its date and the code state it described. Any mention of a pointer receipt names its path and says whether this run judged it.
- A queued or launched command, a launcher's zero exit code, a screenshot directory, an empty evidence directory, or a receipt that is FAIL or ABORTED.
- Level-file hash matches (they cover data only), or anything older than the newest code or asset change. After any edit, redo the checks.

## Procedure

0. **Prepare.** Adapt `ModelContractRunner` (every `mechanics.md` claim row incl. `reject`/`boundary`, and a `CompareLevel` reading the raw file independently) and the `PointerSmoke` hooks. Compile outside Play Mode via the control route (`unity-pipeline`, `unity-cli`, else batchmode `-executeMethod`); wait until compile and import finish; read the result.
1. **Run start.** Create `<dir>/checks/<run-id>/`, record Editor state, then `python3 <skill dir>/scripts/check_evidence.py --write-sources-manifest <dir>/checks/<run-id>/sources.sha256 --sources <paths>`. `<paths>`: absolute sources, unity-control §9.
2. **Freeze.** From here on, any source edit means a new run from step 0.
3. **Model contracts** (items 1, 4): run `ModelContractRunner` into `checks/<run-id>/`; read `model.txt`.
4. **Pointer smoke** (items 1, 2, 3, 5, 6): run it once portrait and once landscape, each with its own receipt, started before you wait. It selects every level through the switcher grid, runs `switch-*`, `ui-blocks-gameplay`, one `mechanic-<id>` per mechanic and `sample-win`, and captures PNGs. A null switcher button fails the step; it is never skipped.
5. **Judge each receipt at judge time.** `--since` is always the newest source mtime under `<paths>`, recomputed now (unity-control §9). Per receipt, with `<o>` = `portrait` or `landscape`:
   `python3 <skill dir>/scripts/check_evidence.py --strict --receipt <receipt> --since <cutoff> --expect-levels <N> --require-checks "level-*" "switch-*" "ui-blocks-gameplay" "mechanic-*" "sample-win" "console" --per-level-images "level-{n}-<o>-*.png" --model <dir>/checks/<run-id>/model.txt --sources <paths> --sources-manifest <dir>/checks/<run-id>/sources.sha256`
   PASS: that JSON with empty `problems` and `skipped`, and `report.txt` read.
6. **Look at the images** (item 5). Fill the visual matrix. Name shaders "reconstructed" when they are.
7. **Console ground truth** (item 7): compile state, error and warning counts now, and the per-run `console` line. Explain retained older entries; do not hide real ones.
8. **Report** in `checks/<run-id>/verification-report.md`. Restore the Editor state you changed.

A FAIL goes back to the `build` phase with `systematic-debugging` if installed. Fix the cause. Do not add
retries, clamps, fallback materials or extra rotations, and do not weaken an assertion or enlarge a timeout.
After the fix, run the whole procedure again: only the last run counts.

## Per-level, sample and switching checks

- Per level: `level-<n>` PASS needs a pointer-selected load, no errors logged, and a capture. `--expect-levels N` and `--per-level-images` check every level.
- Sample level: record `moves.txt` (source line, then each move). A solution you derived is `Inferred`: add a `decisions.md` line. It proves that level's win path only.
- Real input: a probe that sends no pointer event fails. `ui-blocks-gameplay` clicks a switcher button placed over the board; the button must take the click and the board must not change.
- Switching: `switch-*` (next, previous, both wraps, retry, clears input) compare board, pending input and inventory with a fresh load. With N = 1, next and previous wrap to level 1 (a reload); that is the PASS.

## Completing the phase

Before claiming done, use `verification-before-completion` if installed; else cite this run's JSON per PASS.
When items 4 and 7 are PASS and the others are PASS, or BLOCKED or NOT RUN with reasons in the report:
`python3 <recreate-puzzle-gameplay skill dir>/scripts/progress.py complete --workdir <dir> --phase verify --artifact <dir>/checks/<run-id>/verification-report.md`.
Any FAIL: do not complete; go back to `build`. Item 4 or 7 NOT RUN or BLOCKED: do not complete; it is a stop
(Unity cannot open or compile the project), and the handoff is PARTIAL. Without that skill, keep the same
layout and say that progress was not recorded.

## Common mistakes

| Rationalization | Reality |
|---|---|
| "The user said it is already verified." / "`Verification-<range>.md` says PASS." | A claim, and history. Check it against the final code and list it under "Earlier runs (not counted)"; otherwise write "verified `<date>` on an earlier code state; re-verification pending". |
| "The Editor is not running, so I will report the earlier result." | Unrun items are NOT RUN with the reason. Never fill them with an old PASS. |
| "The evidence folder has screenshots" / "the command was accepted." | Wait for the receipt, read `report.txt`, and run `check_evidence.py --strict`. |
| "The level hashes match, so levels are verified." | Data only. Items 1 to 3 need model contracts and pointer input. |
| "Calling `Tap()` on the model is enough." | A direct call is setup. Send pointer events. |
| "It is flaky: retry or raise the timeout." | Find the failing step and its condition (Editor not ticking, stale reference). Change that. |
| "The expected value is what the model returns." | Take it from the claim row's exact source. |