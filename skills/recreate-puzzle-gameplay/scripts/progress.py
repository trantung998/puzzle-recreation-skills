#!/usr/bin/env python3
"""Work directory, progress and resume for puzzle-gameplay recreation.

Subcommands: init, resume, complete, reset (--from <phase>: that phase and every later
phase back to pending), status.
Exit codes: 0 ok, 2 refused (inputs changed) or reset with an unknown phase, 1 error.
Output is JSON on stdout.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile

PHASES = ["intake", "decompile", "level-catalog", "mechanics", "visuals", "build", "verify", "game-notes", "handoff"]
SUBDIRS = ["decompile", os.path.join("evidence", "levels"), os.path.join("evidence", "native"), "checks"]
SUFFIX_RE = re.compile(r"(_\d+_APKPure|_APKPure|-\d+(\.\d+)*)$", re.IGNORECASE)


def emit(obj, code=0):
    print(json.dumps(obj))
    return code


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug_from_apk(apk):
    stem = os.path.splitext(os.path.basename(apk))[0]
    prev = None
    while prev != stem:
        prev = stem
        stem = SUFFIX_RE.sub("", stem)
    words = [w for w in re.split(r"[^A-Za-z0-9]+", stem) if w]
    return "".join(w[0].upper() + w[1:] for w in words) or "Game"


def progress_path(workdir):
    return os.path.join(workdir, "progress.json")


def load(workdir):
    with open(progress_path(workdir), encoding="utf-8") as f:
        return json.load(f)


def save(workdir, data):
    fd, tmp = tempfile.mkstemp(dir=workdir, prefix=".progress-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, progress_path(workdir))
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def next_phase(data):
    for name in PHASES:
        if data["phases"].get(name, {}).get("status") != "done":
            return name
    return None


def norm_path(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def empty_phase():
    return {"status": "pending", "completed_at": None, "note": None, "artifacts": {}}


def do_resume(workdir, apk, levels, project=None):
    data = load(workdir)
    if not os.path.isfile(apk):
        return emit({"error": "apk not found: " + apk}, 1)
    if sha256_file(apk) != data["inputs"]["apk_sha256"]:
        return emit({"refused": "apk_sha256", "message": "APK bytes differ from the recorded SHA-256; use a new work directory."}, 2)
    if levels != data["inputs"]["levels"]:
        return emit({"refused": "levels", "message": "Level count %d differs from recorded %d; use a new work directory." % (levels, data["inputs"]["levels"])}, 2)
    if project is not None and norm_path(project) != norm_path(data["inputs"]["project"]):
        return emit({"refused": "project", "message": "Project %s differs from recorded %s; use a new work directory." % (project, data["inputs"]["project"])}, 2)
    return emit({"workdir": workdir, "slug": data["slug"], "next_phase": next_phase(data)})


def cmd_init(a):
    apk = os.path.abspath(a.apk)
    if not os.path.isfile(apk):
        return emit({"error": "apk not found: " + apk}, 1)
    slug = slug_from_apk(apk)
    workdir = os.path.abspath(a.workdir) if a.workdir else os.path.join(os.path.dirname(apk), slug + "-recreation")
    if os.path.isfile(progress_path(workdir)):
        return do_resume(workdir, apk, a.levels, a.project)
    for d in SUBDIRS:
        os.makedirs(os.path.join(workdir, d), exist_ok=True)
    decisions = os.path.join(workdir, "decisions.md")
    if not os.path.exists(decisions):
        open(decisions, "w", encoding="utf-8").close()
    data = {
        "schema": 1,
        "inputs": {
            "apk": apk,
            "apk_sha256": sha256_file(apk),
            "levels": a.levels,
            "project": os.path.normpath(os.path.abspath(a.project)),
            "references": list(a.references or []),
        },
        "slug": slug,
        "tools": {},
        "phases": {p: empty_phase() for p in PHASES},
    }
    save(workdir, data)
    return emit({"workdir": workdir, "slug": slug, "next_phase": next_phase(data)})


def cmd_resume(a):
    workdir = os.path.abspath(a.workdir)
    if not os.path.isfile(progress_path(workdir)):
        return emit({"error": "no progress.json in " + workdir}, 1)
    return do_resume(workdir, os.path.abspath(a.apk), a.levels, a.project)


def cmd_reset(a):
    workdir = os.path.abspath(a.workdir)
    if a.from_phase not in PHASES:
        return emit({"error": "unknown phase: " + a.from_phase, "phases": PHASES}, 2)
    if not os.path.isfile(progress_path(workdir)):
        return emit({"error": "no progress.json in " + workdir}, 1)
    data = load(workdir)
    reset = PHASES[PHASES.index(a.from_phase):]
    for p in reset:
        data["phases"][p] = empty_phase()
    save(workdir, data)
    return emit({"reset": reset, "next_phase": next_phase(data)})


def cmd_complete(a):
    workdir = os.path.abspath(a.workdir)
    if a.phase not in PHASES:
        return emit({"error": "unknown phase: " + a.phase, "phases": PHASES}, 1)
    if not os.path.isfile(progress_path(workdir)):
        return emit({"error": "no progress.json in " + workdir}, 1)
    arts = {}
    for p in a.artifact or []:
        if not os.path.isfile(p):
            return emit({"error": "artifact not found: " + p}, 1)
        arts[os.path.abspath(p)] = sha256_file(p)
    data = load(workdir)
    data["phases"][a.phase] = {
        "status": "done",
        "completed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": a.note,
        "artifacts": arts,
    }
    save(workdir, data)
    return emit({"phase": a.phase, "next_phase": next_phase(data)})


def cmd_status(a):
    workdir = os.path.abspath(a.workdir)
    if not os.path.isfile(progress_path(workdir)):
        return emit({"error": "no progress.json in " + workdir}, 1)
    data = load(workdir)
    return emit({
        "workdir": workdir,
        "slug": data["slug"],
        "inputs": data["inputs"],
        "phases": {k: v["status"] for k, v in data["phases"].items()},
        "next_phase": next_phase(data),
    })


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--apk", required=True)
    p.add_argument("--levels", type=int, required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--workdir")
    p.add_argument("--references", nargs="*")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("resume")
    p.add_argument("--workdir", required=True)
    p.add_argument("--apk", required=True)
    p.add_argument("--levels", type=int, required=True)
    p.add_argument("--project")
    p.set_defaults(fn=cmd_resume)
    p = sub.add_parser("reset")
    p.add_argument("--workdir", required=True)
    p.add_argument("--from", dest="from_phase", required=True)
    p.set_defaults(fn=cmd_reset)
    p = sub.add_parser("complete")
    p.add_argument("--workdir", required=True)
    p.add_argument("--phase", required=True)
    p.add_argument("--note")
    p.add_argument("--artifact", nargs="*")
    p.set_defaults(fn=cmd_complete)
    p = sub.add_parser("status")
    p.add_argument("--workdir", required=True)
    p.set_defaults(fn=cmd_status)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Exception as e:  # report, don't crash with a traceback
        return emit({"error": "%s: %s" % (type(e).__name__, e)}, 1)


if __name__ == "__main__":
    sys.exit(main())
