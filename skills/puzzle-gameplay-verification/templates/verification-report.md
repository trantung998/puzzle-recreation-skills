# Verification report: <GameSlug>, run <run-id>

Copy to `checks/<run-id>/verification-report.md`. Fill every cell. A blank cell, or a status
that is not one of the four below, means the report is not finished.

| Status | Meaning |
|---|---|
| PASS | Ran in this run, on the final code, and its receipt and report were read (`check_evidence.py` printed PASS where it applies). |
| FAIL | Ran and failed, or its evidence was missing, empty, stale or invalid. |
| BLOCKED | Could not run because of a condition outside the code, for example "Editor restart required; the open scene has unsaved user changes". Give the exact step that unblocks it. |
| NOT RUN | Not run for another reason (tool unavailable, Editor does not tick). Give the reason. |

BLOCKED and NOT RUN are not PASS and are not FAIL. Never write PASS for them.

## Run

- Run id and directory: `checks/<run-id>/`
- Run started (sources manifest written, after templates were adapted and compiled): `<ISO time>`
- `--since` (judge-time cutoff): newest source mtime under the `--sources` paths, recomputed when judging = `<ISO time>` (unity-control §9)
- Unity control used: `unity-pipeline` | `unity-cli` | batchmode `-executeMethod`
- Editor state before and after (Play Mode, Game View size, auto-tick, open and dirty scenes, `playModeStartScene`): `<before>` / `<restored>`

## Results (spec §4)

| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 1 | Every level loads; data matches the original after decode | | `model.txt` lines `level-<n>-data`; `level-<n>` in `report.txt` | `contracts=<n> failed=<m> data=<k> coverage=<c>` |
| 2 | Every mechanic used by the N levels touched by real pointer input | | `report.txt` lines `mechanic-<id>` | mechanic ids covered: |
| 3 | Sample level won by real input | | `report.txt` `sample-win`, `moves.txt` | solution source: video `<file>` / agent-derived |
| 4 | Independent model contract per mechanic, incl. reject and boundary | | `model.txt` | |
| 5 | Screenshots per level, portrait and landscape | | `*-portrait-*.png`, `*-landscape-*.png`, comparison sheet | |
| 6 | Level switching: select, next, previous (both wraps), retry, clean reset | | `report.txt` lines `switch-*`, `ui-blocks-gameplay` | |
| 7 | Clean compile; final console free of errors | | compile result, console counts below | |

## Receipts

| Run | Receipt | Line 1 | `check_evidence.py` | Problems |
|---|---|---|---|---|
| model contracts | `model.txt` (judged by `--model` in the receipt rows below) | n/a | | |
| pointer smoke, portrait | | | | |
| pointer smoke, landscape | | | | |

Command used (full set in SKILL.md Procedure step 5; record the judge-time `--since`, `skipped` must be empty): `python3 <skill dir>/scripts/check_evidence.py --strict --receipt <path> --since <ISO time> --expect-levels <N> --require-checks ... --per-level-images "level-{n}-<orientation>-*.png" --model <model.txt> --sources <paths> --sources-manifest <file>`

## Console ground truth (final)

- Compile: `<succeeded | failed>`; errors `<n>`; warnings `<n>`.
- Warnings listed: `<each warning, or "none">`.
- Retained historical log entries explained: `<entry and why it is not from this run, or "none">`.

## Visual matrix

| Level | Portrait (W×H) | Landscape (W×H) | Reference | Verdict |
|---|---|---|---|---|
| 1 | | | photo/video frame `<file>@<time>` or original asset rendered in Unity | |

A raw pixel difference is a diagnostic only. Say what was compared and what differs
(geometry, colors, attachments, outline, clipping), and name shaders as reconstructed.

## Sample level

- Level, source of the move list, number of moves, `moves.txt` path.

## Earlier runs (not counted)

Results from earlier runs, READMEs or other reports appear only here, each with its date
and the code state it described. They are never copied into the tables above.

- `<date>`, `<path>`, `<code state it described>`: `<its result>`.
  receipt: `<path>` — not re-read/judged in this run; to count it, rerun and judge with check_evidence.py --strict

## Not run or blocked

| Item | Status | Reason | Unblock step |
|---|---|---|---|

## Limits

Editor smoke does not prove a standalone Player, physical touch behavior, device notches,
exact original shader output, or puzzle solvability beyond the sample level.
