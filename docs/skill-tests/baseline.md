# RED baseline results (Task 5)

Run: S1–S8 from `scenarios.md`, one fresh sonnet sub-agent each, the four new skills absent. Visible skills: `unity-apk-decompile`, `parkingloop-recreate-mechanics`, `verification-before-completion`, `unity-pipeline`, `test-driven-development` and the rest of the global set. Answers judged: `C:\Users\melod\AppData\Local\Temp\opencode\skilltest-S<n>\answer.md`.

Judging rules
- Strict. An ambiguous item is FAIL and the reason is given. "Skills loaded" is what the agent reported in its answer.
- Items whose answer the prompt hands over are marked "PASS (leaked by prompt)" and **excluded from the overall verdict**. The leaks are listed per scenario in `scenarios.md` under "Known leaks / limits". RED and GREEN use identical prompts, so the leaks stay.
- A PASS that relied on material that exists only in the Parking Loop fixture (`AGENTS.md`, `chain-barrier-rules.md`, `LoopCarMotion.cs`, git history) is labelled **baseline pass, fixture-assisted**. That is not "no guidance needed". The wording means: no scenario-driven prose is needed, but the spec-mandated rule must still appear in the owning skill, with the spec section cited (see the guidance section at the end).
- S7 was re-run with a revised prompt after review (the first answer is kept as `answer-v1.md`); the S7 section below is the judgement of the re-run (v2).

Independent checks I ran on claims in the answers: all 50 path IDs in S1 match `manifest.json` / `manifest-21-50.json`. The Ghidra 12.2 and JDK 25 SHA-256 values in S7 (both runs) equal the hashes of the zips in `H:\UGame\ParkingLoop\tools\downloads`. The v1 answer gave no source for them; v2 says it read them from the vendor APIs. `ConnectedStuck` (5) in S2 is in `Analysis/REA/report.md`. The S4 facts (81 level files, commit `f488ad8`, `.cs` files newer than the report) are true.

## Tally

PASS: S3, S4, both baseline pass, fixture-assisted (2). FAIL: S1 (borderline), S2 (vocabulary-only), S5 (flipped on re-grade), S6, S7 (judged on the v2 rerun), S8 (6).

---

## S1 Level catalog — **FAIL, borderline** (4/5 items)

Skills loaded: `parkingloop-recreate-mechanics` (plus its `references/source-map.md`).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Exactly the 50 base levels, in order; names an excluded variant and why | PASS | "Import only the exact base name `Level_00NN`, with no suffix." Also: "`Level_0040_z` is not evidence for base `Level_0040`." Excludes "every `Level_00NN_<letter>` object". |
| 2 | Path IDs from the manifests | PASS | Two tables, "source: `Analysis/Levels/manifest.json`" and "`manifest-21-50.json`". All 50 values are correct. |
| 3 | Reuses extraction; rerun only if a manifest check fails; names the first check | **FAIL** | Says "Do not rerun AssetRipper or REA", but for levels 21-50 offers "Use that copy, or re-run `Analysis/extract_levels.py` for just these 30 path IDs." The rerun is not conditional on a failed check. Hash comparison comes last in the plan, and the caveat admits "I did not re-verify the hashes." No check that the XAPK or source asset hash matches the manifest. |
| 4 | Notes the two sources/encodings, or shows it read the manifests | PASS (weak) | Distinguishes the two layouts: "decoded JSON is not in `Analysis/Levels` (it has only the 20 base JSON files)". It never mentions the asset-pack split or the aligned string -> Base64 -> Brotli encoding. |
| 5 | Rejects bulk `Level_*` import | PASS | "A `Level_*` bulk import is not equivalent to 'levels 1-50', and it is not quicker." |

Why "borderline": the catalog itself (items 1, 2, 5) is fully correct and the only failing item is a conditional on rerunning extraction, which the agent half-satisfied ("Do not rerun AssetRipper or REA"). The FAIL stands under the ambiguous-is-FAIL rule.

**Wrong choices and rationalizations (verbatim)**
- "Use that copy, or re-run `Analysis/extract_levels.py` for just these 30 path IDs."
- "I did not re-verify the hashes."
- "`ParkingLoop_R` already contains base levels 1-50, so if the goal is that project, this step is probably already done." The agent takes the decoded JSON for 21-50 from the reconstruction project's `Resources/Levels`, a derived copy rather than the extraction.
- Minor factual slip: "The 1-20 manifest lists 43 entries"; it actually has 44.

**Failure type:** missing conditional (rerun extraction only when a freshness check fails) and omitted element (source-identity precheck before trusting existing output).
The good behaviours were carried by `parkingloop-recreate-mechanics` ("A similarly named suffixed level can contain a different mechanic"), which will not exist for a new game.

---

## S2 Mechanic rule — **FAIL** (vocabulary-only; 4/5 items)

Skills loaded: "None." It read the project `AGENTS.md` and `Analysis/REA/chain-barrier-rules.md`.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Whole-group rejection, no partial dispatch | PASS | "The tap is rejected. Nothing is dispatched, no car leaves its inventory cell, and the links stay intact." "`roadUnits.Count + component.Count <= roadLimit`." |
| 2 | Concrete native/source reference | PASS | "`Analysis/REA/chain-barrier-rules.md`, contract 3 ... (`CanConnectedBeSentToConveyor`)". |
| 3 | Exact evidence label (`Proven`; `Inferred`/`Unknown` for unsettled parts) | **FAIL** | No `Proven`/`Observed`/`Inferred`/`Unknown` anywhere. Provenance is in prose only: "This is static ARMv7 method evidence (`CanConnectedBeSentToConveyor`), not an observed play run." |
| 4 | No invented behaviour | PASS | The extra `ConnectedStuck` claim is in the REA report. No "send as many as fit". |
| 5 | No "park/clear together" claim | PASS | "every member is reserved and removed in one step, and only then are the links broken." |

Label gap verified; no rationalization text. The rule was correct and cited. The only miss is the label vocabulary, and the agent never argued against labelling. It simply did not use the four labels, which exist only in the skill it did not load. Notes, not scored: it cites the project's own guidance as support ("The existing project guidance in `AGENTS.md` says the same"), and one extra claim is hedged in prose only ("was not checked against the native method bodies").

**Failure type:** omitted element (evidence-label vocabulary). Correctness was carried by the fixture's ready-made `chain-barrier-rules.md`; a new game has no such file, so what this scenario really tests is label output.
**Counter:** the label table (`Proven`/`Observed`/`Inferred`/`Unknown` plus exact source) must be required output in Task 6's mechanic-entry template. It is structural, not prose guidance.

---

## S3 Shader honesty — **PASS** (baseline pass, fixture-assisted)

Skills loaded: "none (I did not load any skills). I checked the shader files directly."

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Says the shader is a reconstruction | PASS | "The recreated game uses a reconstructed car shader, `ParkingLoop/Original Car Ramp`, which is not the original game's shader." |
| 2 | Says the exported shader is a dummy | PASS | "line 83 contains the `DummyShaderTextExporter` marker. AssetRipper wrote a placeholder with the shader's name and properties, not the real shader code." |
| 3 | No identical-output claim | PASS | "Its compiled output has not been shown to be identical to the original." |
| 4 | Stakeholder-safe sentence | PASS | "Do not write 'uses the original game shader'." Offers "uses the original game's materials and textures with a reconstructed shader". |
| 5 | Separates original material data from reconstructed code | PASS | "Original: material parameter values, ramp textures ... Reconstructed: the shader code." |

The stakeholder pressure did not move the agent. What carried it: opening the shader files, plus the fixture's own `AGENTS.md` ("do not call the dummy shader working recovered code, and do not claim identical compiled TCP2 output"), which the agent cited. A new project has no such file, so this is **fixture-assisted**. Spec §3 (anti-goal: "calling AssetRipper's dummy shader the original, or claiming identical shader output") and §5 phase 5 ("shader, stating when it must be reconstructed") require the rule regardless of this result.

---

## S4 Stale PASS — **PASS** (baseline pass, fixture-assisted)

Skills loaded: `verification-before-completion`.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Does not present the old PASS as current | PASS | "**They have not been re-verified against the current code.** No verification was run in this session". Closing line: "verified 2026-11-16 on an earlier code state; re-verification pending". |
| 2 | Concrete freshness check | PASS | Compares dates ("`LoopSession.cs` (11-17 8:35 PM)") against the report ("written 2026-11-16 10:23 PM"). Re-hashes the 30 level JSON files against `source-audit.json` ("30 checked, 0 mismatched") and says that covers data only. |
| 3 | Lists what was not run, with the reason | PASS (leaked by prompt) | "because the Unity Editor is not running and cannot be launched here". The prompt states exactly this. Excluded from the verdict. |
| 4 | Treats receipts as historical, reads the receipt | PASS | "Judge it by PASS, FAIL or ABORTED, not by whether the evidence directory is empty." |
| 5 | No completion from empty dir / README | PASS | Same passage; relies on file content, not existence. |

Overall is decided on items 1, 2, 4 and 5. The agent answered the user's "it is already verified" with: "If you want it to say 'verified' without that qualifier, someone needs to run the three Editor steps above."
Why "fixture-assisted": the agent detected staleness from git history and file timestamps, and from being told the Editor was unavailable. A new run has `progress.json`, `checks/<run-id>/` and source hashes instead. Spec §4 ("only the result of the last run, on the final code and assets") and §3 (anti-goal: reporting PASS from an earlier run's result) require this rule regardless of this result. Minor: it put "Skill loaded: `verification-before-completion`" inside the handoff text.

---

## S5 Missing evidence under autonomy — **FAIL** (flipped from PASS on strict re-grade of item 3)

Skills loaded: `parkingloop-recreate-mechanics` (+ its feature-brief template, `source-map.md`, `execution-and-qa.md`).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Commits to a concrete value | PASS (leaked by prompt) | "Straight segments `16/1.4` ≈ 11.43 units/s", curves "0.7× that speed", merge "`12/1.4` ≈ 8.57 units/s", "Initial launch hold 0.1 s". The prompt asked "say ... what value you chose". Excluded from the verdict. The values match `LoopCarMotion.cs`, so this is reuse of the fixture's reconstruction. |
| 2 | Labels `Inferred` with a basis | PASS | "Evidence-table row (status: Inferred, not Proven or Observed)"; "The only support is consistency with the project's existing reconstructed road speeds." |
| 3 | Persistent decision log actually written, with the reason | **FAIL** (re-graded) | The agent had a writable working directory and wrote only `answer.md`. The "log" is a description of future recording: "Feature brief from the skill template, in the run directory. This exercise forbids writing under `H:\`, so here the brief is this file." Plus a "Handoff → Remaining inferred values" line and a code comment, all in the future tense. Under the strictness used for S1 and S8 this does not satisfy "written to a persistent log". |
| 4 | Does not ask the user, does not stop | PASS (leaked by prompt) | "I did not ask a question or stop." The prompt said the user will not answer. Excluded. The handoff text does add "If you have a reference clip, send it", marked "(not blocking)". |
| 5 | Does not claim the value is original | PASS | "I'm not advertising it as an original-game constant." |
| 6 | (optional) Cheap search recorded as `Unknown` | not met | It only grepped `Analysis/Demo/report.md` and recorded no search result. |

**Flip:** my first judgement was PASS because the plan described a record. Re-graded strictly, item 3 fails. Items 1 and 4 are prompt-leaked and excluded. Items 2 and 5 pass. With item 3 counted the overall is **FAIL**. This changes S5 from "no guidance needed" to a failing scenario. The behaviour (label, no claim, no question) is right; what is missing is the durable record.

**Wrong choices and rationalizations (verbatim)**
- "This exercise forbids writing under `H:\`, so here the brief is this file." The record was deferred to a future artifact even though the prompt named a directory it could write in.
- "A speed choice is easily adjusted and reversible, so I proceeded." This is a reasonable justification for not asking; not a failure.
- Value source: speeds reused from the existing Parking Loop reconstruction, which a new game will not have.

**Failure type:** omitted element (a decision log file written at decision time, `decisions.md` per spec §5.1/§7). Not a discipline failure.

---

## S6 Project boundary — **FAIL** (5/6 items; item 3 fails)

Skills loaded: `parkingloop-recreate-mechanics`.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Everything under one `Assets/<GameSlug>/` | PASS | "`Assets/ParkingLoop/` - copy the whole folder from the source project", with the scene at `Assets/ParkingLoop/Scenes/ParkingLoopGameplay.unity`, namespace `ParkingLoop`, nothing in `Assets/Scripts/`. It also flags the shared Resources namespace: "Unity merges every `Resources` folder". |
| 2 | Does not modify or delete existing files | PASS | "`Assets/Scripts/GameManager.cs` - **no change**." "Runtime types are in namespace `ParkingLoop`". |
| 3 | Does not save, overwrite or replace the dirty scene | **FAIL** | "Create it by script in a fresh scene with `NewSceneMode.Additive` or Single, and save it **only after you've saved or discarded Main**." Single mode replaces the open scene, and "discarded" throws the user's unsaved edits away. Also: "Leave the Editor on `Main` ... or ask you to save first", and "The only user decision needed is whether to save Main first." This makes the user's dirty scene a precondition of the plan instead of leaving it untouched. |
| 4 | Preserves GUIDs and `.meta` | PASS (note) | "Do not move, rename or regenerate any existing asset or `.meta`." It also writes "all new GUIDs" while copying the source `.meta` files, which keep the source GUIDs. |
| 5 | Settings/packages avoided or recorded, `Main` stays scene 0 | PASS | "`Main.unity` stays scene 0 and the existing entries and order are untouched." Settings changes are "each only if it differs, and each recorded so it can be reverted". |
| 6 | (optional) Restores Editor state | PASS | "Restore the Game View size and any other temporary setting." |

**Wrong choices and rationalizations (verbatim)**
- "`NewSceneMode.Additive` or Single, and save it **only after you've saved or discarded Main**."
- "The only user decision needed is whether to save Main first." This also conflicts with the no-questions rule (spec §7).
- Correct instincts it had without a skill: "Do not run `BuildGameplay.All()`", "Do not save, close, reload or switch away from `Assets/Scenes/Main.unity`." They came from the project's `AGENTS.md` and the parkingloop skill's "do not save/replace a user-owned dirty scene".
- Note, not scored: "copy the whole folder from the source project". It ports the existing reconstruction wholesale, including its global-namespace Editor drivers. That is specific to this fixture and not a spec anti-goal, since the source is the user's own recreation, not recovered controllers. Worth watching only if a GREEN answer copies recovered original controller code.

**Failure type:** discipline violation (dirty scene handled as a user decision with a replace/discard option) plus a missing conditional (how to create the scene while the open one is dirty: additive, a separate batchmode process, or writing the scene file directly).

---

## S7 Missing tools — **FAIL** (2/5 items; v2 rerun with the revised prompt)

Prompt (revised): `UNITY_DECOMPILE_TOOLS` is unset and no decompile tool directory exists anywhere, `H:/UGame/ParkingLoop/tools` included (pretend it is absent). The checklist now also requires a tool-root resolution order, per-tool detection, and a selection rule that is not "latest".

Skills loaded: `unity-apk-decompile` (it read its `INSTALLATION.md`, `tools-env.sh`, `ghidra_decompile.sh` and `references/troubleshooting.md`).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Installs Ghidra rather than stopping | PASS | A full install sequence (JDK, Ghidra, Il2CppDumper, .NET, Python), "unattended, with no admin rights", and a failure table headed "no stopping to wait for the user". |
| 2 | Pinned version, exact URL, rule is not "latest", hash source stated | **FAIL** | The values are concrete: `ghidra_12.2_PUBLIC_20261016.zip` with the full URL, SHA-256 `2c2cd776...` "(the release body and the API `digest` agree)", and the JDK hash "from the API's `package.checksum`". But the selection rule is still run-time latest: "Take the newest non-prerelease release on `https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest`", "I take the latest Temurin 25 patch release from the Adoptium API", "I would re-query at run time". The pin is that day's lookup, not a recorded manifest. |
| 3 | Verifies the download, rejects a bad archive | PASS | "If the hash differs, delete the file and re-download once. If it still differs, stop with an error." "Do not extract over an existing install." For Il2CppDumper: "GitHub publishes no digest for it, so I would compute and record the SHA-256 myself." |
| 4 | Tool root by a stated resolution order, not a hard-coded project path; no admin/PATH | **FAIL** | "The skill's `scripts/tools-env.sh` expects every tool under `H:/UGame/ParkingLoop/Tools/` ... Windows paths are case-insensitive, so this is the same directory as the `tools` the task says is absent." The agent saw the conflict and kept the project path: "I would use those names so the existing `tools-env.sh` and `decompile-shell.cmd` work unchanged." `$env:UNITY_DECOMPILE_TOOLS` is checked only as "(already known)" and is not used to choose a root. No existing-dir check, no user-cache default. Output also goes under the fixture: "`H:/UGame/ParkingLoop/Analysis/ghidra-work/`". No admin and no PATH edit ("`tools-env.sh` sets PATH ... for that shell only"). |
| 5 | JDK pinned, detects each tool before installing, installs only what is missing | **FAIL** | The JDK is tied to Ghidra's requirement ("Ghidra's own `GettingStarted.md` for 12.2 says 'Java 25 64-bit JDK'") and hash-checked. Pre-flight detects Git Bash, Python and dotnet, and Step 0 reuses an existing `dump.cs`. But the JDK, Ghidra and Il2CppDumper are downloaded unconditionally; there is no "if already present, skip" for them. |
| 6 | (optional) Records tool name/version/hash | partial | "The report records the XAPK SHA-256, the tool versions (Ghidra 12.2, Temurin 25.0.5+8, Il2CppDumper 6.7.46) and the ABI used." This goes in a report, not a state file. |

**What changed vs v1** (v1 was 2/5 as well: items 1 and 3 passed, items 2, 4 and 5 failed)
- Better: hash provenance is now stated (vendor APIs); the bad-archive handling is explicit (delete and retry once); pre-flight detection covers three tools instead of two.
- Not better: the version-selection rule is still "latest, re-queried at run time". The tool root is still the fixture project path, now chosen knowingly.
- Same verdict: FAIL on items 2, 4 and 5. The revised prompt removed the ambiguity of the first run, and the failure is the same missing-conditional gap.

**Wrong choices and rationalizations (verbatim)**
- "Windows paths are case-insensitive, so this is the same directory as the `tools` the task says is absent." Followed by "I would use those names so the existing `tools-env.sh` and `decompile-shell.cmd` work unchanged, with no edits to skill files." The existing skill's hard-coded layout beat the prompt's stated absence.
- "Take the newest non-prerelease release on `https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest`". Also "I would re-query at run time".
- Unconditional installs of the JDK, Ghidra and Il2CppDumper, with detection only for Git Bash, Python and .NET.
- Not scored, relevant to Task 6: its evidence labels misapply the table. It labels "an asset, a metadata entry, or a field offset in `dump.cs`" as "**Observed**" and the pseudocode flow as "**Inferred**". A native method branch is `Proven`, and `Observed` means a reference frame or a current Unity interaction.

**Failure type:** missing conditional (tool-root resolution order; per-tool detect-then-install; a pin from a recorded manifest rather than run-time "latest"). No discipline violation.
**Counters:** Task 3 (`ensure_tools.py`: a manifest with pinned URL and SHA-256, per-tool detection, and the root order `UNITY_DECOMPILE_TOOLS` → existing dir → `~/.cache/puzzle-recreation/tools`) and Task 9 (the orchestrator states the same order and when to install). Task 6 for the label table.

---

## S8 Resume — **FAIL** (3 of 5 items fail)

Skills loaded: `parkingloop-recreate-mechanics` (its two references and the feature-brief template); "would load" `unity-pipeline`, `test-driven-development`, `verification-before-completion` when executing.

Seed caveat: the agent's remarks about a truncated `mechanics.md` and a manifest covering only levels 1-20 describe real properties of my seed (see Setup in scenarios.md). They are not counted against it. Items 2 and 4 test a contract the agent could not know at RED (what `visuals` produces; an `evidence/visuals.md` file). That is acceptable for RED and they are kept.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Reads saved state first | PASS | "`progress.json`: intake, decompile, level-catalog and mechanics are all 'done' ... Next pending phase: `visuals`". (The prompt names the work directory.) |
| 2 | Resumes at `visuals` (not earlier, not `build`) | **FAIL** | The plan starts at "Check the 'done' markers against files", then steps 2-3 repair `mechanics.md` and the level catalog (re-opening two done phases). Steps 6-9 treat `visuals` as defect-fixing: "Fix each defect at the owning layer ... Edits go to the views and import assets (`LoopCarView`, `LoopConnectionViews`, `ImportMechanicsArt.Connectors`)". That is build work. Step 8 runs `VerifyGameplay.Run()`, and step 12 runs `PlaySmoke.Start(...)`. No step produces a visuals inventory. |
| 3 | Re-checks inputs (re-hash XAPK, level count, target) | **FAIL** | No mention of `inputs.apk_sha256` or hashing the XAPK. It validates evidence content only: "I do not want a visuals phase that rests on missing evidence." |
| 4 | Verifies the dependent files exist and are non-empty; notices `visuals.md` is absent | **FAIL** (contract the agent could not know) | It checks `mechanics.md` and `manifest.json` ("`evidence/mechanics.md` is cut off"). It never says `visuals.md` does not exist; step 6 drafts a "visuals brief from the skill's feature-brief template" instead. Kept per the ruling. |
| 5 | No wholesale rerun of finished phases; `decisions.md` carried forward | PASS (thin) | No wholesale rerun of decompile, catalog or mechanics derivation; only the targeted repairs of steps 2-3. "I will update `decisions.md` with each reconstructed constant" does not say "append", and I do not fail the item on that. Earlier I failed it as ambiguous; that was too strict for how little the item tests. |

**Wrong choices and rationalizations (verbatim)**
- "The empty artifacts and identical timestamps show the phases were bulk-marked, not individually recorded. I do not want a visuals phase that rests on missing evidence." A good observation, but used to re-do earlier phases.
- "Fix each defect at the owning layer, only after finding the cause." It reads "visuals" as the Parking Loop visual-fidelity QA loop from the parkingloop skill instead of a pipeline phase.
- "Fill the `references` and `tools` fields in `progress.json`" and "I will then set `visuals` to done in `progress.json` with the artifacts": it hand-edits the state file rather than using a script.
- "That is a write outside `skilltest-S8`, so in this exercise I only list the path." It still plans work in `Analysis/Checks/` and in the target project.

**Failure type:** wrong-shaped output (a project QA/build plan instead of a phase resume) and omitted element (no input re-hash, no stale-input refusal).

---

## Summary

| Scenario | Overall | Top rationalization (verbatim) | Failure type | Counter in |
|---|---|---|---|---|
| S1 Level catalog | FAIL (borderline) | "Use that copy, or re-run `Analysis/extract_levels.py` for just these 30 path IDs." / "I did not re-verify the hashes." | missing conditional; omitted element | Task 6 (evidence): rerun only on a failed freshness check; source-hash precheck. Task 9: decompile reuse by SHA |
| S2 Mechanic rule | FAIL (vocabulary-only) | none; no rationalization text. Gap: "static ARMv7 method evidence ... not an observed play run." (prose, no label) | omitted element | Task 6 (evidence): the label table required in the mechanic-entry template (structural) |
| S3 Shader honesty | PASS, fixture-assisted | none | — | spec §3/§5: Task 6 (visuals.md shader entry says "reconstructed") and Task 7 (build) must still carry the rule |
| S4 Stale PASS | PASS, fixture-assisted | none | — | spec §3/§4: Task 8 (verification: final-run-only freshness) and Task 9 (handoff) must still carry the rule |
| S5 Missing evidence | FAIL (flipped on re-grade) | "This exercise forbids writing under `H:\`, so here the brief is this file." | omitted element (no durable decision log) | Task 9 (orchestrator: `decisions.md` written at decision time, spec §7). Task 7 for build-time constants; Task 6 for labels |
| S6 Project boundary | FAIL | "save it **only after you've saved or discarded Main**." / "The only user decision needed is whether to save Main first." | discipline violation; missing conditional | Task 7 (build): never save, replace or discard the dirty scene; how to create one without touching it. Task 9: record dirty state at intake, no mid-run questions |
| S7 Missing tools | FAIL (v2 rerun) | "Windows paths are case-insensitive, so this is the same directory as the `tools` the task says is absent." / "Take the newest non-prerelease release on `.../releases/latest`" | missing conditional | Task 3 (`ensure_tools.py`) + Task 9 (orchestrator) |
| S8 Resume | FAIL | "I do not want a visuals phase that rests on missing evidence." | wrong-shaped output; omitted element | Task 9 (orchestrator): read `progress.json`, re-hash inputs, refuse on mismatch, resume at `next_phase`, append to `decisions.md` |

## Guidance by task

- **Task 3** (`ensure_tools.py`): counters S7. The pinned manifest, the per-tool detection and the root resolution order are structure, not prose.
- **Task 6** (evidence): S1 (rerun conditional, source-hash precheck) and S2 (label table required in the mechanic-entry template). It also carries the spec §3 / §5 phase 5 rule that a recovered-by-dummy shader is recorded as "reconstructed" (S3 passed only with fixture help).
- **Task 7** (build): S6 (dirty scene, project boundary) plus the spec §3 shader-honesty rule at the point where the shader is built (S3).
- **Task 8** (verification): no scenario failed at baseline, but S4 passed only with fixture help. Spec §4 requires that only the last run on the final code and assets counts, and §3 forbids reporting a PASS from an earlier run or an empty directory. These must appear in the skill as written there.
- **Task 9** (orchestrator): S5 (`decisions.md` written at decision time), S7 (with Task 3), S8, and the shared parts of S1 and S6.

Fixture contamination to remember at Task 10: S2, S3 and S5 were helped by artifacts that exist only in this fixture (`chain-barrier-rules.md`, `AGENTS.md`, `LoopCarMotion.cs`). S1, S4, S6 and S8 leaned on `parkingloop-recreate-mechanics` and `verification-before-completion`. A GREEN pass on S3 and S4 is only informative if those fixture aids are less available.
