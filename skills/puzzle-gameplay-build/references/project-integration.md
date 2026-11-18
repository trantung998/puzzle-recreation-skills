# Integrating into the target Unity project

The target project belongs to the user. It may contain other games, open scenes with
unsaved work, and assets referenced by GUID. Your work lives in `Assets/<GameSlug>/`.
Examples use the fictional game "Tile Twister" (slug and namespace `TileTwister`).
`<GameSlug>` is the raw slug (folders, Resources paths, scene file); `<Id>` is the C#
identifier that replaces `__GAME_NAMESPACE__` (namespace, type and script names, asmdefs).

## 1. Read the project first

Before writing files, append one `[build] RECORD` line per value to `decisions.md`, in the
format of `recreate-puzzle-gameplay/templates/decisions.md`; skip values intake already recorded.

| Item | Where to read it | What to do with it |
|---|---|---|
| Unity version | `ProjectSettings/ProjectVersion.txt` (`m_EditorVersion`) | Templates use Unity 6 APIs. On 2021/2022, check each API (`FindAnyObjectByType` needs 2021.3.18+ or 2022.2+; `LegacyRuntime.ttf` needs 2022.2+, older uses `Arial.ttf`). |
| Render pipeline | `Packages/manifest.json` (`com.unity.render-pipelines.universal` / `.high-definition`); `ProjectSettings/GraphicsSettings.asset` (`m_CustomRenderPipeline`) and per-quality overrides in `QualitySettings.asset` | Write shaders and materials for that pipeline. Never switch or convert the project's pipeline. |
| Input System | `Packages/manifest.json` (`com.unity.inputsystem`); `ProjectSettings/ProjectSettings.asset` (`activeInputHandler`: 0 Input Manager, 1 Input System, 2 Both) | Section 3. |
| uGUI | `Packages/manifest.json` (`com.unity.ugui`) | Required by the overlay and HUD. Missing: add it (section 3). |
| JSON | `com.unity.nuget.newtonsoft-json` present? | Needed only if the level schema does not fit `JsonUtility` (architecture.md). |
| Open scenes | Unity control skill: loaded scenes, paths, `isDirty`, active scene | Section 4. Never touched. |
| Names in use | search `Assets/` for `namespace <X>`, `class <X>`, and the folder `Assets/<GameSlug>/` | Section 2. |
| Git | `git status --porcelain` (read only), if the project is a repository | Baseline for the boundary check. Never commit, stash or reset. |

Also write `<workdir>/build-boundary.txt` at the start of the phase: the SHA-256 of
`Packages/manifest.json` and of every file in `ProjectSettings/`, plus the Editor state
from section 6. The boundary check at the end compares against it.

## 2. Folder, namespace and resource names

```text
Assets/<GameSlug>/
|-- Runtime/                        # <Id>.Runtime.asmdef, namespace <Id>
|   |-- LevelCatalog.cs, GameSession.cs, LevelSwitcherOverlay.cs (from templates)
|   |-- <Id>Game.cs + partials, model, level data, views
|-- Editor/                         # <Id>.Editor.asmdef: scene builder, import, verification drivers
|-- Scenes/<GameSlug>Gameplay.unity
|-- Resources/<GameSlug>/Levels/    # _manifest.json + <name>.json, byte copies from evidence/levels/
|-- Resources/<GameSlug>/...        # audio, prefabs and art loaded by path
|-- Art/  Audio/  Shaders/  Materials/  Prefabs/
`-- PROVENANCE.md
```

- `__GAME_SLUG__` = `slug` from `progress.json`, unchanged, for folders and Resources
  paths. `__GAME_NAMESPACE__` (`<Id>`) = the slug if it is a valid C# identifier; else
  `Game` + slug (`2048` → `Game2048`, `3Tiles` → `Game3Tiles`). If that matches an
  existing namespace or type in the project, append `Recreation`. Use `<Id>` for every
  derived identifier: namespace, `<Id>Game` and other type prefixes, script file names,
  asmdef `name` and `rootNamespace`. Record the value in `decisions.md`.
- Folder collision: if `Assets/<GameSlug>/` already exists and is not output of this work
  directory (no matching `PROVENANCE.md`), `<GameSlug>Recreation` becomes the slug for every
  token and path: the folder `Assets/<GameSlug>Recreation/`, `__GAME_SLUG__`, the
  `Resources/<GameSlug>Recreation/` prefix, the scene name, and the `build` artifact path.
  Record it in `decisions.md` before writing files
  (`- [build] RECORD folder slug: <GameSlug>Recreation (Assets/<GameSlug>/ exists and is not ours) | source: Assets/<GameSlug>/PROVENANCE.md <missing or for another work directory>`).
  Verification and the handoff then use that slug wherever they say `<GameSlug>`.
- Unity merges every `Resources` folder in the project. Always load with the
  `<GameSlug>/` prefix (`Resources.Load<TextAsset>("TileTwister/Levels/Stage_001")`).
- Never reuse or edit an existing class to host your code (a `GameManager`,
  `LevelManager`, `AudioManager`). Your types live in your namespace; a same-named type
  there does not touch theirs.
- Assembly definitions keep compile errors on either side apart. Runtime:

```json
{
  "name": "TileTwister.Runtime",
  "rootNamespace": "TileTwister",
  "references": ["Unity.InputSystem", "UnityEngine.UI"]
}
```

  Editor: the same with `"name": "TileTwister.Editor"`, `"TileTwister.Runtime"` added to
  `references`, and `"includePlatforms": ["Editor"]`. Any asmdef holding game code must
  reference `Unity.InputSystem` (the package is always required, section 3) and
  `UnityEngine.UI`; the overlay template uses both. Add `Unity.TextMeshPro` if you use TMP.

## 3. Packages and input handling

A package or setting changes only when the recreation cannot work without it. Each
change gets a `decisions.md` line: what, old value, new value, why, how to revert.

| Case | Action |
|---|---|
| `com.unity.inputsystem` present, `activeInputHandler` 1 or 2 | Nothing. |
| Package present, `activeInputHandler` 0 | Set 2 (Both). Never 1: a code search misses `StandaloneInputModule` components serialized in scenes and vendor code, which throw every frame under 1. Restart needed (below). |
| Package absent | Required: spec §4 checks every mechanic with real Input System pointer events. If `activeInputHandler` is 0, set it to 2 (Both) first (1 stays only if it is already 1), then add `com.unity.inputsystem` with no version so the Editor picks the version it recommends (`unity-package-management` skill if installed, or `UnityEditor.PackageManager.Client.Add("com.unity.inputsystem")`). Setting the handler first avoids the package's modal "enable backends" dialog, which blocks an unattended Editor. |
| `com.unity.ugui` absent | Add it the same way. |
| Newtonsoft needed and absent | Add `com.unity.nuget.newtonsoft-json` the same way. |

- Set `activeInputHandler` through the Player settings, or a `SerializedObject` on
  `ProjectSettings/ProjectSettings.asset` (property `activeInputHandler`), never by
  editing the file while an Editor has it open.
- Never remove, upgrade or downgrade a package the project already has.
- **Restart rule.** An input-handler change takes effect after an Editor restart. Never
  quit or restart an Editor that has a dirty scene you did not create: quitting either
  blocks on a save prompt or loses the user's work. In that case finish everything that
  does not need the restart (code, model contracts, captures), record the pointer checks
  as BLOCKED with the reason "Editor restart required; the open scene has unsaved user
  changes", and put the exact unblock step in the handoff. Do not ask mid-run.

## 4. The gameplay scene, without touching the user's scene

Never save, close, reload, replace or discard a scene you did not create, and never ask
the user to save it first. Forbidden on an Editor that has user scenes open:
`EditorSceneManager.SaveOpenScenes`, `SaveScene(<user scene>)`,
`SaveCurrentModifiedScenesIfUserWantsTo`, `NewScene(..., NewSceneMode.Single)`,
`OpenScene(..., OpenSceneMode.Single)`, `MarkAllScenesDirty`, and menu items that save.

Pick the first route that applies. Record which one in `decisions.md`.

**Route A: an Editor has the project open (normal case).** Run an Editor method through
the Unity control skill:

```csharp
var previousActive = SceneManager.GetActiveScene();
var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    SceneManager.SetActiveScene(scene);   // new objects land in the active scene
    var root = new GameObject("TileTwisterRoot");
    root.AddComponent<TileTwister.TileTwisterGame>();
    if (!EditorSceneManager.SaveScene(scene, "Assets/TileTwister/Scenes/TileTwisterGameplay.unity"))
        throw new System.InvalidOperationException("Saving the new gameplay scene failed.");
}
finally
{
    if (previousActive.IsValid() && previousActive.isLoaded)
        SceneManager.SetActiveScene(previousActive);
    EditorSceneManager.CloseScene(scene, true);
}
```

`SaveScene(scene, path)` writes only that scene. After it, confirm the user's scene is
still loaded, at the same path, and still dirty.

**Route B: no Editor has the project open.** Run the same builder in a separate process:
`<Unity> -batchmode -projectPath <project> -executeMethod TileTwister.EditorTools.SceneBuilder.Build -logFile <workdir>/checks/<run-id>/scene-build.log -quit`
(`<Unity>` per OS: `puzzle-gameplay-verification` `references/unity-control.md` §1; on macOS
it is `.../Unity.app/Contents/MacOS/Unity`).
That process loads no user scene, so `NewSceneMode.Single` is acceptable there only when
`Application.isBatchMode` is true. Never take that branch in an interactive Editor. A
second Unity process cannot open a project an Editor already has open; that is not a
reason to close the user's Editor.

**Route C: Route A fails** (for example Unity refuses additive creation next to an
unsaved untitled scene). Write the scene file directly. After the bootstrap script has
compiled, read its GUID from `<Id>Game.cs.meta`, write the file below to
`Assets/<GameSlug>/Scenes/<GameSlug>Gameplay.unity`, then `AssetDatabase.ImportAsset` it.
This text is unverified: open it in Play Mode (below) and check the root component runs.

```yaml
%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {fileID: 101}
  - component: {fileID: 102}
  m_Layer: 0
  m_Name: TileTwisterRoot
  m_TagString: Untagged
  m_Icon: {fileID: 0}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_GameObject: {fileID: 100}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
  m_Children: []
  m_Father: {fileID: 0}
--- !u!114 &102
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 100}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: <GUID from TileTwisterGame.cs.meta>, type: 3}
  m_Name:
  m_EditorClassIdentifier:
```

**Playing the scene.** Do not open it in place of the user's scene. Set
`EditorSceneManager.playModeStartScene` to its `SceneAsset`, enter Play Mode, and set the
previous value back afterwards. Entering Play Mode over a dirty user scene can prompt to save or
discard it, so `puzzle-gameplay-verification`'s pointer smoke refuses to start while any loaded
scene is dirty and records the pointer checks as BLOCKED (unblock: the user saves or discards the
scene, then the run is repeated). Do not enter Play Mode yourself in that state.
Runtime `SceneManager.LoadScene` is not needed, so build settings stay as they are.

**EventSystem module swap.** With the Input System active, `LevelSwitcherOverlay`
replaces a `StandaloneInputModule` on an existing EventSystem with
`InputSystemUIInputModule`. That is a runtime-only change (Play Mode, discarded on exit).
Never make it in Edit Mode or save it into the user's scene; the template refuses
outside Play Mode.

**Build settings.** Not needed for Editor play or verification. Change them only if the
user asked for it: append the scene at the end, keep every existing entry and its order
(index 0 stays index 0), and record it.

## 5. GUIDs and `.meta` files

- Never move, rename, delete or regenerate an existing asset or its `.meta`.
- Imported original files are copied without their exported `.meta` by default; Unity
  assigns new GUIDs. Apply the original import settings (sprite mode, pivot, pixels per
  unit, filter, wrap, compression, audio load type) from the exported `.meta` with an
  Editor script or `AssetPostprocessor` limited to `Assets/<GameSlug>/`.
- Keep an exported `.meta` only when its GUID is needed (for example sprite fileIDs
  inside an atlas). First search every `.meta` under `Assets/` and `Packages/` for
  `guid: <that guid>`. If found, do not keep it. Record the choice in `PROVENANCE.md`.
- Do not import exported copies of Unity packages (TextMesh Pro resources, Input System
  assets, shader libraries). Use the project's installed packages.

## 6. Temporary Editor state

Before changing any of these, write the current value into `build-boundary.txt`; after
the phase, set each one back:

- Play Mode (stopped or playing), active scene, loaded scenes with `isDirty`
- `EditorSceneManager.playModeStartScene`
- Game View size, Editor auto-tick or run-in-background settings you enabled

Editor control goes through `unity-pipeline` (preferred) or `unity-cli` when installed.
Without them, batchmode `-executeMethod` (Route B) covers compile and Editor scripts but
not an Editor the user has open. `puzzle-gameplay-verification` has the details.

## 7. Boundary check (before completing the phase)

1. List every file changed outside `Assets/<GameSlug>/`: `git status --porcelain` (read
   only) if the project is a repository, otherwise compare hashes with
   `build-boundary.txt`.
2. Allowed: `Packages/manifest.json` and `ProjectSettings/ProjectSettings.asset`, each
   with its `decisions.md` line; `Packages/packages-lock.json` and files a package
   creates on install (under `Assets/` or `ProjectSettings/`, for example a package's
   own settings asset), only those created by a logged required package install. List
   each such file in the handoff; do not revert it. Changes Unity wrote by itself when it opened the project
   (version upgrade of settings files) are listed in the handoff, not reverted.
3. Anything else you changed: revert your change, then record it.
4. Confirm each user scene from the intake record is loaded, at the same path, with the
   same dirty state, and that the Editor state in section 6 is restored.
