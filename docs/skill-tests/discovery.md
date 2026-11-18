# Cross-harness discovery check

Date: 2026-11-18. Windows, PowerShell. Codex CLI 0.167.0, Claude Code 2.1.325.
Skills under test (canonical `C:\Users\melod\.agents\skills\`): `recreate-puzzle-gameplay`,
`puzzle-evidence-extraction`, `puzzle-gameplay-build`, `puzzle-gameplay-verification`,
`unity-apk-decompile`. Live prompts ran in `C:\Users\melod\AppData\Local\Temp\opencode\task11\`.

## 1. OpenCode

```text
opencode api get "/api/skill?location%5Bdirectory%5D=C%3A%5CUsers%5Cmelod"
```

76 skills listed; the five under test:

```text
puzzle-evidence-extraction     C:\Users\melod\.agents\skills\puzzle-evidence-extraction\SKILL.md
puzzle-gameplay-build          C:\Users\melod\.agents\skills\puzzle-gameplay-build\SKILL.md
puzzle-gameplay-verification   C:\Users\melod\.agents\skills\puzzle-gameplay-verification\SKILL.md
recreate-puzzle-gameplay       C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\SKILL.md
unity-apk-decompile            C:\Users\melod\.agents\skills\unity-apk-decompile\SKILL.md
```

Also listed from `~/.claude/skills`: `reverse-engineer-anything`, `task-routing` and
`synced\...` entries, so OpenCode scans `~/.claude/skills` as well as `~/.agents/skills`.

Re-run after the Claude links were created (section 3): still 76 entries, no duplicate IDs,
the five paths still point under `.agents\skills\`.

From `H:\UGame\ParkingLoop`: `unity-apk-decompile` resolves to
`H:\UGame\ParkingLoop\.agents\skills\unity-apk-decompile\SKILL.md` (project copy wins).

Result: PASS.

## 2. Codex

Documentation (https://developers.openai.com/codex/build-skills, fetched 2026-11-18),
"Where Codex loads local skills":

- `USER`: `$HOME/.agents/skills`
- `REPO`: `.agents/skills` in the launch directory, each parent, and the repository root
- `ADMIN`: `/etc/codex/skills`; `SYSTEM`: bundled
- "Codex supports symlinked skill folders and follows the symlink target when scanning these
  locations." Same-name skills are not merged. Explicit use: `/skills` or `$name`.

`codex --help` (0.167.0) shows no skills-directory option; it does list `exec`, `plugin` and
`agents` commands. `~/.codex/skills` contains only `.system`.

Decision: `~/.agents/skills` is scanned, so no Codex links were created.
`install_links.py --harness codex` reports `ok` for all five (no link needed).

Live check, one prompt:

```text
codex exec --skip-git-repo-check --ephemeral -s read-only \
  "List the names of all skills available to you. Do not run tools or modify files."
```

Exit 0. The list (54 names) included all five: `puzzle-evidence-extraction`,
`puzzle-gameplay-build`, `puzzle-gameplay-verification`, `recreate-puzzle-gameplay`,
`unity-apk-decompile`, plus `parkingloop-recreate-mechanics`, `orca-cli`, other
`~/.agents/skills` entries, and Codex's own (`imagegen`, `skill-creator`, ...). It did not list
`reverse-engineer-anything` or `task-routing`, which exist only under `~/.claude/skills`, so
Codex does not read `~/.claude/skills`.

Result: PASS (no links needed).

## 3. Claude Code

Documentation (https://code.claude.com/docs/en/skills.md): personal skills in
`~/.claude/skills/<name>/SKILL.md`, project skills in `.claude/skills/` up to the repository
root; a `<name>` entry "can be a symlink to a directory elsewhere on disk"; same-name
precedence enterprise > personal > project. `~/.agents/skills` is not a documented location.

`~/.claude/skills` had 40 entries before (two were already junctions: `orca-cli`,
`orchestration`).

```text
python scripts/install_links.py --harness claude --dry-run
-> 5 x would-create (exit 0, nothing changed)
python scripts/install_links.py --harness claude
-> 5 x created
python scripts/install_links.py --harness claude        (second run)
-> 5 x ok
```

After: 45 entries; the only additions are the five junctions, each targeting
`C:\Users\melod\.agents\skills\<skill-id>`. No existing entry was changed.

Live check, one prompt (the first invocation, `--tools ""` before the prompt, failed
immediately with "Input must be provided either through stdin or as a prompt argument";
no model call was made, so it was re-issued once with the prompt first):

```text
claude -p "List the names of all skills available to you. Do not use tools." --no-session-persistence
```

Exit 0, 100 skills listed, including all five (`puzzle-evidence-extraction`,
`puzzle-gameplay-build`, `puzzle-gameplay-verification`, `recreate-puzzle-gameplay`,
`unity-apk-decompile`). `parkingloop-recreate-mechanics`, which exists only under
`~/.agents/skills`, was not listed, so Claude Code does not read `~/.agents/skills` and the
links are required.

Result: PASS.

## 4. Other documentation read for `compatibility.md`

- Codex subagents (https://developers.openai.com/codex/subagents.md): enabled by default in
  current releases; spawned on a direct request or when `AGENTS.md`/skill instructions ask;
  `/subagents` in the CLI; subagents inherit sandbox and approvals. No background-wait
  mechanism described.
- Claude Code subagents (https://code.claude.com/docs/en/sub-agents.md): built-in Agent tool;
  subagents started from the main conversation run in the background by default; the
  Monitor tool is available to background subagents.
- Not run on this machine: Codex `$skill` / `/skills` selection, Claude Code `/skill-name`,
  any sub-agent or background-wait behaviour of either harness, symlink following in Codex,
  parent-directory discovery in Codex and Claude Code.

## 5. Script tests

```text
python -m unittest discover -s C:\Users\melod\.agents\skills\recreate-puzzle-gameplay\tests -v
Ran 63 tests ... OK      (47 existing + 16 for install_links.py)
```
