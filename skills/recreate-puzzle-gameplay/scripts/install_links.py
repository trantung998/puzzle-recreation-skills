#!/usr/bin/env python3
"""Link the five puzzle-recreation skills into other harnesses' skill folders.

Usage: python3 install_links.py [--harness claude|codex|all] [--dry-run]

Windows uses directory junctions (`_winapi.CreateJunction`, else `cmd /c mklink /J` with the
paths quoted; no admin rights); Unix uses symlinks.
An existing entry with the same name that is not a link to the canonical skill is never
replaced: it is reported as skipped-exists. Output is JSON, one entry per skill per harness
with status created | ok | skipped-exists | would-create | error. Exit code 1 if any error.
Codex scans ~/.agents/skills itself, so for it every skill reports ok and no link is made.
"""
import argparse
import json
import os
import subprocess
import sys

try:
    import _winapi  # CPython on Windows: CreateJunction needs no admin rights and no shell
except ImportError:
    _winapi = None

SKILLS = [
    "recreate-puzzle-gameplay",
    "puzzle-evidence-extraction",
    "puzzle-gameplay-build",
    "puzzle-gameplay-verification",
    "unity-apk-decompile",
]
HARNESSES = ["claude", "codex"]
REPARSE_POINT = 0x400


def default_canonical_root(home=None):
    return os.path.join(home or os.path.expanduser("~"), ".agents", "skills")


def default_harness_dirs(home=None):
    home = home or os.path.expanduser("~")
    return {
        "claude": os.path.join(home, ".claude", "skills"),
        "codex": os.path.join(home, ".agents", "skills"),
    }


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def is_link(path):
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:
        return isjunction(path)
    try:
        return bool(os.lstat(path).st_file_attributes & REPARSE_POINT)
    except (AttributeError, OSError):
        return False


def points_to(path, target):
    return is_link(path) and os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(target))


def mklink_junction(link, target):
    # Paths travel in environment variables inside double quotes: cmd expands %VAR% once and
    # does not re-expand the value, and the quotes keep & and ^ literal.
    env = dict(os.environ, INSTALL_LINKS_LINK=link, INSTALL_LINKS_TARGET=target)
    p = subprocess.run('cmd /d /c mklink /J "%INSTALL_LINKS_LINK%" "%INSTALL_LINKS_TARGET%"',
                       env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise OSError((p.stderr or p.stdout).strip() or "mklink failed")


def create_link(link, target):
    if os.name == "nt":
        junction = getattr(_winapi, "CreateJunction", None)
        if junction is not None:
            junction(target, link)
        else:
            mklink_junction(link, target)
    else:
        os.symlink(target, link, target_is_directory=True)


def plan_entry(harness, skill, link_root, canonical_root, dry_run, link_fn):
    link = os.path.join(link_root, skill)
    target = os.path.join(canonical_root, skill)
    entry = {"harness": harness, "skill": skill, "link": link, "target": target}
    if not os.path.isdir(target):
        entry.update(status="error", detail="canonical skill directory not found")
        return entry
    if _norm(link) == _norm(target):
        entry.update(status="ok", detail="harness scans the canonical folder; no link needed")
        return entry
    if os.path.lexists(link):
        if points_to(link, target):
            entry["status"] = "ok"
        else:
            kind = "link to another target" if is_link(link) else "existing directory or file, not replaced"
            entry.update(status="skipped-exists", detail=kind)
        return entry
    if dry_run:
        entry["status"] = "would-create"
        return entry
    try:
        os.makedirs(link_root, exist_ok=True)
        link_fn(link, target)
        entry["status"] = "created"
    except OSError as exc:
        entry.update(status="error", detail=str(exc))
    return entry


def main(argv=None, harness_dirs=None, canonical_root=None, link_fn=None, out=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness", choices=HARNESSES + ["all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    harness_dirs = harness_dirs or default_harness_dirs()
    canonical_root = canonical_root or default_canonical_root()
    link_fn = link_fn or create_link
    out = out or sys.stdout
    selected = HARNESSES if args.harness == "all" else [args.harness]
    entries = [
        plan_entry(h, s, harness_dirs[h], canonical_root, args.dry_run, link_fn)
        for h in selected
        for s in SKILLS
    ]
    out.write(json.dumps(entries, indent=2) + "\n")
    return 1 if any(e["status"] == "error" for e in entries) else 0


if __name__ == "__main__":
    sys.exit(main())
