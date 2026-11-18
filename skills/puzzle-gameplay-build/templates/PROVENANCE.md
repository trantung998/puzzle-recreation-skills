# Provenance for `Assets/<GameSlug>/`

Copy this file to `Assets/<GameSlug>/PROVENANCE.md` in the target project and replace the
example rows. One row per imported or reconstructed asset. The example rows describe a
fictional game, "Tile Twister" (slug `TileTwister`); none of them is a real asset.

- Source build: <APK/XAPK file name>, SHA-256 <inputs.apk_sha256 from progress.json>
- Work directory: <path to <GameSlug>-recreation/>
- Export root: `decompile/export/ExportedProject/Assets` (paths below are relative to it)
- Evidence: `evidence/visuals.md`, `evidence/mechanics.md`, `evidence/levels/manifest.json`

## Original data

| Project path | Source | Check |
|---|---|---|
| `Resources/TileTwister/Levels/_manifest.json` | byte copy of `evidence/levels/manifest.json` | SHA-256 equal to the work-dir file |
| `Resources/TileTwister/Levels/Stage_001.json` | byte copy of `evidence/levels/Stage_001.json` | SHA-256 equals manifest `sha256_decoded` |

## Original assets (imported files, names kept)

| Project path | Original path | Original GUID | Container | `.meta` | Changes |
|---|---|---|---|---|---|
| `Art/Textures/tile_atlas.png` | `Texture2D/tile_atlas.png` | 3f9c... | `base.apk!assets/bin/Data/sharedassets0.assets` | new GUID (Unity assigned) | none; import settings set from the original `.meta` (filter Bilinear, PPU 100) |
| `Audio/ice_crack.wav` | `AudioClip/ice_crack.wav` | 81aa... | same | new GUID | none |

`.meta` is `new GUID (Unity assigned)` or `original GUID kept (checked unused in this project)`.

## Reconstructed assets

| Project path | Built from | Shader status | Label | Notes |
|---|---|---|---|---|
| `Shaders/TileTwister_TileLit.shader` | placeholder `Shader/Tile Lit.shader` (contains `DummyShaderTextExporter`: property names only) | reconstructed | Inferred | URP Unlit pass with a ramp lookup; property names kept from the placeholder |
| `Materials/Tile_Blue.mat` | values from `Material/Tile_Blue.mat` (`_Color`, `_RampTex`) | uses the reconstructed shader above | Proven (values) | original material values with a reconstructed shader |
| `Prefabs/IceCrack.prefab` | ParticleSystem modules from `GameObject/IceCrackFx.prefab` fileID 4411 | n/a | Proven (module values) | trigger binding Inferred, see `decisions.md` |

Wording for any summary: "original materials and textures with a reconstructed shader".
Do not write "original shader", "essentially the original", "faithful port" or "identical output".

## Code templates used

| Project file | Template | Placeholders replaced |
|---|---|---|
| `Runtime/LevelCatalog.cs` | `puzzle-gameplay-build/templates/csharp/LevelCatalog.cs.txt` | `__GAME_NAMESPACE__` = TileTwister, `__GAME_SLUG__` = TileTwister |

Verification results are not recorded here (this file is the `build` artifact, hashed before
`verify` runs); they live only in `checks/<run-id>/verification-report.md`.
