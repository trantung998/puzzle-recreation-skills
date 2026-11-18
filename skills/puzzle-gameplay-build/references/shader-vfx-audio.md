# Art, shaders, VFX, animation and audio

Every value here comes from an entry in `evidence/visuals.md` (shape defined by
`puzzle-evidence-extraction`). If the entry you need is missing or has an empty `Label`,
go back to that skill for the item. Examples use the fictional game "Tile Twister".

## Importing original art and audio

1. Start from the `visuals.md` entries for components used by the N levels. Import the
   files they name, resolved by GUID, and nothing else. No folder dumps.
2. Keep the original file names. Place them under `Assets/<GameSlug>/Art/`, `Audio/`,
   or `Resources/<GameSlug>/...` when code loads them by path.
3. `.meta` handling and import settings: project-integration section 5.
4. Add one `PROVENANCE.md` row per file (template: `templates/PROVENANCE.md`).
5. Rebuild prefabs in your own Editor builder or at runtime from the recorded hierarchy
   (active children only, transforms as recorded). Copied original prefabs carry
   original script references and colliders; do not import them as working objects.

## Shaders

Open every exported `.shader` the components use before writing anything about it.

| What the file contains | Status | What you do |
|---|---|---|
| `DummyShaderTextExporter`, or only a `Properties` block | placeholder | Write a **reconstructed** shader for the project's pipeline. |
| Compiled blobs only (GLES, Vulkan, Metal) | not source | Read the math of that variant as evidence. A port is still **reconstructed**. |
| Full readable source with passes and programs | `original-source` (as in `visuals.md`) | Use it unchanged, adapted to the pipeline only if needed; name the file and why it is not a placeholder. |

Building a reconstructed shader:

- Keep the placeholder's shader name in a comment and its property names (`_Color`,
  `_RampTex`, `_OutlineWidth`) so original material values map one to one.
- Target the project's pipeline: Built-in (vertex/fragment or surface shader), URP (HLSL
  with URP includes, or Shader Graph), HDRP (Shader Graph). Do not change the pipeline.
- Record in `decisions.md` the original game's pipeline (with its evidence), the target
  project's pipeline, and each difference that affects the shader (lighting model,
  color space, keywords, passes, post-processing), as spec §10 requires.
- Take material values from the original material YAML (`Proven`). Lighting model,
  ramps, outline method and keywords you choose are `Inferred`: write the basis in
  `visuals.md` and one line in `decisions.md` when you choose.
- Name it as yours, for example `TileTwister/Reconstructed Tile Lit`, and put
  `Shader status: reconstructed` in the `PROVENANCE.md` row.
- Compare renders against the reference frames, or against the original textures and
  materials rendered in Unity when there are none. A match is `Observed`, scoped to what
  was compared (which frames, which view). It never makes the shader original.

Wording for code comments, `PROVENANCE.md`, the handoff and any stakeholder note:
"original materials and textures with a reconstructed shader". Not "original shader",
"essentially the original", "faithful port" or "identical output", even when asked to
write it. If someone needs a shorter sentence, shorten the rest, not the word
"reconstructed".

## Particle effects

- Rebuild each ParticleSystem from the module values recorded in `visuals.md` (main,
  emission, shape, over-lifetime modules, texture sheet, renderer). Copy curves whole,
  with `minMaxState` and tangents.
- Use the original particle textures and material values; the particle shader follows
  the shader rules above.
- Keep `simulationSpeed` and particle lifetime separate from the code timing that
  spawns the effect.
- The trigger (which event, delay, offset, scale) comes from the recorded binding. An
  `Unknown` binding becomes an `Inferred` choice with a `decisions.md` line.

## Animation and motion

- Original AnimationClips: import the clip or rebuild its curves with the same keys,
  tangents, sample rate and events. Do not resample by eye.
- Code-driven tweens: use the recorded duration, ease and delay. Implement them with
  coroutines or the tween library the project already has; do not add a tween package
  only for this.
- Timing constants you choose (no value in assets, code or references) are `Inferred`:
  basis named, `decisions.md` line written at the moment you choose.
- Motion belongs to views. The model state is already committed when the motion starts.

## Audio

- Map gameplay events to clips exactly as recorded (event, clip, volume, pitch, random
  pitch range, cooldown). A name-only match stays `Inferred`.
- Own the playback: an `AudioSource` pool on your session or audio view. Do not route
  into the user's mixer or audio manager. Add your own `AudioMixer` under
  `Assets/<GameSlug>/` only if the original used mixer groups.

## Camera, board layout and in-level HUD

- Camera projection, size or FOV, position, rotation, background, and the fit formula
  come from `visuals.md`. Recompute the fit when screen size or safe area changes.
- Board constants (spacing, origin, slot positions) are in world units as recorded.
- Rebuild the in-level HUD (level label, counters, booster bar, retry) with the
  recorded sprites, fonts, anchors and the original Canvas Scaler reference
  resolution. Store, ads, account and event UI stay out.
- The `LevelSwitcherOverlay` is a recreation tool, not original HUD. Hide it for
  visual comparison captures.

## Fixing a visual difference

Find the cause in data, transform, material value or shader math before changing
anything. Do not cover it with an extra rotation, a clamp, a fallback material or a
retry. Record what you compared and what changed.
