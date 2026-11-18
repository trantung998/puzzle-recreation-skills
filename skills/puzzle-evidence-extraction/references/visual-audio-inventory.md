# Visual, VFX, SFX, shader and animation inventory

Output: `evidence/visuals.md`, one entry per gameplay component in the N levels (board,
pieces, obstacles, tracks or paths, effects, in-level HUD). Paths below are relative to
`decompile/export/ExportedProject/Assets` unless they start with `decompile/` or `evidence/`.

## Entry format (required)

Every entry uses this shape. An entry with an empty `Label` cell is incomplete.

```markdown
## <Component> (used by: Stage_001, Stage_004, ...)

- Active prefab: `GameObject/<Name>.prefab`, root fileID <id>; active children: <names>
- Mesh/Sprite: `<path>` GUID <guid> (resolved through the `.meta`, not by file name)
- Materials: `<path>` GUID <guid>; source values: <property = value, ...>
- Runtime overrides: <code path that changes material, color, scale> or "none found (searched: ...)"
- Shader status: reconstructed | original-source

| Parameter | Value | Label | Exact source | Notes |
|---|---|---|---|---|
| startLifetime | 0.5-0.8 | Proven | `GameObject/X.prefab` ParticleSystem fileID 123, `InitialModule.startLifetime` | simulation seconds |
| play trigger | on match | Inferred | field name `_popEffect` in `dump.cs` only | binding not read in code |
```

`Shader status` takes one of two values:

- `reconstructed`: the shader you render with is written or ported by you. This is the
  status whenever the export is a placeholder, and also when you ported an original
  compiled blob.
- `original-source`: real shader source (not a placeholder, not a compiled blob) was
  recovered and is used unchanged. Name the file and the evidence that it is not a
  placeholder.

`Label` takes exactly one of `Proven`, `Observed`, `Inferred`, `Unknown`.
`Exact source` names the file and the object (fileID, GUID, method index/RVA, frame time).

## Prefab hierarchy and GUID resolution

- Start from the object that code or the scene actually spawns: a prefab field in a
  scene/config asset, or a `Resources.Load` path from `stringliteral.json`.
- Follow `m_IsActive`. Inactive children do not render unless code enables them; find
  that code before including them.
- Resolve every `{fileID, guid}` through the `.meta` with that GUID. Two assets can share
  a name. Sprites inside an atlas are fileIDs inside the texture's `.meta`.
- Nested prefabs: apply the `PrefabInstance` `m_Modifications` overrides before reading
  values.
- Record transforms (position, rotation, scale) of the visible parts. Note the ground
  plane (XZ or XY) and any rotation you add when rebuilding.

## Runtime material overrides

Serialized material values can be replaced at runtime. Search `stringliteral.json` and
`dump.cs` for property names (`_Color`, `_BaseColor`, `_MainTex`, `_EmissionColor`),
`MaterialPropertyBlock`, palette or color config assets, and methods that set colors.
A palette asset that maps a color ID to a material or color is the source for piece
colors. The material's own name is not.

## Shaders: recovery limits

- AssetRipper usually cannot export shader source. An exported `.shader` that contains
  `DummyShaderTextExporter`, or only a property block, is a placeholder. Open the file
  and check before writing anything about it.
- A placeholder gives property names and the material values. It does not give the
  lighting model, keyword selection or passes. The shader you write is **reconstructed**.
- Compiled blobs (GLES/Vulkan/Metal) may be extractable. They are evidence for the math
  of that one variant. A port of them is still a reconstructed shader.
- Write: "original materials and textures with a reconstructed shader". Never write
  "original shader", "essentially the original", "faithful port" or "identical output".
- Material values copied from the original material YAML are `Proven`. Formulas you
  chose are `Inferred`, with the basis named (for example, a template module).

## ParticleSystem module values

Read from the prefab YAML, per system (and per child system):

- Main: `lengthInSec`, `looping`, `startDelay`, `startLifetime`, `startSpeed`,
  `startSize`, `startColor`, `startRotation`, `gravityModifier`, `simulationSpeed`,
  `simulationSpace`, `scalingMode`, `maxNumParticles`.
- Emission (`rateOverTime`, `rateOverDistance`, bursts), Shape, Velocity/Force over
  lifetime, Color/Size/Rotation over lifetime, Texture sheet animation, Noise, Trails.
- Renderer: render mode, material GUID, sorting order, alignment.
- `minMaxState`: 0 constant, 1 curve, 2 two curves, 3 two constants. Copy curves whole.
- `simulationSpeed` scales visible time. Particle lifetime is not the controller's
  spawn duration; keep them separate.
- The trigger (which event plays it, delay, offset, scale) needs code or a serialized
  reference. A prefab that exists but is not referenced is `Unknown` as a binding.

## Animation

- AnimationClip YAML: `m_SampleRate`, `m_StopTime` (from `m_MuscleClipInfo`),
  `m_PositionCurves`, `m_EulerCurves`, `m_ScaleCurves`, `m_FloatCurves`, `m_Events`
  (function, time). Keep keyframes and tangents.
- Animator controllers: states, transitions, conditions, exit times, parameters.
- Code-driven tweens (DOTween, LeanTween, coroutines): durations, eases and delays live
  in static constructors, serialized controller fields or call arguments. Read them from
  native code or the serialized instance. A default in a static constructor is `Proven`
  as the startup default. That a live config does not change it is `Unknown` unless shown.
- Timings from reference video frames are `Observed` and only as precise as the frame
  interval.

## Audio

- List AudioClips from the export (`AudioClip/`), with length and import settings.
- Map clips to gameplay events. Search `dump.cs` and `stringliteral.json` for clip names,
  sound IDs or enums. Then read the audio config asset that maps IDs to clips, and the
  code that plays each ID.
- The mapping is `Proven` when a config asset links the ID to the clip GUID and the
  branch you read plays that ID. A match by name only is `Inferred`.
- Record volume, pitch, random pitch range, loop and cooldown when the config has them.

## Camera and board layout

- From the gameplay scene: camera projection, orthographic size or FOV, position,
  rotation, clipping, background color, post-processing volumes.
- Fitting code (aspect-ratio fit, safe area, board zoom by level size) is in native
  code. Record the formula and its label.
- Board layout constants: cell spacing, row distance, origin, slot positions. Find them
  in serialized controllers or static constructors. Record the unit (world units).

## In-level UI

Only gameplay HUD: level label, counters, move/time limits, booster bar, pause/retry.
Record sprites by GUID, fonts (TMP font assets), anchors and sizes from RectTransforms,
and the reference resolution of the Canvas Scaler. Store, ads, accounts and events are
out of scope.

## Reference images and video (when supplied)

- Record file, resolution, duration and frame rate. Extract frames at a fixed interval
  with exact timestamps (for example with ffmpeg if available) into `evidence/frames/`.
- Each behaviour you read from a frame is `Observed`, with file and timestamp.
- Measure positions in pixels and normalize to the frame size. Frame sampling limits
  timing: do not claim durations finer than the interval.
- Say what the clip does not show (for example, no level clear). Those parts stay
  native or asset evidence only.
- With no references, screenshots of the recreation are compared with the original
  prefabs and assets rendered in Unity. Say so in the entry.

## Inferred values under autonomy

If a value is not in assets, code or references:

1. Do one cheap search (AnimationClip, config asset, static constructor, tween call)
   and record what you searched as `Unknown`.
2. Choose a value, label it `Inferred`, and give the basis (another recovered timing,
   speed and distance, the reference clip).
3. Write the entry in `visuals.md` and append one line to `decisions.md` now, at the
   moment you choose. A later brief, handoff or code comment is not the record.
4. A constant from an existing reconstruction is not source evidence. If you reuse it,
   it is `Inferred` and its basis is "reused from <path>".
