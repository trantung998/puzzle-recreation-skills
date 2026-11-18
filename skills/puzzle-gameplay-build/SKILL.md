---
name: puzzle-gameplay-build
description: Use when building recreated Unity puzzle gameplay into an existing or new Unity project from extracted evidence (levels manifest, mechanics.md, visuals.md) - model/view architecture, loading original level files, a level switcher with next, previous and retry, importing recovered assets, reconstructing shaders, VFX and audio, or keeping the work inside Assets/<GameSlug>/ while the user's scenes, packages and settings stay untouched. Also for dựng gameplay vào project Unity, tải level gốc, chuyển level, nhập asset gốc, tái tạo shader, không sửa scene của người dùng.
---

# Puzzle gameplay build

## Overview

Phase `build`: turns the work directory's `evidence/` into playable gameplay inside
`Assets/<GameSlug>/` of the target project. The C# in `templates/csharp/` is unverified
template text: adapt it, then verify it there with `puzzle-gameplay-verification`.

## Inputs

- `progress.json` (`slug`, `inputs.project`, `inputs.levels`), `decisions.md` (append only).
- `evidence/levels/manifest.json`, `evidence/levels/<name>.json`, `evidence/mechanics.md`,
  `evidence/visuals.md`, and `decompile/export/ExportedProject/Assets` for asset files.
- A missing entry or empty `Label` cell goes back to `puzzle-evidence-extraction`.

## Preconditions: read the project, adapt, never convert

Read the Unity version, render pipeline, Input System package and `activeInputHandler`,
uGUI, open scenes with their dirty state, and names already in use. Record them in
`decisions.md`. Detection table and actions: [project integration](references/project-integration.md).

- Shaders follow the project's pipeline. Never switch the pipeline.
- The Input System is required (spec §4 uses real Input System pointer events). Keep
  `activeInputHandler` if it is 1 or 2. If it must change, set 2 (Both), never 1: scenes
  and vendor code may hold a `StandaloneInputModule` a code search misses. If the
  package is absent, set the handler first, then add `com.unity.inputsystem` without a
  version. Log old and new values in `decisions.md`. Never restart an Editor that holds
  a dirty user scene; record the pointer checks as blocked.

## Layout and templates

`Assets/<GameSlug>/` holds `Runtime/`, `Editor/`, `Scenes/`, art, audio, shaders,
`PROVENANCE.md` (from [the template](templates/PROVENANCE.md)) and
`Resources/<GameSlug>/Levels/`: byte copies of `evidence/levels/manifest.json` (named
`_manifest.json`) and of each `<name>.json`.

| Template | Contract |
|---|---|
| `LevelCatalog.cs.txt` | `Count`, `NameAt(i)`, `LoadRaw(i)`; reads `Resources/<GameSlug>/Levels/` in manifest `index` order (not array order; gaps throw) |
| `GameSession.cs.txt` | `IGameSession` (`CurrentLevel`, `LevelLoaded`, `Won`, `Load`, `Retry`, `Next`, `Previous`; wrap at both ends) and abstract `GameSession` |
| `LevelSwitcherOverlay.cs.txt` | runtime uGUI (adapt via `ui-ugui` if installed, else as is), 20 levels per page, safe area, `SetVisible(false)` for captures |

Copy each to `.cs` and replace the two tokens, then search for `__GAME_`: zero hits.

- `__GAME_SLUG__`: the raw `slug`, used only in folder and Resources paths.
- `__GAME_NAMESPACE__` (`<Id>` in the references): the C# identifier for the namespace, type
  prefixes (`<Id>Game`), script file names and asmdef `name`/`rootNamespace`. It is the
  slug if that is a valid identifier, else `Game` + slug (`2048` → `Game2048`); on a
  clash with an existing name, append `Recreation`. Record it.

Indices are 0-based in code; level numbers and check ids are index + 1
([architecture](references/architecture.md)). Do not rename these types; verification
calls them.

## Ownership

| Layer | Owns |
|---|---|
| Loader | original data, order and field names; reads no further than the original consumer |
| Model (plain C#) | rules, legality, state, win and fail |
| Session | load and teardown, input acceptance, animation sequencing, audio and HUD events |
| Views | presentation only, including the in-level HUD |

Details and a fictional example: [architecture](references/architecture.md).

## Per mechanic, in this order

1. Model contracts from the `mechanics.md` claim rows, including `reject` and `boundary`.
   Expected results come from `Exact source`. See them fail.
2. Model, until they pass. 3. View. 4. Input and session wiring.

Any constant you choose (timing, spacing, color) is `Inferred`: append it to
`decisions.md` when you choose it.

## Input across animation boundaries

Before writing input code, decide and record: busy policy, target identity, duplicate
taps, when capacity is reserved, when boosters are consumed, drain order, and reset on
`Load`. State commits on accept; views catch up. Never drop a valid tap silently.

## Asset import

Import only what `visuals.md` names for the N levels, resolved by GUID; keep original
names; one `PROVENANCE.md` row each. Never import recovered controllers, script stubs,
colliders or Animator controllers as logic. Open every exported shader: a
`DummyShaderTextExporter` or properties-only file is a placeholder, never a working
shader, so the shader you write is reconstructed. Say "original materials and textures
with a reconstructed shader", never "original shader", even when a stakeholder asks.
Details: [shaders, VFX, audio](references/shader-vfx-audio.md).

## Editing boundaries

| Files | Rule |
|---|---|
| `Assets/<GameSlug>/**` | yours |
| `Packages/manifest.json` | add a dependency only when required; never remove or change one; log it |
| `Packages/packages-lock.json`, files a package creates on install | only those created by a logged required package install |
| `ProjectSettings/ProjectSettings.asset` | `activeInputHandler` only, per the rule above; log it |
| `ProjectSettings/EditorBuildSettings.asset` | untouched; if the user asks, append only (index 0 stays) |
| everything else (existing scripts, scenes, prefabs, `Resources`, `.meta`, `Assets/Scripts/`) | never |

- The user's open scene is never saved, closed, reloaded, replaced or discarded, and
  the user is not asked to save it. Create your scene additively, save only it by path,
  close it, restore the active scene. Recipe and fallbacks: project integration §4.
- Play your scene through `EditorSceneManager.playModeStartScene`. Record Play Mode,
  Game View size, auto-tick and `EditorSceneManager.playModeStartScene` before changing
  them; restore them after. Do not enter Play Mode while a loaded scene is dirty: the
  verification pointer smoke refuses to start then and records BLOCKED.
- Load resources with the `<GameSlug>/` prefix. Leave existing GUIDs and `.meta` alone.
- Editor control: `unity-pipeline` or `unity-cli`; fallback batchmode `-executeMethod`,
  only when no Editor has the project open.
- Before completing, run the boundary check (project integration §7).

## Completing the phase

When all N levels load through `LevelCatalog`, every mechanic has model, view and
input, the switcher works and the project compiles:
`python3 <recreate-puzzle-gameplay skill dir>/scripts/progress.py complete --workdir <dir> --phase build --artifact <project>/Assets/<GameSlug>/PROVENANCE.md`.
Without that skill, keep the same layout and say that progress was not recorded.

## Common mistakes

| Rationalization | Reality |
|---|---|
| "Save it only after you've saved or discarded Main." | Never save or discard the user's scene. Create yours additively and save only it. |
| "The only user decision needed is whether to save Main first." | No question. Their scene stays dirty and open; record it. |
| "Create it in a fresh scene with `NewSceneMode.Single`." | Single replaces the open scene. Additive, then close yours. |
| "Extend `GameManager` with level loading." | Existing files are off limits. Use your namespace and folder. |
| "Add the gameplay scene to build settings." | Not needed: `playModeStartScene`. |
| "Switch the project to URP / Input System only." | Adapt to the pipeline; keep `activeInputHandler`, or set 2 (Both) if it must change. |
| "Uses the original game shader." | The export is a placeholder: reconstructed shader, original materials. |
| "Import the decompiled controllers; they already work." | They are evidence. Rules go into your model. |
| "Clamp it / add a fallback material until it looks right." | Find the cause first. |
