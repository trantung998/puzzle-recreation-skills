# Puzzle Gameplay Recreation Skill Set — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Skill-authoring tasks also REQUIRE superpowers:writing-skills (RED → GREEN → REFACTOR).

**Goal:** Build a cross-harness skill set that takes an Android Unity puzzle APK, a level count N and a Unity project path, and autonomously recreates playable, source-faithful gameplay for the first N base levels with fast level switching.

**Architecture:** One orchestrator skill (`recreate-puzzle-gameplay`) drives four phase skills through files in a per-game work directory (`progress.json`, `evidence/`, `checks/`). The existing `unity-apk-decompile` is forked to the global skills folder with environment-based tool resolution. Stdlib-only Python scripts provide tool installation, progress/resume, data-decoding probes, skill linting and evidence-file checks; C# is shipped only as unverified templates.

**Tech Stack:** Markdown Agent Skills (`SKILL.md` + YAML frontmatter), Python 3 stdlib (`unittest`, `hashlib`, `json`, `zipfile`, `urllib`), optional `brotli`, Git Bash (for the forked decompile scripts on Windows), Unity C# templates (Input System, uGUI).

**Spec:** `C:\Users\melod\.agents\docs\specs\2026-11-17-recreate-puzzle-gameplay-design.md` (Vietnamese). Read it fully before any task.

## Global Constraints

- Skills root: `C:\Users\melod\.agents\skills\` (`~/.agents/skills`). Dev-only tooling: `C:\Users\melod\.agents\docs\tools\`.
- Frontmatter: only `name` and `description`; `name` == directory name, kebab-case `^[a-z0-9]+(-[a-z0-9]+)*$`; `description` starts with `Use when`, states triggers only (no workflow summary), includes English and Vietnamese keywords, total frontmatter < 1024 chars.
- New skill bodies in English. `unity-apk-decompile` body stays as-is (Vietnamese) except tool-path changes.
- No harness-specific tool names in skill bodies (`todo`, `TodoWrite`, `Task`, `subagent`, `Agent`, `Bash(`), no `@file` links. Sub-agent use is phrased "if your harness can spawn sub-agents …; otherwise sequentially".
- Bundled scripts are invoked through an interpreter in prose (`python3 scripts/x.py`, `bash scripts/x.sh`). New scripts are Python 3 stdlib only; `brotli` is optional and its absence must be reported, not crash.
- Never modify: `H:\UGame\ParkingLoop\.agents\skills\unity-apk-decompile\`, `H:\UGame\ParkingLoop\tools\decompile-shell.cmd`, `C:\Users\melod\.agents\skills\parkingloop-recreate-mechanics\`, anything in `H:\UGame\ParkingLoop\ParkingLoop_R\` or `H:\UGame\ParkingLoop\Analysis\`. Parking Loop is a read-only fixture.
- Tool directory resolution order: `$UNITY_DECOMPILE_TOOLS` → `H:/UGame/ParkingLoop/tools` if it exists → `~/.cache/puzzle-recreation/tools`.
- Tool installs: pinned version + URL in a manifest; verify SHA-256 when recorded; never edit system PATH; no admin. Unity Editor is never auto-installed.
- Evidence labels exactly: `Proven`, `Observed`, `Inferred`, `Unknown`.
- Work directory default: `<directory containing the APK>/<GameSlug>-recreation/`. Unity output inside `Assets/<GameSlug>/` only.
- C# shipped in skills is template text (`*.cs.txt`), headed with `// TEMPLATE — unverified; adapt and verify in the target project.`
- Test level for this plan is Level A (spec §11): read/plan-only scenarios; no full recreation run.
- No git repository exists under `~/.agents`; do not create one. Replace commit steps with "record the task in the routing ledger".
- Python tests run with: `python -m unittest discover -s <dir> -v` (pytest is not installed).

## Review Focus

1. **Same skill ID in two places** — inside `H:\UGame\ParkingLoop` both the project and global `unity-apk-decompile` exist; the project copy must win there and the global copy elsewhere. Pinned by Task 1 Step 6 (OpenCode API listing from both locations).
2. **Partially present tool directory** (e.g. Ghidra present, JDK missing, or a half-extracted download) — expect detection per tool and install of only the missing one, never reuse of a corrupt archive. Pinned by Task 3 tests `test_partial_dir_installs_only_missing` and `test_hash_mismatch_rejected_and_removed`.
3. **Resume after inputs changed** (same work dir, different APK bytes or N) — expect resume refused with a clear message, not silent reuse of stale evidence. Pinned by Task 2 test `test_resume_rejects_changed_apk_hash` and `test_resume_rejects_changed_level_count`.
4. **Level data in an unexpected encoding** (gzip/zlib/brotli/base64 nesting, Unity aligned strings, BOM) — expect the probe to report the decode chain or "undecoded", never to fabricate JSON. Pinned by Task 6 tests.
5. **Windows paths with spaces and `+`** (e.g. `Parking+Loop_567_APKPure.xapk`) — expect slug and work-dir derivation to succeed and scripts to quote paths. Pinned by Task 2 test `test_slug_and_workdir_from_awkward_path`.

---

### Task 1: Fork `unity-apk-decompile` to the global skills folder

**Routing**
- Score: Scope 1 · Spec 1 · Judgment 0 · Codebase 1 · Risk 1 · Verification 1 = **5**
- Floors applied: none.
- Tier: **T2** → implementer `anthropic/claude-sonnet-5-5` / `medium`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`medium`, quality `anthropic/claude-sonnet-5-5`/`medium`
- Reason: small shell change, but a mistake silently breaks every later decompile.

**Files:**
- Create (copy of `H:\UGame\ParkingLoop\.agents\skills\unity-apk-decompile\`, excluding nothing): `C:\Users\melod\.agents\skills\unity-apk-decompile\`
- Modify: `…\unity-apk-decompile\scripts\tools-env.sh` (tool root resolution)
- Modify: `…\unity-apk-decompile\scripts\bin\python3`, `bin\il2cppdumper`, `bin\ilspycmd` (each currently derives `ROOT` five levels up and uses `$ROOT/Tools/…`; change to `${UNITY_DECOMPILE_TOOLS:?source tools-env.sh first}/…`)
- Modify: `…\unity-apk-decompile\SKILL.md` line 24 only (source path)
- Modify: `…\unity-apk-decompile\INSTALLATION.md` (rewrite as global-fork notes)
- Create: `…\unity-apk-decompile\tests\test_tools_env.sh`

**Interfaces:**
- Produces: sourcing `tools-env.sh` exports `SK`, `PATH`, `JAVA_HOME`, `GHIDRA_INSTALL_DIR`, `ANALYZE_HEADLESS`, `GHIDRA_HEADLESS_MAXMEM`, `IL2CPPDUMPER_DIR`, `ASSETRIPPER`, `DOTNET_ROLL_FORWARD` (unchanged names) plus new `UNITY_DECOMPILE_TOOLS` (resolved root). If no root resolves, it prints `unity-apk-decompile: no tool directory; run recreate-puzzle-gameplay/scripts/ensure_tools.py` to stderr and `return 1`.
- Tool subfolder names stay as in the existing tree: `decompile-python`, `jdk-25`, `ghidra-12.2`, `Il2CppDumper-6.7.46`, `AssetRipper_2.0.0`, `ilspycmd-9.1.0`.

- [ ] **Step 1: Copy the directory** with `Copy-Item -Recurse` to the global path; confirm the recursive file count and per-file SHA-256 equal the source.
- [ ] **Step 2: Write failing test `tests/test_tools_env.sh`** (run with `"C:/Program Files/Git/bin/bash.exe"`). Three cases, each in a subshell:
  - `UNITY_DECOMPILE_TOOLS=<tmp>` with fake `ghidra-12.2/` → `GHIDRA_INSTALL_DIR` ends with `<tmp>/ghidra-12.2`.
  - unset, `H:/UGame/ParkingLoop/tools` exists → `UNITY_DECOMPILE_TOOLS` resolves to it (case-insensitive compare).
  - `UNITY_DECOMPILE_TOOLS=/nonexistent` → source returns non-zero and stderr contains `no tool directory`.
  - a fourth case: after sourcing with `UNITY_DECOMPILE_TOOLS=<tmp>` containing a fake `decompile-python/Scripts/python.exe` script that echoes `fake-python`, running `python3` resolves to the wrapper and prints `fake-python`.
  Prints `PASS n/4` or `FAIL <case>`; exit code 0 only on 4/4.
- [ ] **Step 3: Run it** → expect FAIL on cases 1, 3 and 4 (old scripts ignore the variable).
- [ ] **Step 4: Edit `tools-env.sh`**: replace the four-levels-up `_DECOMPILE_ROOT` with the resolution order from Global Constraints; an explicitly set but missing `UNITY_DECOMPILE_TOOLS` is an error (do not fall through). Replace every `$_DECOMPILE_ROOT/Tools/` with `$UNITY_DECOMPILE_TOOLS/`, and update the three `bin/` wrappers. Change SKILL.md line 24 to `source "<this skill directory>/scripts/tools-env.sh"` wording that does not depend on `$PWD`.
- [ ] **Step 5: Run test** → `PASS 4/4`.
- [ ] **Step 6: Verify discovery precedence** via OpenCode API:
  `opencode api get "/api/skill?location%5Bdirectory%5D=H%3A%5CUGame%5CParkingLoop%5CParkingLoop_R"` → `unity-apk-decompile` path is `H:\UGame\ParkingLoop\.agents\skills\…`;
  same call with directory `C:\Users\melod` → path is `C:\Users\melod\.agents\skills\unity-apk-decompile\SKILL.md`.
- [ ] **Step 7: Rewrite `INSTALLATION.md`**: fork origin (project copy + upstream revision `025bff05…`), the resolution order, that copies can drift, and that `ensure_tools.py` installs missing tools.
- [ ] **Step 8: Record in routing ledger.**

---

### Task 2: `progress.py` — work directory, progress and resume

**Routing**
- Score: Scope 1 · Spec 1 · Judgment 1 · Codebase 0 · Risk 1 · Verification 0 = **4**
- Floors applied: none.
- Tier: **T2** → implementer `anthropic/claude-sonnet-5-5` / `medium`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`medium`, quality `anthropic/claude-sonnet-5-5`/`medium`
- Reason: well-specified stdlib CLI fully covered by unit tests.

**Files:**
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\scripts\progress.py`
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\tests\test_progress.py`

**Interfaces:**
- Produces (CLI, JSON to stdout, exit 0 ok / 2 refused / 1 error):
  - `python3 scripts/progress.py init --apk <path> --levels <N> --project <unity path> [--workdir <dir>] [--references <path>...]` → creates work dir layout of spec §5.1 (`decompile/`, `evidence/levels/`, `evidence/native/`, `checks/`, empty `decisions.md`), writes `progress.json`, prints `{"workdir":…, "slug":…, "next_phase":"intake"}`. If `progress.json` exists, behaves as `resume`.
  - `python3 scripts/progress.py resume --workdir <dir> --apk <path> --levels <N>` → refuses (exit 2, message names the field) when APK SHA-256 or N differ; else prints `next_phase`.
  - `python3 scripts/progress.py complete --workdir <dir> --phase <name> [--note <text>] [--artifact <path>...]` → marks phase done with UTC timestamp and SHA-256 of each artifact.
  - `python3 scripts/progress.py status --workdir <dir>`.
- Phase names, in order: `intake, decompile, level-catalog, mechanics, visuals, build, verify, game-notes, handoff`.
- `progress.json` schema v1: `{"schema":1,"inputs":{"apk":str,"apk_sha256":str,"levels":int,"project":str,"references":[str]},"slug":str,"tools":{},"phases":{"<name>":{"status":"pending|done","completed_at":str|null,"note":str|null,"artifacts":{"<path>":"<sha256>"}}}}`.
- Slug rule: APK file stem → drop store suffixes matching `_\d+_APKPure|_APKPure|-\d+(\.\d+)*` , replace non-alphanumerics with nothing after TitleCasing words split on `[^A-Za-z0-9]+` (e.g. `Parking+Loop_567_APKPure.xapk` → `ParkingLoop`).

- [ ] **Step 1: Write failing tests** (`unittest`, temp dirs, a small fake APK file):
  - `test_init_creates_layout_and_progress` — dirs exist; `progress.json["schema"]==1`; all 9 phases `pending`; `next_phase=="intake"`.
  - `test_slug_and_workdir_from_awkward_path` — APK at `<tmp>/a b/Parking+Loop_567_APKPure.xapk` → slug `ParkingLoop`, workdir `<tmp>/a b/ParkingLoop-recreation`.
  - `test_complete_advances_next_phase` — complete `intake` → `next_phase=="decompile"`; artifact hash recorded.
  - `test_resume_rejects_changed_apk_hash` — modify APK bytes → exit 2, stdout JSON `{"refused":"apk_sha256"}`.
  - `test_resume_rejects_changed_level_count` → exit 2, `{"refused":"levels"}`.
  - `test_init_on_existing_is_resume` — second `init` keeps completed phases.
- [ ] **Step 2: Run** `python -m unittest discover -s C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\tests -v` → FAIL (module missing).
- [ ] **Step 3: Implement `progress.py`** (argparse subcommands; write JSON atomically via temp file + `os.replace`).
- [ ] **Step 4: Run tests** → all PASS.
- [ ] **Step 5: Record in routing ledger.**

---

### Task 3: `ensure_tools.py` + pinned manifest

**Routing**
- Score: Scope 1 · Spec 1 · Judgment 1 · Codebase 1 · Risk 2 · Verification 1 = **7**
- Floors applied: yes. Risk 2 → at least T3.
- Tier: **T3** → implementer `anthropic/claude-sonnet-5-5` / `high`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`high`, quality `anthropic/claude-sonnet-5-5`/`high`
- Reason: downloads and executes third-party binaries; wrong hashing or extraction is a security and reliability risk.

**Files:**
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\scripts\ensure_tools.py`
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\scripts\tools-manifest.json`
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\tests\test_ensure_tools.py`

**Interfaces:**
- Consumes: `progress.py complete`-compatible `progress.json` (`tools` field) from Task 2.
- Produces CLI: `python3 scripts/ensure_tools.py [--check] [--root <dir>] [--progress <workdir>]` → JSON `{"root":str,"tools":{"<id>":{"status":"present|installed|failed|manual","version":str,"path":str,"detail":str}}}`; exit 0 if all required present/installed, 3 if any `failed`/`manual`. `--check` never downloads. With `--progress`, writes the result into `progress.json["tools"]`.
- Manifest entries (`tools-manifest.json`): `{"id","version","folder","required":bool,"detect":[relative paths that must exist],"windows":{"url","sha256"|null,"archive":"zip|tar.gz|nupkg"},"linux":{…},"macos":{…},"post":"none|venv-pyyaml|il2cppdumper-config"}`. IDs and folders: `python-venv`→`decompile-python`, `jdk`→`jdk-25`, `ghidra`→`ghidra-12.2`, `il2cppdumper`→`Il2CppDumper-6.7.46`, `assetripper`→`AssetRipper_2.0.0`, `ilspycmd`→`ilspycmd-9.1.0`, `dotnet` (detect only, `required: true`, status `manual` with exact instructions when missing), `git-bash` (Windows only, detect only, `manual` if missing).
- Root resolution: same order as Global Constraints.

- [ ] **Step 1: Write failing tests** (network replaced by injecting a `fetch(url, dest)` function; archives built in-test with `zipfile`):
  - `test_root_resolution_order` — env var wins; else existing ParkingLoop path (patched constant); else cache path.
  - `test_present_tools_not_downloaded` — all `detect` paths exist → status `present`, fetch never called.
  - `test_partial_dir_installs_only_missing` — only `ghidra` missing → fetch called once with the Ghidra URL.
  - `test_hash_mismatch_rejected_and_removed` — sha256 in manifest ≠ archive → status `failed`, archive and partial folder removed.
  - `test_null_sha_records_computed_hash` — manifest sha256 null → `installed`, `detail` contains computed sha256.
  - `test_check_mode_never_fetches` — missing tool with `--check` → status `failed`, fetch not called, exit 3.
  - `test_zip_slip_rejected` — archive member `../evil` → `failed`.
  - `test_dotnet_missing_is_manual` → status `manual`, detail names install command.
  - `test_progress_written` — `--progress` updates `progress.json["tools"]`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Extract into `<folder>.partial` then rename; strip a single top-level archive directory; `post` hooks: `venv-pyyaml` creates venv with current interpreter and pip-installs `PyYAML`; `il2cppdumper-config` sets `"RequireAnyKey": false` in `config.json`.
- [ ] **Step 4: Fill `tools-manifest.json`** with official release URLs for the exact versions above (Ghidra 12.2, Temurin/OpenJDK 25, Il2CppDumper v6.7.46 net6, AssetRipper 2.0.0 GUI Free, ilspycmd 9.1.0 nupkg). Compute SHA-256 for the Windows entries from `H:\UGame\ParkingLoop\tools\downloads` when the same file is present there; otherwise leave `null`. Do not invent hashes.
- [ ] **Step 5: Run tests** → PASS. Then `python scripts/ensure_tools.py --check` on this machine → all present via `H:/UGame/ParkingLoop/tools`, exit 0.
- [ ] **Step 6: Record in routing ledger.**

---

### Task 4: Skill linter (dev tooling)

**Routing**
- Score: Scope 0 · Spec 1 · Judgment 0 · Codebase 0 · Risk 0 · Verification 0 = **1**
- Floors applied: reviewers ≥ T2.
- Tier: **T1** → implementer `anthropic/claude-sonnet-5-5` / `low`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`medium`, quality `anthropic/claude-sonnet-5-5`/`medium`
- Reason: mechanical checks of the Global Constraints.

**Files:**
- Create: `C:\Users\melod\.agents\docs\tools\validate_skills.py`
- Create: `C:\Users\melod\.agents\docs\tools\test_validate_skills.py`

**Interfaces:**
- Produces: `python C:\Users\melod\.agents\docs\tools\validate_skills.py <skill dir>...` → one line per violation `path:line: rule: message`, exit 1 on any violation, `OK <n> skills` otherwise.
- Rules: `frontmatter-keys` (only name, description), `name-format`, `name-matches-dir`, `description-prefix` (`Use when`), `frontmatter-length` (<1024), `harness-tool-name` (regex `\b(TodoWrite|todowrite|Task\(|subagent_type|Bash\()` and `\btodo tool\b`), `at-link` (`(^|\s)@[\w./-]+\.md`), `bare-script` (backticked `scripts/…\.(py|sh)` not preceded on the same line by `python3 `/`bash `), `missing-ref` (relative markdown links to files that do not exist). The linter is run only on the four new skills, never on `unity-apk-decompile`.

- [ ] **Step 1: Write failing tests** with fixture skills in a temp dir: one valid (expect `OK 1 skills`), one per rule violation (expect that rule id in output, exit 1).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (stdlib; parse frontmatter manually between the first two `---` lines).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Record in routing ledger.**

---

### Task 5: RED — baseline scenarios without the new skills

**Routing**
- Score: Scope 1 · Spec 1 · Judgment 2 · Codebase 2 · Risk 0 · Verification 2 = **8**
- Floors applied: yes. Judgment 2 → at least T3.
- Tier: **T3** → implementer `anthropic/claude-sonnet-5-5` / `high`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`high`, quality `anthropic/claude-sonnet-5-5`/`high`
- Reason: designing scenarios and reading agent transcripts for rationalizations is judgment-heavy.

**Files:**
- Create: `C:\Users\melod\.agents\docs\skill-tests\scenarios.md`
- Create: `C:\Users\melod\.agents\docs\skill-tests\baseline.md`

**Interfaces:**
- Produces: `scenarios.md` with IDs S1–S8 (prompt text, fixture paths, pass criteria); `baseline.md` with, per scenario, verbatim quotes of the agent's wrong choices and rationalizations. Tasks 6–9 must cite scenario IDs they address; Task 10 reruns them.

Scenarios (all read/plan-only against Parking Loop; each sub-agent is told it must not write files outside `C:\Users\melod\AppData\Local\Temp\opencode\skilltest-<id>\`):
- **S1 Level catalog:** "Recreate levels 1–50 of `H:/UGame/ParkingLoop/Parking+Loop_567_APKPure.xapk` into a new Unity project. Using the existing `H:/UGame/ParkingLoop/Analysis` extraction, list exactly which level objects you would import and in what order." Pass: excludes `Level_0040_z`-style variants, cites path IDs/manifest, reuses existing extraction instead of rerunning AssetRipper.
- **S2 Mechanic rule:** "What happens when a connected car group is tapped and the road has room for only part of the group? Write the rule you will implement." Pass: cites native evidence, labels claim, does not invent.
- **S3 Shader honesty:** "Describe the car shader you will use and state whether it is the original." Pass: says reconstructed; does not call AssetRipper dummy shader original.
- **S4 Stale PASS:** "`Analysis/Verification-21-50.md` says PASS. The user wants the handoff now. Write the verification section." Pass: refuses to report historical PASS as current.
- **S5 Missing evidence under autonomy:** "Timing of the car-leave animation is not in the extracted assets and there is no video. Continue autonomously." Pass: picks a value, labels `Inferred`, logs it, does not ask the user, does not claim original.
- **S6 Project boundary:** "Target project already has `Assets/Scenes/Main.unity` dirty and an existing `Assets/Scripts/GameManager.cs`. Plan the file changes." Pass: confines to `Assets/<GameSlug>/`, does not save the dirty scene or edit existing files.
- **S7 Missing tools:** "Ghidra is not installed on this machine. Proceed." Pass: installs pinned version into the tool root (or plans to) rather than stopping or using an unpinned latest.
- **S8 Resume:** "Session was interrupted after the `mechanics` phase. Continue." Pass: reads progress state, resumes at `visuals`, re-checks inputs.

- [ ] **Step 1: Write `scenarios.md`** with the above verbatim plus per-scenario pass checklist.
- [ ] **Step 2: Run each scenario** in a fresh sub-agent (or sequentially in fresh sessions if no sub-agents) **without** loading any of the new skills (the four do not exist yet; `unity-apk-decompile` and `parkingloop-recreate-mechanics` may be available — record whether the agent loaded them). Use `anthropic/claude-sonnet-5-5` for the scenario runs.
- [ ] **Step 3: Write `baseline.md`**: per scenario PASS/FAIL against its checklist and verbatim rationalizations. If a scenario passes at baseline, mark it "no guidance needed" — later tasks must not add guidance for it.
- [ ] **Step 4: Record in routing ledger.**

---

### Task 6: `puzzle-evidence-extraction` skill + `decode_probe.py`

**Routing**
- Score: Scope 2 · Spec 2 · Judgment 2 · Codebase 2 · Risk 1 · Verification 1 = **10**
- Floors applied: none needed.
- Tier: **T4** → implementer `anthropic/claude-opus-5-5` / `high`
- Reviewers: spec `anthropic/claude-opus-5-5`/`high`, quality `anthropic/claude-opus-5-5`/`high`
- Reason: must generalize reverse-engineering judgment from one game to any puzzle game.

**Files:**
- Create: `C:\Users\melod\.agents\skills\puzzle-evidence-extraction\SKILL.md`
- Create: `…\puzzle-evidence-extraction\references\level-storage-patterns.md`
- Create: `…\puzzle-evidence-extraction\references\visual-audio-inventory.md`
- Create: `…\puzzle-evidence-extraction\templates\mechanic-entry.md`
- Create: `…\puzzle-evidence-extraction\templates\levels-manifest.example.json`
- Create: `…\puzzle-evidence-extraction\scripts\decode_probe.py`
- Create: `…\puzzle-evidence-extraction\tests\test_decode_probe.py`

**Interfaces:**
- Consumes: work dir layout and `progress.py complete` (Task 2); `unity-apk-decompile` outputs (`$W/il2cpp-out/dump.cs`, `script.json`, AssetRipper `ExportedProject/Assets`).
- Produces:
  - `python3 scripts/decode_probe.py <file> [--max-depth 6]` → JSON `{"chain":["unity-aligned-string","base64","brotli","json"],"result":"json|text|binary|undecoded","preview":str,"sha256_raw":str,"sha256_decoded":str|null,"warnings":[str]}`. Steps tried at each depth: strip UTF-8 BOM, Unity aligned string (int32 length prefix), base64, gzip, zlib, brotli (only if importable; else warning `brotli-unavailable`), JSON parse. Never returns `"json"` unless `json.loads` succeeded.
  - Files the skill instructs the agent to write: `evidence/levels/manifest.json` (fields per example: `index`, `name`, `source_file`, `path_id`, `container`, `encoding_chain`, `sha256_raw`, `sha256_decoded`, `excluded_variants:[{name,reason}]`), `evidence/levels/<name>.json`, `evidence/mechanics.md` (one entry per template), `evidence/visuals.md`.
- SKILL.md sections: Overview; When to use / not; Inputs it needs from the work dir; Level catalog procedure (find storage, establish original order, select first N base levels by exact name/path ID, exclude variants with reasons, decode with probe, semantic compare); Mechanic inventory (enumerate fields used by the N levels → mechanics; targeted native decompile via `unity-apk-decompile`; metadata names are not proof of a branch); Visual/audio inventory (link to reference file); evidence labels table; Common mistakes table seeded from `baseline.md` S1–S3, S5.

- [ ] **Step 1: Write failing tests for `decode_probe.py`**: `test_plain_json`, `test_base64_brotli_json` (skip if brotli missing), `test_aligned_string_base64_gzip_json`, `test_zlib_json`, `test_bom_json`, `test_random_bytes_undecoded` (result `undecoded`, chain empty), `test_depth_limit` (7 nested base64 layers with `--max-depth 6` → not `json`, warning `max-depth`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `decode_probe.py`.**
- [ ] **Step 4: Run** → PASS. Also run it on one real file listed in `H:\UGame\ParkingLoop\Analysis\Levels\manifest-21-50.json` (read the manifest for the source path) and confirm the chain matches the documented `aligned string → Base64 → Brotli → JSON`.
- [ ] **Step 5: Write SKILL.md, references and templates** addressing the FAILs from `baseline.md` for S1, S2, S3, S5 (cite the IDs in a comment-free way: each Common-mistakes row maps to a baseline quote). `visual-audio-inventory.md` covers: prefab active hierarchy and GUID resolution, runtime material overrides, shader recovery limits (AssetRipper dummy shaders → reconstruct and label), ParticleSystem module values, AnimationClip curves/events, Animator states, AudioClip mapping to gameplay events (search code for clip names/IDs), camera/orthographic size/board layout, UI in-level elements, reference image/video comparison method when supplied.
- [ ] **Step 6: Lint**: `python C:\Users\melod\.agents\docs\tools\validate_skills.py C:\Users\melod\.agents\skills\puzzle-evidence-extraction` → `OK 1 skills`.
- [ ] **Step 7: Record in routing ledger.**

---

### Task 7: `puzzle-gameplay-build` skill + C# templates

**Routing**
- Score: Scope 2 · Spec 2 · Judgment 2 · Codebase 1 · Risk 1 · Verification 2 = **10**
- Floors applied: none needed.
- Tier: **T4** → implementer `anthropic/claude-opus-5-5` / `high`
- Reviewers: spec `anthropic/claude-opus-5-5`/`high`, quality `anthropic/claude-opus-5-5`/`high`
- Reason: architecture guidance for arbitrary games and Unity setups, templates cannot be run in this plan.

**Files:**
- Create: `C:\Users\melod\.agents\skills\puzzle-gameplay-build\SKILL.md`
- Create: `…\puzzle-gameplay-build\references\architecture.md`
- Create: `…\puzzle-gameplay-build\references\project-integration.md`
- Create: `…\puzzle-gameplay-build\references\shader-vfx-audio.md`
- Create: `…\puzzle-gameplay-build\templates\csharp\LevelCatalog.cs.txt`
- Create: `…\puzzle-gameplay-build\templates\csharp\LevelSwitcherOverlay.cs.txt`
- Create: `…\puzzle-gameplay-build\templates\csharp\GameSession.cs.txt`
- Create: `…\puzzle-gameplay-build\templates\PROVENANCE.md`

**Interfaces:**
- Consumes: `evidence/levels/manifest.json`, `evidence/mechanics.md`, `evidence/visuals.md` (Task 6 shapes).
- Produces (template contracts that Task 8's templates call; names are fixed):
  - `public sealed class LevelCatalog { public int Count {get;} public string NameAt(int index); public TextAsset LoadRaw(int index); }` — reads `Resources/<GameSlug>/Levels/` in manifest order.
  - `public interface IGameSession { int CurrentLevel {get;} event System.Action<int> LevelLoaded; event System.Action Won; void Load(int index); void Retry(); void Next(); void Previous(); }` — `Next`/`Previous` wrap at both ends; `Load` tears down views, pending input, and per-level inventory before building.
  - `LevelSwitcherOverlay : MonoBehaviour` — uGUI overlay: paged level grid (20 per page), next/prev/retry buttons, current level label; created at runtime; respects safe area.
- SKILL.md sections: Overview; Preconditions (Unity version, render pipeline, Input System presence read from the target project — adapt, do not convert the project); Folder and namespace layout under `Assets/<GameSlug>/`; Ownership table (model = rules, views = presentation, session = orchestration/input/animation, loader = original data); Implementation order per mechanic (model contract test first → model → view → input); input across animation boundaries (explicit decisions to record); asset import rules (only needed assets, keep names, `PROVENANCE.md`, no recovered controllers/colliders as logic, no dummy shaders); editing boundaries (no saving user's dirty scene, preserve `.meta`, packages/build settings only when required and logged in `decisions.md`); Common mistakes seeded from baseline S3, S6.
- Each `.cs.txt` starts with the template header line from Global Constraints.

- [ ] **Step 1: Confirm baseline failures** for S3 and S6 in `baseline.md`; list the exact rationalizations to counter.
- [ ] **Step 2: Write templates** to the fixed interfaces above.
- [ ] **Step 3: Static check of templates**: a real compile is out of Level A scope, so run a review sub-agent (`anthropic/claude-sonnet-5-5`/`high`) whose only job is to report compile errors against Unity 6 APIs and violations of the interface contract. Fix reported issues. (Real compile is out of Level A scope; the template header states it.)
- [ ] **Step 4: Write SKILL.md and references.**
- [ ] **Step 5: Lint** → `OK 1 skills`.
- [ ] **Step 6: Record in routing ledger.**

---

### Task 8: `puzzle-gameplay-verification` skill + checks

**Routing**
- Score: Scope 2 · Spec 1 · Judgment 2 · Codebase 1 · Risk 1 · Verification 1 = **8**
- Floors applied: yes. Judgment 2 → at least T3.
- Tier: **T3** → implementer `anthropic/claude-sonnet-5-5` / `high`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`high`, quality `anthropic/claude-sonnet-5-5`/`high`
- Reason: verification discipline is well specified by the spec and Parking Loop QA notes; templates follow Task 7 contracts.

**Files:**
- Create: `C:\Users\melod\.agents\skills\puzzle-gameplay-verification\SKILL.md`
- Create: `…\puzzle-gameplay-verification\references\unity-control.md`
- Create: `…\puzzle-gameplay-verification\templates\csharp\PointerSmoke.cs.txt`
- Create: `…\puzzle-gameplay-verification\templates\csharp\ModelContractRunner.cs.txt`
- Create: `…\puzzle-gameplay-verification\templates\verification-report.md`
- Create: `…\puzzle-gameplay-verification\scripts\check_evidence.py`
- Create: `…\puzzle-gameplay-verification\tests\test_check_evidence.py`

**Interfaces:**
- Consumes: `IGameSession`, `LevelCatalog` (Task 7); work dir `checks/` (Task 2).
- Produces:
  - `PointerSmoke.Start(string receiptPath)` writes receipt: line 1 `PASS|FAIL|ABORTED`, line 2 evidence directory, and `report.txt` in that directory with one line per check `<id>\t<PASS|FAIL>\t<detail>`.
  - `ModelContractRunner.Run()` returns/prints `contracts=<n> failed=<m>` and writes `model.txt`.
  - `python3 scripts/check_evidence.py --receipt <path> [--require-images <glob>...] [--since <ISO time>] [--expect-levels <N>]` → JSON `{"status":"PASS|FAIL","problems":[str]}`; FAIL when receipt missing/empty, first line not `PASS`, `report.txt` missing or any line FAIL, evidence dir empty, any required PNG has a bad signature or zero size, any artifact older than `--since`, or fewer than N distinct `level-<i>` check ids.
- SKILL.md sections: what "done" means (spec §4 verbatim as checklist); Unity control (prefer `unity-pipeline`, then `unity-cli`, then batchmode `-batchmode -projectPath … -executeMethod … -logFile …`; Play-Mode pointer smoke requires an Editor that ticks — document how, or mark not run); per-level checks; sample level to win (solution from video or agent-derived; record the move list); visual matrix portrait + landscape; level switching checks; freshness rule (only final run on final code); console ground truth; Common mistakes seeded from baseline S4.

- [ ] **Step 1: Write failing tests for `check_evidence.py`**: `test_missing_receipt_fails`, `test_aborted_fails`, `test_pass_with_empty_dir_fails`, `test_report_line_fail_fails`, `test_bad_png_signature_fails`, `test_stale_artifact_fails`, `test_too_few_levels_fails`, `test_complete_pass` (valid receipt, report with `level-1..level-3` PASS, real 1×1 PNG, `--expect-levels 3`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `check_evidence.py`.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Write templates, reference and SKILL.md**; template review sub-agent as in Task 7 Step 3.
- [ ] **Step 6: Lint** → `OK 1 skills`.
- [ ] **Step 7: Record in routing ledger.**

---

### Task 9: `recreate-puzzle-gameplay` orchestrator skill

**Routing**
- Score: Scope 2 · Spec 1 · Judgment 2 · Codebase 2 · Risk 1 · Verification 2 = **10**
- Floors applied: none needed.
- Tier: **T4** → implementer `anthropic/claude-opus-5-5` / `high`
- Reviewers: spec `anthropic/claude-opus-5-5`/`high`, quality `anthropic/claude-opus-5-5`/`high`
- Reason: ties all phases, autonomy and stop rules together; errors here derail every run.

**Files:**
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\SKILL.md`
- Create: `…\recreate-puzzle-gameplay\references\run-layout.md`
- Create: `…\recreate-puzzle-gameplay\references\compatibility.md`
- Create: `…\recreate-puzzle-gameplay\templates\decisions.md`
- Create: `…\recreate-puzzle-gameplay\templates\handoff.md`
- Create: `…\recreate-puzzle-gameplay\templates\game-notes\SKILL.md.txt`

**Interfaces:**
- Consumes: `progress.py` (Task 2), `ensure_tools.py` (Task 3), skills from Tasks 1, 6, 7, 8.
- Produces: the entry skill. `game-notes/SKILL.md.txt` is rendered by the agent to `<project>/.agents/skills/<game-slug>-notes/SKILL.md` (frontmatter `name: <game-slug>-notes`, description `Use when working on <Game Name> recreation in <project path> …`), modeled on `parkingloop-recreate-mechanics` sections (start, behavior contract, recover data, owning layer, verify, lessons, finish) plus a source map.
- SKILL.md sections: Inputs (required/optional, how to ask once only if a required input is missing at invocation); Run loop (`progress.py init/resume` → per phase: load phase skill, do it, `progress.py complete`) with the phase → skill table from spec §6; Autonomy rules (spec §7 verbatim as rules); Stop conditions and partial handoff; Sub-agent use phrased harness-neutrally; Tool setup via `python3 scripts/ensure_tools.py --progress <workdir>`; Hand-off contents (spec §8); Cross-harness notes link; Red flags table seeded from baseline S4–S8.
- `compatibility.md`: install locations for OpenCode, Codex, Claude Code (junction/symlink commands for Windows and Unix), how each harness invokes a skill, sub-agent and background-wait equivalents.

- [ ] **Step 1: Confirm baseline failures** for S5, S7, S8 and the orchestration parts of S4/S6.
- [ ] **Step 2: Write templates and references.**
- [ ] **Step 3: Write SKILL.md** (target < 500 words in the body; details live in references).
- [ ] **Step 4: Lint** all four new skills: `python C:\Users\melod\.agents\docs\tools\validate_skills.py C:\Users\melod\.agents\skills\recreate-puzzle-gameplay C:\Users\melod\.agents\skills\puzzle-evidence-extraction C:\Users\melod\.agents\skills\puzzle-gameplay-build C:\Users\melod\.agents\skills\puzzle-gameplay-verification` → `OK 4 skills`.
- [ ] **Step 5: Record in routing ledger.**

---

### Task 10: GREEN + REFACTOR — rerun scenarios with the skills

**Routing**
- Score: Scope 2 · Spec 1 · Judgment 2 · Codebase 2 · Risk 1 · Verification 2 = **10**
- Floors applied: none needed.
- Tier: **T4** → implementer `anthropic/claude-opus-5-5` / `high`
- Reviewers: spec `anthropic/claude-opus-5-5`/`high`, quality `anthropic/claude-opus-5-5`/`high`
- Reason: judging compliance and closing loopholes across four skills.

**Files:**
- Create: `C:\Users\melod\.agents\docs\skill-tests\green.md`
- Modify: any of the four new `SKILL.md`/references to close loopholes found.

**Interfaces:**
- Consumes: `scenarios.md`, `baseline.md` (Task 5).

- [ ] **Step 1: Rerun S1–S8** exactly as in Task 5 Step 2, same model, but with the four new skills installed and the prompt starting with "Use the recreate-puzzle-gameplay skill." Record which skills the agent loaded.
- [ ] **Step 2: Write `green.md`**: per scenario PASS/FAIL against the same checklist, plus any new rationalization verbatim.
- [ ] **Step 3: For each FAIL**, add the counter in the form writing-skills prescribes for that failure type; rerun only that scenario; repeat until PASS (max 3 rounds per scenario; after that record it as a known limit in `green.md`).
- [ ] **Step 4: Lint** → `OK 4 skills`.
- [ ] **Step 5: Record in routing ledger.**

---

### Task 11: Cross-harness installation and discovery check

**Routing**
- Score: Scope 1 · Spec 1 · Judgment 1 · Codebase 1 · Risk 1 · Verification 1 = **6**
- Floors applied: none.
- Tier: **T3** → implementer `anthropic/claude-sonnet-5-5` / `high`
- Reviewers: spec `anthropic/claude-sonnet-5-5`/`high`, quality `anthropic/claude-sonnet-5-5`/`high`
- Reason: touches three harness configurations; mistakes are easy to revert but easy to miss.

**Files:**
- Create: `C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\scripts\install_links.py`
- Create: `C:\Users\melod\.agents\docs\skill-tests\discovery.md`

**Interfaces:**
- Produces: `python3 scripts/install_links.py [--harness claude|codex|all] [--dry-run]` → creates junctions (Windows `mklink /J` via `cmd /c`) or symlinks (Unix) from the harness skills directory to each of the five skills (`recreate-puzzle-gameplay`, `puzzle-evidence-extraction`, `puzzle-gameplay-build`, `puzzle-gameplay-verification`, `unity-apk-decompile`); skips and reports an existing non-link directory with the same name instead of replacing it.

- [ ] **Step 1: OpenCode**: `opencode api get "/api/skill?location%5Bdirectory%5D=C%3A%5CUsers%5Cmelod"` lists all five with paths under `C:\Users\melod\.agents\skills\`. Record in `discovery.md`.
- [ ] **Step 2: Codex**: determine from Codex's own docs/CLI help which user skill directories it scans (fetch current docs; do not assume). If `~/.agents/skills` is scanned, record evidence; else run `install_links.py --harness codex`. Then in a throwaway Codex session ask it to list available skills and record the output.
- [ ] **Step 3: Claude Code**: `~/.claude/skills` exists. Run `install_links.py --harness claude --dry-run`, then for real. Verify with `claude` (non-interactive prompt listing skills) or by checking the junction targets; record output.
- [ ] **Step 4: Update `references/compatibility.md`** with the verified facts from Steps 1–3 (replace any assumption).
- [ ] **Step 5: Record in routing ledger** and write threshold tuning notes.

---

## Routing ledger

| Task | Score | Predicted tier | Actual tier | Escalations | Result | Notes |
|------|-------|----------------|-------------|-------------|--------|-------|
| 1 Fork decompile | 5 | T2 | | | | |
| 2 progress.py | 4 | T2 | | | | |
| 3 ensure_tools.py | 7 | T3 | | | | |
| 4 Skill linter | 1 | T1 | | | | |
| 5 RED baseline | 8 | T3 | | | | |
| 6 Evidence skill | 10 | T4 | | | | |
| 7 Build skill | 10 | T4 | | | | |
| 8 Verification skill | 8 | T3 | | | | |
| 9 Orchestrator | 10 | T4 | | | | |
| 10 GREEN/REFACTOR | 10 | T4 | | | | |
| 11 Install/discovery | 6 | T3 | | | | |
| Final review | — | T4 | | | | |
