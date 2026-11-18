# Level storage patterns and catalog extraction

Paths are relative to the work directory. `decompile/` is the `unity-apk-decompile`
output (`$W` in that skill): `unpacked/`, `il2cpp-out/dump.cs`, `il2cpp-out/script.json`,
`il2cpp-out/stringliteral.json`, `export/ExportedProject/Assets`, `work/native-code/`.
For a Mono build, the ILSpy C# output replaces `dump.cs` and native pseudocode.

## 1. Where Unity puzzle games keep levels

| Pattern | How it shows up | How to read it | Pitfall |
|---|---|---|---|
| ScriptableObject per level, plain fields | `MonoBehaviour/Stage_*.asset` with filled fields | YAML: `unity_yaml.py` from `unity-apk-decompile`, or any YAML reader after stripping the `--- !u!` tags | Field names are serialized names; keep them |
| ScriptableObject holding an encoded string | Asset has one long string field (Base64-looking) | Decode the field with `python3 scripts/decode_probe.py` | Probe the field bytes, not the whole asset |
| Custom MonoBehaviour exported header-only | `.asset` has only `m_Script`/`m_Name`; fields missing | Read raw object bytes (section 3) | Missing fields are not zero values |
| Catalog object listing levels | One asset with a `List<...>` of PPtrs | Its serialized list order is the original order | Variants may sit inline in the list |
| TextAsset (`.json`, `.txt`, `.bytes`) | `TextAsset/` in the export, often `Resources/Levels` | Probe each file | `.bytes` is often compressed or encrypted |
| Addressables / AssetBundles | `assets/aa/Android/*.bundle`, `catalog.json` | Same as above, inside the bundle | Container path is the bundle internal path |
| StreamingAssets | `assets/` files in the APK (JSON, CSV, SQLite, custom binary) | Probe; for SQLite read with `sqlite3` | Custom binary needs the parsing method |
| Install-time asset pack / split APK | Extra APKs beside the base APK; large serialized files cut into numbered `.splitN` parts | Load from the first part; readers join the parts | The base APK may hold a different subset |
| One scene per level | `Scenes/Stage_01.unity` | Scene objects are the data | Prefab instances carry overrides |
| Generated from a seed in code | Few or no level assets; generator class in `dump.cs` | Decompile the generator method | Label every rule from the branch read |
| Remote / downloaded | Loader uses URLs, remote config or a cache path | Look for a bundled default first | If none is in the APK, it is a stop condition |
| Encrypted | Probe says `undecoded`; code calls a decrypt routine | Decompile the decoder; reproduce it read-only | Record the key source; never guess a key |

## 2. Finding the storage

1. In `dump.cs`, list classes whose names or fields mention Level, Stage, Puzzle, Board,
   Grid, Catalog or Config. Note serialized fields and their offsets (`// 0x..`).
2. In `stringliteral.json`, search for resource paths and formats (`Levels/`, `level_`,
   `{0:D4}`, `.json`, `.bytes`) and for decoder clues (`gzip`, `brotli`, `base64`).
3. In `dump.cs`, search for decoder methods (`Decode`, `Decompress`, `Decrypt`,
   `FromBase64String`, `GZipStream`, `BrotliDecoder`, `JsonConvert`, `JsonUtility`)
   and the class that calls them.
4. In the export, count assets by type and size. Many similar assets, or one large
   TextAsset, usually hold levels.
5. Confirm with one object: decode it and check that its content matches its name
   (for example, a level number field equals the number in the name).

## 3. Reading custom fields when the export is header-only

Read raw object bytes with a reader that exposes path IDs (for example UnityPy, if
importable). Installing one is a tool install: pin its version and record name, version
and hash in `decisions.md`. Never install into system Python.

Unity binary serialization, little-endian, no type tree:

- Asset-file MonoBehaviour header: `m_GameObject` PPtr (int32 fileID + int64 pathID,
  12 bytes), `m_Enabled` (1 byte + align to 4), `m_Script` PPtr (12 bytes), `m_Name`
  string. The name's length is usually at byte 28. Verify on an object whose name you know.
- Then serialized fields in `dump.cs` declaration order, including base-class fields
  first. Serialized means public non-static non-const fields or `[SerializeField]`;
  skip `[NonSerialized]`, static, const and properties.
- `string`: int32 byte length, UTF-8 bytes, align to 4. `int`/`float`: 4 bytes.
  `bool`/`byte`: 1 byte, then align to 4. Arrays and `List<T>`: int32 count, elements.
  Nested `[Serializable]` classes are inline. PPtr: 12 bytes.
- Cut the exact field bytes (length prefix included) to a file and run the probe on it.
  The probe reports `unity-aligned-string` as the first step.

Labels: the field order and offsets from `dump.cs` are `Proven` schema facts. A layout
you assumed without checking a known object is `Inferred` until a known object decodes.

## 4. Original order

Use, in this priority: (1) the catalog object's serialized list order; (2) the loader's
index-to-name rule from code or a string literal format; (3) a level-number field inside
the decoded data. Do not order by path ID, filesystem order, or alphabetical name alone,
and do not assume path IDs are contiguous. When two sources disagree, record both,
label the order `Unknown`, choose one, and append the choice to `decisions.md`.

## 5. Base levels and variants

Signals of a variant: a suffix beyond the exact base name (`Stage_007_hard`), a variant or
A/B field holding a value, a separate catalog per experiment, or selection through
remote config. Only base levels are recreated: A/B test, event and difficulty variants
are never imported.

- Select the first N base levels by exact name or path ID. Never by glob or prefix.
- Every variant that shares a base number goes into that level's `excluded_variants`,
  with its reason and the signal you saw.
- A variant is never evidence for its base level. It can contain a different mechanic.
- If code picks a variant by default (no remote config), record that `Unknown` in
  `mechanics.md`, keep the base level, and append the decision to `decisions.md`.

## 6. Decoding

`python3 scripts/decode_probe.py <file> [--max-depth 6] [--out <decoded file>]`
(on Windows the interpreter may be `python`).

- It tries BOM strip, Unity aligned string, base64, gzip, zlib, raw deflate, brotli (if
  importable) and JSON, recursively. It prints `chain`, `result`, `preview`, `sha256_raw`,
  `sha256_decoded` and `warnings`.
- `result: json` means `json.loads` returned an object or array. `text`, `binary` and
  `undecoded` are not level data yet: `--out` writes nothing for them (warning
  `out-not-written:<result>`). Find the decoder method in code and decompile it.
- `json-scalar` means the bytes parse as a bare JSON number, boolean or null. That is
  not a level.
- `brotli-unavailable` means the brotli step was not tried. Install the module (pinned)
  or decode elsewhere. Do not report the level as undecodable.
- For a `json` result, `--out` writes the decoded bytes unchanged, so the file hash
  equals `sha256_decoded`.
  Save that file as `evidence/levels/<name>.json`. If you want a pretty-printed copy,
  give it a different name.
- Keep the probe output: copy `chain` into the manifest's `encoding_chain`.

## 7. Reuse and freshness (before trusting any earlier extraction)

1. First check: SHA-256 of the APK in `progress.json` (`inputs.apk_sha256`) against the
   source hash recorded with the earlier extraction (manifest, decompile record).
   If they differ, or none is recorded, the extraction is not reusable.
2. For each level you reuse, recompute `sha256_raw` from the original container bytes
   and `sha256_decoded` from the decoded file. Compare them with the manifest.
3. Rerun extraction only for entries whose check fails. Do not rerun everything "to be
   safe", and do not skip the check because the machine is slow.
4. A decoded copy inside a reconstruction project, or any other derived copy, is not a
   source. Decode from the original container.

## 8. Semantic compare

Byte hashes identify files. Pretty-printing changes bytes, not data. When you compare
two copies of a level (earlier extraction, a loader's input, a test fixture), parse both
and compare the values. Report both hash equality and semantic equality.
