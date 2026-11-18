# Handoff: <Game Name> (<GameSlug>), levels 1-<N>

<!-- Template for <workdir>/handoff.md (spec §8). Replace every <...>. Delete these comments.
     Results come only from the FINAL run: checks/<run-id>/verification-report.md of this
     work directory, on the final code and assets. Never copy a PASS from an earlier run,
     a README, a report or another session into the tables; those go under "Earlier runs".
     The chat summary repeats: overall state, the results table, blocked/not-run items with
     their unblock steps, the Inferred count with the path to this file. -->

## Run

| Field | Value |
|---|---|
| Overall state | COMPLETE (all seven items PASS) / COMPLETE WITH EXCEPTIONS (items 4 and 7 PASS; the others PASS, BLOCKED or NOT RUN) / PARTIAL (stopped at phase `<phase>`; every other mix, e.g. item 4 or 7 NOT RUN or BLOCKED, or item 7 PASS with items 1-6 NOT RUN) |
| Source build | `<apk path>`, SHA-256 `<inputs.apk_sha256>` |
| Levels | first `<N>` base levels (`evidence/levels/manifest.json`) |
| Target project | `<project path>`, Unity `<version>`, pipeline `<Built-in/URP/HDRP>` |
| Work directory | `<workdir>` |
| Final verification run | `checks/<run-id>/` started `<ISO time>`; newest code/asset change `<ISO time>` |
| Phases done | `<output of progress.py status: phase -> status>` |

## Stop point (PARTIAL only)

- Phase: `<phase>`; blocker: `<exact condition, with the command and the message it printed>`
- Unblock step: `<exact action for the user>`
- Resume: after the unblock step, invoke `recreate-puzzle-gameplay` again with the work directory; it runs `python3 <skill dir>/scripts/progress.py resume --workdir "<workdir>" --apk "<apk>" --levels <N> --project "<project>"` and continues at `<next_phase>`.
- This PARTIAL handoff is not recorded with `progress.py complete`; only the final handoff is.

## Files added or changed

| Path | Kind | Note |
|---|---|---|
| `<project>/Assets/<GameSlug>/` | added | gameplay, levels, imported assets, `PROVENANCE.md` |
| `<project>/.agents/skills/<game-slug>-notes/SKILL.md` | added | game notes skill |
| `<project>/Packages/manifest.json` | changed / untouched | `<dependency added, from decisions.md CHANGE line>` |
| `<project>/ProjectSettings/ProjectSettings.asset` | changed / untouched | `<setting, old -> new>` |
| `<other file from the build boundary check>` | `<created by package install / written by Unity on open>` | `<listed, not reverted>` |

The boundary check compared against `<workdir>/build-boundary.txt`: `<result>`.

The notes skill is found by OpenCode and Codex when started inside the project. Claude Code
ignores `<project>/.agents/skills`: to use it there, link
`<project>/.claude/skills/<game-slug>-notes` to `<project>/.agents/skills/<game-slug>-notes`
yourself (junction on Windows: `mklink /J "<link>" "<target>"` from `cmd`; `ln -s` on Unix).
The run does not create that link.

## Mechanics and evidence labels

| Mechanic | Levels | Rule (one line) | Label | Source |
|---|---|---|---|---|
| `<id>` | `<level numbers>` | `<rule>` | Proven / Observed / Inferred / Unknown | `<evidence/native/<file>.c, method, RVA>` |

Full claim rows: `evidence/mechanics.md`.

## Verification results (final run only)

Status is exactly one of PASS, FAIL, BLOCKED, NOT RUN. BLOCKED and NOT RUN are never PASS.
If the run stopped before `verify`, every item is NOT RUN with the reason "run stopped at
phase `<phase>`".

| Check | Status | Evidence | Reason and unblock step (if not PASS) |
|---|---|---|---|
| 1 Every level loads; data matches the original | | `model.txt` `level-<n>-data`, `report.txt` `level-<n>` | |
| 2 Every mechanic touched by real pointer input | | `report.txt` `mechanic-<id>` | |
| 3 Sample level won by real input | | `report.txt` `sample-win`, `moves.txt` | |
| 4 Model contracts per mechanic, incl. reject/boundary | | `model.txt` (`contracts=<n> failed=<m>`) | |
| 5 Screenshots per level, portrait and landscape | | `<receipt>-evidence/*.png` | |
| 6 Level switching: select, next, previous, wraps, retry, reset | | `report.txt` `switch-*`, `ui-blocks-gameplay` | |
| 7 Clean compile; final console without errors | | compile `<result>`; errors `<n>`, warnings `<n>`: `<list>` | |

Status counts: PASS `<n>`, FAIL `<n>`, BLOCKED `<n>`, NOT RUN `<n>`.

## Visual comparison

| Level | Portrait | Landscape | Compared with | Verdict |
|---|---|---|---|---|
| `<n>` | `<png>` | `<png>` | reference `<file>@<time>` / original asset rendered in Unity | `<what matches, what differs>` |

Shaders built from AssetRipper placeholders are named "reconstructed": original materials
and textures with a reconstructed shader.

## Inferred decisions

Every line of `decisions.md` that contains `| Inferred |`, unchanged:

```text
<lines>
```

## Not run or blocked

| Item | Status | Reason | Exact unblock step |
|---|---|---|---|
| Pointer checks (items 2, 3, 5, 6) | BLOCKED | `<a loaded user scene has unsaved changes>` / `<Editor restart required to enable the Input System; the open scene has unsaved user changes>` | `<save or discard <scene path> in the Editor yourself (restart the Editor for the Input System case); then invoke recreate-puzzle-gameplay again: it runs progress.py reset --workdir "<workdir>" --from verify, then verify, game-notes and a new handoff>` |
| `<item>` | NOT RUN | `<tool unavailable, Editor does not tick, ...>` | `<step>; then invoke recreate-puzzle-gameplay again: it runs progress.py reset --workdir "<workdir>" --from verify, then verify, game-notes and a new handoff>` |

On the next invocation, when the condition behind every BLOCKED or NOT RUN item above is
gone, the run applies one rule (run layout §5): `progress.py reset --from verify`, rerun
`verify`, then `game-notes`, then the final handoff, running `complete` for each.

## Evidence paths

- Work directory: `<workdir>`
- Decisions: `<workdir>/decisions.md`
- Evidence: `<workdir>/evidence/` (levels, `mechanics.md`, `visuals.md`, `native/`)
- Final run: `<workdir>/checks/<run-id>/` (`verification-report.md`, receipts, `report.txt`, images)
- Provenance: `<project>/Assets/<GameSlug>/PROVENANCE.md`

## Editor state

| Item | Before | Restored to |
|---|---|---|
| Play Mode | | |
| Open scenes and dirty state | | |
| Active scene | | |
| `EditorSceneManager.playModeStartScene` | | |
| Game View size | | |
| Auto-tick / run in background | | |

## Earlier runs (not counted)

- `<date>`, `<path>`, `<code state it described>`: `<its result>`. Historical only.
  receipt: `<path>` — not re-read/judged in this run; to count it, rerun and judge with check_evidence.py --strict

## Limits

Editor checks do not prove a standalone Player, touch hardware, device notches, exact
original shader output, or solvability of levels other than the sample level. C# taken
from the skill templates was verified only by the checks above.

Tooling: pip pins use `==` without `--require-hashes`; the optional `level-decoders` venv
had never been installed live before this run (`<installed / present / failed / not needed>`
here); its `tpk-ar` pin builds from source during install.
