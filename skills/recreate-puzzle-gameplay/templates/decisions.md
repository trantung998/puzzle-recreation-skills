# decisions.md template

`<workdir>/decisions.md` is the run's decision log. `progress.py init` creates it empty.
If it is empty, append the heading `# Decisions: <GameSlug>` once. If it is missing (for
example, a single phase run outside a work directory), create it with that heading. Copy
nothing else from this file into it: everything after the heading is lines you append.

## Rules

- Append only. Never overwrite, reorder or delete a line, not even on resume.
- Write the line at the moment you choose, before the value is used in code, data or text.
  "I will record it later", a later brief, a handoff note or a code comment is not a record.
- One line per decision. `<phase>` is a `progress.py` phase name: `intake`, `decompile`,
  `level-catalog`, `mechanics`, `visuals`, `build`, `verify`, `game-notes`, `handoff`.
- `searched` names where you looked for the original value and what you found: at least
  one search you ran (the cheap search of visual-audio-inventory), plus any earlier evidence
  file you cite by path. "nothing found" is a valid result; leaving the field out, or
  listing a search you did not run, is not. Only a line re-recording an earlier session's
  decision may say `searched: not recorded by an earlier session`.
- The handoff copies every line containing `| Inferred |`, so keep the separators exactly.
- To revise a choice, append a new line that says `replaces [<phase>] <item>`. The earlier
  line stays.

## Line formats

Inferred choice (a value or behaviour chosen without original evidence):

```text
- [<phase>] <item> = <chosen value, with units> | Inferred | reason: <basis> | searched: <places and results>
```

Recorded fact (read from the project, a tool or the build; not a choice):

```text
- [<phase>] RECORD <item>: <value> | source: <file, command or tool output>
```

Change outside `Assets/<GameSlug>/` (package, setting, tool install):

```text
- [<phase>] CHANGE <file or setting>: <old> -> <new> | why: <reason> | revert: <exact step>
```

Run event (refusal, block, redone phase, stop):

```text
- [<phase>] EVENT <what happened> | next: <what the run did about it>
```

## Example (fictional game "Tile Twister", shape only)

```text
# Decisions: TileTwister
- [intake] RECORD Unity version: 6000.0.41f1 | source: ProjectSettings/ProjectVersion.txt
- [intake] RECORD open scene Assets/Scenes/Menu.unity, dirty | source: unity-pipeline scene list
- [decompile] RECORD tools: Ghidra 12.2, JDK Temurin 25.0.5+8, Il2CppDumper 6.7.46 | source: progress.json "tools" (ensure_tools.py)
- [level-catalog] stage order = serialized order of StageCatalog.stages | Inferred | reason: the loader's index rule is not decompiled; the catalog list is the only ordered source | searched: stringliteral.json for "Stage_{0" (nothing found); StageLoader in dump.cs (names only, no branch read)
- [visuals] tile-clear pop duration = 0.25 s, ease-out quad | Inferred | reason: equals the recovered 0.25 s swap clip TileSwap.anim, the nearest original timing | searched: AnimationClip in the export (no clear clip); TileView methods 5120-5131 in native code (no duration literal); no reference video supplied
- [build] CHANGE ProjectSettings activeInputHandler: 0 -> 2 | why: spec §4 needs real Input System pointer events | revert: Player Settings > Active Input Handling = Input Manager (Old)
- [verify] EVENT pointer checks BLOCKED: Assets/Scenes/Menu.unity has unsaved user changes | next: compile and model contracts ran; unblock step written to handoff.md
```
