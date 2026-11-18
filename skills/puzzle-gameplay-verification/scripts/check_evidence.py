#!/usr/bin/env python3
"""Judge a verification run from its files, never from a launcher exit code.

Prints {"status": "PASS"|"FAIL", "problems": [...], "skipped": [...]} and exits 0 on PASS, 1 on FAIL,
2 on a usage error. "skipped" names every dimension that was not checked because its flag was absent
(--per-level-images also satisfies "require-images"); --strict makes the important ones mandatory.

The receipt: line 1 is PASS, FAIL or ABORTED; line 2 is the evidence directory (an absolute path, or one
relative to the receipt) that must lie inside the receipt's directory tree. The evidence directory holds
report.txt with one line per check: "<id><TAB><PASS|FAIL><TAB><detail>".

Run start:  --write-sources-manifest <file> --sources <path>...   (writes "<sha256><TAB><relpath>" lines)
Judging:    --receipt <path> [--strict] [--since T] [--expect-levels N] [--require-checks ID...]
            [--require-images GLOB...] [--per-level-images PATTERN_WITH_{n}]... [--model model.txt]
            [--sources PATH... [--sources-manifest FILE]]
"""
import argparse
import fnmatch
import glob
import hashlib
import json
import os
import re
import struct
import sys
from datetime import datetime, timezone

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LEVEL_ID = re.compile(r"^level-(\d+)$")
LEVEL_DATA_ID = re.compile(r"^level-(\d+)-data$")
CONTRACT_ID = re.compile(r"^(?!coverage\.).+\.claim[^.]*\.[^.]+$")  # <mechanic>.claim<k>.<case>
DIMENSIONS = ["since", "expect-levels", "require-checks", "require-images",
              "per-level-images", "sources", "sources-manifest", "model"]
STRICT_REQUIRED = [("since", "--since"), ("expect-levels", "--expect-levels"),
                   ("require-checks", "--require-checks"), ("model", "--model")]


class Usage(Exception):
    pass


def read_text(path):
    with open(path, encoding="utf-8-sig", errors="replace") as handle:
        return handle.read()


def parse_since(value):
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.astimezone()  # naive input means local time
    return moment.timestamp()


def inside(child, parent):
    child = os.path.normcase(os.path.realpath(child))
    parent = os.path.normcase(os.path.realpath(parent))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:  # different drives
        return False


def png_problem(path):
    try:
        size = os.path.getsize(path)
        if size == 0:
            return "zero size"
        with open(path, "rb") as handle:
            head = handle.read(33)
            handle.seek(max(0, size - 12))
            tail = handle.read(12)
    except OSError as exc:
        return "cannot read: %s" % exc
    if head[:8] != PNG_SIGNATURE:
        return "bad PNG signature"
    if len(head) < 33 or head[12:16] != b"IHDR":
        return "PNG header chunk missing or truncated"
    width, height = struct.unpack(">II", head[16:24])
    if width == 0 or height == 0:
        return "PNG has zero width or height"
    if tail[4:8] != b"IEND":
        return "PNG is truncated (no IEND chunk)"
    return None


def list_files(directory):
    found = []
    for base, _dirs, names in os.walk(directory):
        for name in names:
            found.append(os.path.join(base, name))
    return sorted(found)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_files(paths):
    """Returns (root, [files], problems). root is the common directory used for relative paths."""
    problems, files, anchors = [], [], []
    for raw in paths:
        path = os.path.abspath(raw)
        if os.path.isdir(path):
            anchors.append(path)
            files.extend(list_files(path))
        elif os.path.isfile(path) or os.path.islink(path):
            anchors.append(os.path.dirname(path))
            files.append(path)
        else:
            problems.append("source path does not exist: %s" % raw)
    if not anchors:
        return None, [], problems
    try:
        root = os.path.commonpath(anchors)
    except ValueError:
        raise Usage("--sources must share one root directory (different drives)")
    return root, sorted(set(files)), problems


def hash_sources(paths):
    """Returns ({relpath: sha256}, problems)."""
    root, files, problems = source_files(paths)
    table = {}
    for path in files:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            table[rel] = sha256_of(path)
        except OSError as exc:
            problems.append("cannot hash source %s: %s" % (rel, exc))
    return table, problems


def write_sources_manifest(args):
    table, problems = hash_sources(args.sources)
    if not table and not problems:
        problems.append("no files found under --sources")
    if not problems:
        with open(args.write_sources_manifest, "w", encoding="utf-8", newline="\n") as handle:
            for rel in sorted(table):
                handle.write("%s\t%s\n" % (table[rel], rel))
    return problems, {"files": len(table)}


def check_sources_manifest(args):
    problems = []
    try:
        recorded = {}
        for number, raw in enumerate(read_text(args.sources_manifest).splitlines(), 1):
            if not raw.strip():
                continue
            digest, sep, rel = raw.partition("\t")
            if not sep or not re.fullmatch(r"[0-9a-f]{64}", digest) or not rel:
                problems.append("sources manifest line %d is malformed: %r" % (number, raw))
                continue
            recorded[rel] = digest
    except OSError as exc:
        return ["sources manifest cannot be read: %s" % exc]
    current, hash_problems = hash_sources(args.sources)
    problems.extend(hash_problems)
    removed = sorted(set(recorded) - set(current))
    added = sorted(set(current) - set(recorded))
    changed = sorted(rel for rel in set(recorded) & set(current) if recorded[rel] != current[rel])
    for label, names in (("removed since run start", removed), ("added since run start", added),
                         ("changed since run start", changed)):
        if names:
            shown = ", ".join(names[:10]) + (" ... (+%d more)" % (len(names) - 10) if len(names) > 10 else "")
            problems.append("%d source file(s) %s: %s" % (len(names), label, shown))
    return problems


def check_sources_mtime(args, receipt):
    problems = []
    try:
        receipt_time = os.path.getmtime(receipt)
    except OSError as exc:
        return ["cannot read the receipt time: %s" % exc]
    _root, files, found = source_files(args.sources)
    problems.extend(found)
    for path in files:
        try:
            if os.path.getmtime(path) > receipt_time:
                problems.append("source newer than the receipt (edited after the run): %s" % path)
        except OSError as exc:
            problems.append("cannot stat source %s: %s" % (path, exc))
    return problems


def check_model(args):
    problems = []
    path = args.model
    if not os.path.isfile(path):
        return ["model file missing: %s" % path]
    try:
        text = read_text(path)
    except OSError as exc:
        return ["model file cannot be read: %s" % exc]
    contracts, level_ids = 0, set()
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split("\t")
        check_id = parts[0].strip()
        result = parts[1].strip() if len(parts) > 1 else ""
        if not check_id or result not in ("PASS", "FAIL"):
            problems.append("model line %d is malformed (want <id>\\t<PASS|FAIL>\\t<detail>): %r" % (number, raw))
            continue
        if result == "FAIL":
            problems.append("model check %s reported FAIL: %s" % (check_id, parts[2].strip() if len(parts) > 2 else ""))
            continue
        if LEVEL_DATA_ID.match(check_id):
            level_ids.add(check_id)
        elif CONTRACT_ID.match(check_id):
            contracts += 1
    if contracts == 0:
        problems.append("model.txt has no contract line (<mechanic>.claim<k>.<case>)")
    if args.expect_levels is not None:
        missing = ["level-%d-data" % n for n in range(1, args.expect_levels + 1)
                   if "level-%d-data" % n not in level_ids]
        if missing:
            problems.append("model.txt has no PASS line for %s" % ", ".join(missing))
    return problems


def evaluate_receipt(args, artifacts, seen_levels, passed_ids):
    """Reads the receipt and evidence directory. Returns problems; fills the three collections."""
    problems = []
    receipt = args.receipt
    if not os.path.isfile(receipt):
        return ["receipt missing: %s" % receipt]
    try:
        lines = read_text(receipt).splitlines()
    except OSError as exc:
        return ["receipt cannot be read: %s" % exc]
    if not any(line.strip() for line in lines):
        return ["receipt is empty: %s" % receipt]

    artifacts.append(receipt)
    status = lines[0].strip()
    if status != "PASS":
        problems.append("receipt status is %s, not PASS" % (status or "blank"))

    evidence_line = lines[1].strip() if len(lines) > 1 else ""
    if not evidence_line:
        problems.append("receipt line 2 (evidence directory) is missing")
        return problems
    receipt_dir = os.path.dirname(os.path.abspath(receipt))
    evidence = evidence_line if os.path.isabs(evidence_line) else os.path.join(receipt_dir, evidence_line)
    if not os.path.isdir(evidence):
        problems.append("evidence directory missing: %s" % evidence)
        return problems
    if not inside(evidence, receipt_dir):
        problems.append("evidence directory is outside the receipt's directory tree (%s): %s" % (receipt_dir, evidence))
        return problems
    args.evidence = evidence

    files = list_files(evidence)
    if not files:
        problems.append("evidence directory is empty: %s" % evidence)
    artifacts.extend(files)

    report_path = os.path.join(evidence, "report.txt")
    if not os.path.isfile(report_path):
        problems.append("report.txt missing in %s" % evidence)
    else:
        count = 0
        report = None
        try:
            report = read_text(report_path).splitlines()
        except OSError as exc:
            problems.append("report.txt cannot be read: %s" % exc)
        for number, raw in enumerate(report or [], 1):
            if not raw.strip():
                continue
            count += 1
            parts = raw.split("\t")
            check_id = parts[0].strip()
            result = parts[1].strip() if len(parts) > 1 else ""
            if not check_id or result not in ("PASS", "FAIL"):
                problems.append("report.txt line %d is malformed (want <id>\\t<PASS|FAIL>\\t<detail>): %r"
                                % (number, raw))
                continue
            if result == "FAIL":
                detail = parts[2].strip() if len(parts) > 2 else ""
                problems.append("check %s reported FAIL: %s" % (check_id, detail))
            else:
                passed_ids.add(check_id)
            match = LEVEL_ID.match(check_id)
            if match:
                seen_levels.add(int(match.group(1)))
        if report is not None and count == 0:
            problems.append("report.txt has no check lines")
    return problems


def match_images(args, pattern, problems):
    """Returns the valid PNG paths matching pattern, reporting bad and out-of-tree matches."""
    receipt_dir = os.path.dirname(os.path.abspath(args.receipt))
    if os.path.isabs(pattern) or ".." in re.split(r"[\\/]", pattern):
        problems.append("image pattern %r resolves outside the receipt's directory tree" % pattern)
        return []
    full = os.path.join(glob.escape(args.evidence), pattern)
    good = []
    for path in sorted(p for p in glob.glob(full, recursive=True) if os.path.isfile(p)):
        if not inside(path, receipt_dir):
            problems.append("%s is outside the receipt's directory tree" % path)
            continue
        reason = png_problem(path)
        if reason:
            problems.append("%s: %s" % (os.path.relpath(path, args.evidence), reason))
        else:
            good.append(path)
    return good


def check(args):
    problems = []
    artifacts, seen_levels, passed_ids = [], set(), set()
    args.evidence = None
    problems.extend(evaluate_receipt(args, artifacts, seen_levels, passed_ids))

    if args.require_checks:
        for pattern in args.require_checks:
            if not any(fnmatch.fnmatchcase(check_id, pattern) for check_id in passed_ids):
                problems.append("no PASS line matches required check %r in report.txt" % pattern)

    if args.evidence:
        for pattern in args.require_images or []:
            before = len(problems)
            matches = match_images(args, pattern, problems)
            if not matches and len(problems) == before:
                problems.append("no file matches required image pattern %r" % pattern)
            artifacts.extend(p for p in matches if p not in artifacts)
        for pattern in args.per_level_images or []:
            for n in range(1, (args.expect_levels or 0) + 1):
                matches = match_images(args, pattern.replace("{n}", str(n)), problems)
                if not matches:
                    problems.append("no valid PNG for level %d matches %r" % (n, pattern))
                artifacts.extend(p for p in matches if p not in artifacts)
    elif args.require_images or args.per_level_images:
        problems.append("images not checked: the evidence directory is unavailable")

    if args.model:
        problems.extend(check_model(args))
        if os.path.isfile(args.model):
            artifacts.append(args.model)

    if args.since:
        try:
            cutoff = parse_since(args.since)
        except ValueError:
            problems.append("--since is not an ISO 8601 time: %r" % args.since)
        else:
            for path in artifacts:
                try:
                    modified = os.path.getmtime(path)
                except OSError as exc:
                    problems.append("cannot stat artifact %s: %s" % (path, exc))
                    continue
                if modified < cutoff:
                    stamp = datetime.fromtimestamp(modified, timezone.utc).isoformat()
                    problems.append("artifact older than --since (%s): %s" % (stamp, path))

    if args.expect_levels is not None:
        wanted = args.expect_levels
        if len(seen_levels) < wanted:
            problems.append("fewer than %d distinct level-<i> checks in report.txt (found %d)"
                            % (wanted, len(seen_levels)))
        missing = [i for i in range(1, wanted + 1) if i not in seen_levels]
        if missing and len(seen_levels) >= wanted:
            problems.append("report.txt has no check for %s" % ", ".join("level-%d" % i for i in missing))

    if args.sources:
        problems.extend(check_sources_mtime(args, args.receipt))
        if args.sources_manifest:
            problems.extend(check_sources_manifest(args))
    return problems


def positive_int(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("%r is not an integer" % text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more, got %d" % value)
    return value


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--receipt", help="receipt file written by PointerSmoke.Start")
    parser.add_argument("--strict", action="store_true",
                        help="require --since, --expect-levels, --require-checks and --model")
    parser.add_argument("--require-images", nargs="+", metavar="GLOB",
                        help="PNG globs, relative to the evidence directory, that must match valid files")
    parser.add_argument("--per-level-images", action="append", metavar="PATTERN",
                        help="pattern containing {n}; every level 1..N needs a valid PNG (repeat per orientation)")
    parser.add_argument("--since", help="ISO 8601 time; every artifact must be modified at or after it")
    parser.add_argument("--expect-levels", type=positive_int, metavar="N",
                        help="report.txt needs distinct level-<i> checks for i = 1..N")
    parser.add_argument("--require-checks", nargs="+", metavar="ID_OR_GLOB",
                        help="fnmatch patterns; each must match at least one PASS line of report.txt")
    parser.add_argument("--model", metavar="FILE", help="model.txt from ModelContractRunner")
    parser.add_argument("--sources", nargs="+", metavar="PATH",
                        help="code and asset paths; none may be newer than the receipt")
    parser.add_argument("--sources-manifest", metavar="FILE",
                        help="manifest written at run start; added, removed or changed sources fail")
    parser.add_argument("--write-sources-manifest", metavar="FILE",
                        help="write the manifest for --sources and exit (run start)")
    return parser


def evaluate(argv):
    """Parses argv and returns the result dict. Raises SystemExit(2) on a usage error."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.write_sources_manifest:
            if not args.sources:
                parser.error("--write-sources-manifest needs --sources")
            problems, extra = write_sources_manifest(args)
            result = {"status": "FAIL" if problems else "PASS", "problems": problems, "skipped": []}
            result.update(extra)
            return result
        if not args.receipt:
            parser.error("--receipt is required")
        if args.strict:
            missing = [flag for dest, flag in STRICT_REQUIRED if not getattr(args, dest.replace("-", "_"))]
            if missing:
                parser.error("--strict also requires " + ", ".join(missing))
        for pattern in args.per_level_images or []:
            if "{n}" not in pattern:
                parser.error("--per-level-images pattern needs {n}: %r" % pattern)
        if args.per_level_images and args.expect_levels is None:
            parser.error("--per-level-images needs --expect-levels")
        if args.sources_manifest and not args.sources:
            parser.error("--sources-manifest needs --sources")
        skipped = [name for name in DIMENSIONS if not getattr(args, name.replace("-", "_"))
                   and not (name == "require-images" and args.per_level_images)]  # per-level PNGs are images
        problems = check(args)
    except Usage as exc:
        parser.error(str(exc))
    return {"status": "FAIL" if problems else "PASS", "problems": problems, "skipped": skipped}


def main(argv):
    result = evaluate(argv)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
