# Architecture for a recreated puzzle game

The example game in this file is fictional: "Tile Twister" (slug `TileTwister`), with
levels `Stage_001`..`Stage_012` and an ice tile mechanic. It shows shape only. Every rule
in a real recreation comes from that game's `evidence/mechanics.md`.

## Layers and ownership

| Layer | Type (example) | Owns | Must not |
|---|---|---|---|
| Catalog | `LevelCatalog` (template) | manifest `index` order (sorted by `index`, not array order; gaps throw), raw original files | parse level contents |
| Level data | `TileTwisterLevelData` | original field names and types, defaults the original code applies | rename fields, add derived state, read entries the original code ignores |
| Model | `TileTwisterModel` + mechanic partials | rules, legality, state, counters, win and fail conditions | reference `UnityEngine.Object`, time, coroutines, input devices |
| Session | `TileTwisterGame : GameSession` + partials | load and teardown, input acceptance and queueing, animation sequencing, audio and HUD events, win and fail timing | decide a rule the model can decide |
| Views | `BoardView`, `TileView`, `HudView` | meshes, sprites, materials, motion, VFX, HUD layout | change model state, keep a second copy of state |
| Editor | `TileTwisterImport`, `TileTwisterSceneBuilder`, verification drivers | asset import, scene file creation, checks | runtime behaviour |

The model is plain C#. A model contract can then construct it from a level file and
call it without a scene, which is what `puzzle-gameplay-verification` needs.

## Level index and level number

| Where | Value | Example (third level) |
|---|---|---|
| Code: `LevelCatalog`, `IGameSession.Load`, `CurrentLevel`, `LevelLoaded` | 0-based index; `CurrentLevel` is -1 before the first load | `2` |
| Shown to users, manifest `index`, check ids | 1-based level number = index + 1 | `Level 3`, `level-3` |

## Load requests and reentrancy

- `Load`, `Retry`, `Next` and `Previous` requested while a level is loading (for example
  from code inside `BuildLevel` or a `LevelLoaded` handler) are queued and run after the
  current load, including the `LevelLoaded` dispatch, has finished. `Next`, `Previous` and `Retry` are resolved when they run.
- Raise `Won` (through `NotifyWon()`) after `Load` has returned, from `Update` or a
  coroutine, never inside `BuildLevel`.
- If `BuildLevel` throws, `CurrentLevel` returns to its previous value, queued requests
  are dropped, and the exception propagates. The old views are already gone: fix the
  cause, then load again.

## Level data classes

- One `[Serializable]` class per original record type. Keep every field name exactly as
  in the decoded JSON, even when it is cryptic (`bw`, `cl`, `mv`). Add a comment that the
  names are original.
- Use `JsonUtility` when the schema fits: objects, arrays of objects, primitives. Use
  Newtonsoft (`com.unity.nuget.newtonsoft-json`) when it does not: a top-level array,
  dictionaries, `null` that must stay distinct from 0, polymorphic records. If the package
  is missing, adding it is a required package change (see project-integration).
- A default for an absent or zero field comes from the original code, with its source
  (for example a constant in a static constructor, `Proven`). Never your own default.
- Read data only as far as the consuming method does. If `mechanics.md` says the
  consumer stops at a capacity or count, the extra entries are not played and not drawn.
  Keep them in the data class so the file still round-trips.

## Model contracts first (per mechanic)

For each mechanic entry in `evidence/mechanics.md`:

1. Turn each claim row into one contract: input state, action, expected result. The
   expected result comes from the row's `Exact source`, never from the code you are about
   to write. Cover every `reject` and `boundary` row, not only `accept`.
2. Run it and see it fail (the model does not exist yet). Use `test-driven-development`
   if installed. The runner is the `ModelContractRunner` template of
   `puzzle-gameplay-verification`.
3. Write the model until the contracts pass.
4. Write the view: geometry and materials from `evidence/visuals.md`.
5. Wire input: collider or raycast target on the view, acceptance in the session, rule
   call into the model. A uGUI raycast target (HUD, `LevelSwitcherOverlay`) does not stop
   physics raycasts or collider input, so the session ignores a pointer that is over UI:
   `EventSystem.current.IsPointerOverGameObject(pointerId)`, or, inside Input System
   action callbacks where that call is unreliable, `EventSystem.current.RaycastAll` with a
   `PointerEventData` at the pointer position and a non-empty result. Without this,
   a click on the switcher also taps the board under it.

Order of work: catalog and level data first (all N levels parse), then the base board,
then mechanics in the order of the first level that uses them.

Example contract rows from the fictional ice tile:

| Claim (from `mechanics.md`) | Contract |
|---|---|
| Tap on an iced cell lowers `ice` by 1 and does not move the piece (`reject`) | Stage_006 cell (2,3) with `ice = 2`: tap, expect `ice == 1`, piece position unchanged |
| Values above 3 play as 3 (`boundary`) | load a copy of Stage_009 with `ice = 5`: expect three taps before the piece moves |

## Input across animation boundaries

Decide each item before you write input code. Write one line per decision into
`decisions.md` with its label. Native input gating from the original code (`Proven`)
wins; without it the decision is `Inferred` with a basis.

| Decision | Question to answer |
|---|---|
| Busy policy | A tap while a previous action animates: accepted now, queued, or rejected? |
| Target identity | A queued tap names the model object (id), not a screen position or a view |
| Duplicates | A second tap on the same target before the first resolves: ignored, queued, or a second action? |
| Reservation | Is capacity (slots, road, moves) reserved when the tap is accepted or when the animation arrives? |
| Consumption | When is a booster, move or key consumed: on accept or on completion? |
| Drain | In which order and at which moment are queued taps applied? |
| Reset | `Load`, `Retry`, `Next` and `Previous` clear every pending tap and reservation (always) |

Rules that hold for every game:

- The model state commits when an action is accepted. Views catch up afterwards. A
  closing, clearing or win state never waits for a late visual event.
- A valid tap is never dropped silently because a view is busy. Queue it or reject it
  with the original feedback, as decided above.
- Capture `LoadGeneration` when a coroutine or tween starts. If it changed, the callback
  returns without touching anything.

## Win and fail timing

- The model answers "is the level won" and "is the position stuck". The session decides
  when to show it: after the animations the original waits for have finished.
- A fail that the original detects after a delay (for example "stuck for N seconds")
  counts the delay only while nothing is settling. Take N from evidence; otherwise
  `Inferred` with a `decisions.md` line.
- Call `NotifyWon()` from the session; `IGameSession.Won` fires once per load.

## Scene and composition root

- The gameplay scene holds as little serialized content as possible: a root object with
  the per-game `GameSession` subclass. The session creates the camera, lights, views,
  HUD and `LevelSwitcherOverlay` at runtime. This keeps the scene file small and makes
  the scene easy to create without touching the user's open scene (project-integration).
- Camera values (projection, size or FOV, position, background) and board layout
  constants come from `evidence/visuals.md` with their labels.
- The switcher bar sits at the bottom of the safe area. If an original HUD element is
  under it, move the bar (anchor or `sortingOrder`), not the original HUD. The bar and
  the open grid block only other uGUI; gameplay input under them is filtered by the
  session's pointer-over-UI check (step 5 above).

## Partial classes

Split a large session or model into `partial` files by mechanic
(`TileTwisterGame.Ice.cs`, `TileTwisterModel.Ice.cs`). One mechanic then maps to a
small, findable set of files, and the game-notes skill can list them in its source map.

## What not to do

- Do not port decompiled original controllers or AssetRipper script stubs as the logic.
  They are evidence for the rules you write into the model.
- Do not use recovered colliders, Rigidbodies or Animator controllers as the rule engine.
  Add your own colliders for raycasting, sized from rendered geometry.
- Do not hide a wrong cause with retries, clamps, fallback materials or extra rotations.
  Find the cause first (`systematic-debugging` if installed).
