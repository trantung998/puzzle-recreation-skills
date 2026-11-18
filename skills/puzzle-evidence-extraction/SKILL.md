---
name: puzzle-evidence-extraction
description: Use when extracting gameplay evidence from a decompiled Android Unity puzzle game - finding, ordering and decoding its original levels (encoded or compressed level data, base levels versus A/B or event variants), deriving or answering a mechanic rule (what happens when pieces are tapped, linked or connected; capacity and reject cases) from dump.cs and native pseudocode, or recording visual, VFX, SFX, shader, animation, camera and HUD parameters with Proven/Observed/Inferred/Unknown labels. Also for trích xuất level, giải mã dữ liệu level, danh mục level, luật cơ chế, điều gì xảy ra khi chạm hoặc nối các ô/khối, thông số hiệu ứng hình ảnh âm thanh, nhãn bằng chứng gốc.
---

# Puzzle evidence extraction

## Overview

Turns decompile output into labelled evidence for phases 3-5: the level catalog,
mechanic rules, and visual/audio parameters. Every claim gets one label and an exact
source: original bytes, schema, native code, assets or supplied references. Never
game-design intuition, and never an existing reconstruction.

## When to use

- Use: after `unity-apk-decompile` output exists, to fill `evidence/` in the work directory.
- Do not use for: running the decompile (`unity-apk-decompile`), building in Unity
  (`puzzle-gameplay-build`), or verification (`puzzle-gameplay-verification`).
- If `unity-apk-decompile` is not installed: run Il2CppInspectorRedux (Il2CppDumper cannot
  read Unity 6 metadata v39) or ILSpy for Mono,
  AssetRipper and targeted headless Ghidra yourself. Record tool versions in `decisions.md`.

## Inputs from the work directory

- `progress.json`: `inputs.apk_sha256`, `inputs.levels` (N), `inputs.references`.
- `decompile/`: `unpacked/`, `il2cpp-out/dump.cs`, `script.json`, `stringliteral.json`,
  `export/ExportedProject/Assets`, `work/native-code/*.c`.
- `decisions.md`: append only.

Outputs: `evidence/levels/manifest.json`, `evidence/levels/<name>.json`,
`evidence/mechanics.md`, `evidence/visuals.md`, `evidence/native/*.c`.

## Level catalog (phase `level-catalog`)

Details: [level storage patterns](references/level-storage-patterns.md).

1. **Reuse check first.** If an earlier extraction exists, compare its recorded source
   hash with `inputs.apk_sha256`, then recompute each reused level's raw and decoded
   hashes. Re-extract only the entries that fail. A copy in a reconstruction project is
   not a source.
2. **Find the storage** (ScriptableObject, encoded string field, TextAsset, bundle,
   StreamingAssets, asset-pack split, scene, generator, remote).
3. **Establish the original order** from the catalog object, the loader's index rule, or
   a level-number field. Never from path ID, file order or name sort.
4. **Select the first N base levels by exact name or path ID.** No globs. List every
   variant you skip in `excluded_variants` with its reason.
5. **Decode with the probe:** `python3 scripts/decode_probe.py <field bytes> --out evidence/levels/<name>.json`.
   Only `result: json` is level data. On `undecoded`, find and decompile the decoder.
6. **Write the manifest** in the shape of
   [the example](templates/levels-manifest.example.json). Compare any second copy
   semantically (parsed values), not only by hash.

## Mechanic inventory (phase `mechanics`)

1. Census the N decoded levels: every field path and every value actually used.
2. Map each field to its class and offset in `dump.cs`, then to the methods that read it.
3. Decompile those methods with `unity-apk-decompile` (targeted list, never the whole
   binary). Copy the read `.c` files into `evidence/native/`. For Mono, ILSpy C#
   replaces `dump.cs` and pseudocode; a decompiled C# branch you read is `Proven`.
4. Write one entry per mechanic from [the mechanic template](templates/mechanic-entry.md),
   including reject and boundary cases.
5. Interpret data only as far as the consuming code does. If an array is longer than a
   capacity or count field, read the method that consumes it; do not play the extras.
6. A class, method or enum name proves the code exists. It does not prove a branch, a
   default, or that it runs in these levels. A rule is `Proven` only for the exact
   branch you read; extrapolated past it, `Inferred`; with no branch read, `Unknown`.
7. Mechanics present in metadata but unused by the N levels: one line each, out of scope.

## Visual and audio inventory (phase `visuals`)

Follow [the visual and audio inventory](references/visual-audio-inventory.md) and its
entry format: prefabs, GUIDs, material overrides, shaders, particles, animation, audio
events, camera, board layout, in-level HUD and reference comparison. An AssetRipper
shader is a placeholder: write `Shader status: reconstructed`.

## Evidence labels

| Label | Meaning | Counts | Does not count |
|---|---|---|---|
| Proven | Original bytes, schema, native branch, prefab or reference frame proves this exact claim | `dump.cs` offsets and RVAs (schema); the exact branch you read; asset YAML values | Branches you did not read; names alone |
| Observed | A reference frame/video or a current Unity interaction shows the behaviour; say which | File + timestamp; run ID | Any static file |
| Inferred | Your reconstruction choice that explains the evidence; not recovered behaviour | Basis named; line in `decisions.md`; a rule carried past the branch you read | Values stated as original |
| Unknown | Missing, contradictory or insufficient evidence | What you searched | Silence |

When you choose an `Inferred` value, write it into the entry and append it to
`decisions.md` at that moment.

## Completing a phase

After each phase, with the `recreate-puzzle-gameplay` skill directory as `<orchestrator>`:
`python3 <orchestrator>/scripts/progress.py complete --workdir <dir> --phase level-catalog --artifact <dir>/evidence/levels/manifest.json`
(likewise `mechanics` with `mechanics.md`, `visuals` with `visuals.md`). Without that
skill, keep the same layout and say that progress was not recorded.

## Common mistakes

| Rationalization | Reality |
|---|---|
| "Use that copy, or re-run the extract script for just these levels." | Check hashes first; re-run only entries that fail the check. |
| "I did not re-verify the hashes." | Unchecked reuse is not evidence. Recompute raw and decoded hashes. |
| "The project already contains the levels, so this step is done." | A derived copy is not a source. Decode from the original container. |
| "A bulk import of everything named `Level_*` is quicker." | A glob pulls in variants. Select by exact name or path ID. |
| "Static method evidence, not an observed play run" (prose, no label). | Every claim row carries one label. Prose provenance is not a label. |
| `dump.cs` offsets labelled Observed; pseudocode flow labelled Inferred. | Offsets and RVAs are Proven schema. The branch you read is Proven. |
| "Uses the original game shader" / "essentially the original". | Exported shaders are placeholders. Original materials, reconstructed shader. |
| "Here the brief is this file" (the record is left for later). | Append to `decisions.md` now, with the label and the basis. |
| A constant taken from an existing reconstruction. | It is not source evidence: `Inferred`, basis "reused from <path>". |
