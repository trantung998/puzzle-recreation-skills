import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from unittest import mock
from datetime import datetime, timedelta, timezone

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "check_evidence.py")


def load_module():
    spec = importlib.util.spec_from_file_location("check_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ALL_DIMENSIONS = ["since", "expect-levels", "require-checks", "require-images", "per-level-images", "sources", "sources-manifest", "model"]


def png_1x1():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixel = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixel) + chunk(b"IEND", b"")


def report_lines(count, status="PASS"):
    return "".join("level-%d\t%s\tloaded\n" % (i, status) for i in range(1, count + 1))


class CheckEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="check_evidence_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.receipt = os.path.join(self.root, "pointer.txt")
        self.evidence = os.path.join(self.root, "evidence")

    def write(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(data, bytes) else "w"
        kwargs = {} if isinstance(data, bytes) else {"encoding": "utf-8", "newline": ""}
        with open(path, mode, **kwargs) as handle:
            handle.write(data)

    def make_run(self, status="PASS", report=None, png=True):
        os.makedirs(self.evidence, exist_ok=True)
        self.write(self.receipt, "%s\n%s\n" % (status, self.evidence))
        if report is not None:
            self.write(os.path.join(self.evidence, "report.txt"), report)
        if png:
            self.write(os.path.join(self.evidence, "level-1-portrait.png"), png_1x1())

    def run_check(self, *extra):
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--receipt", self.receipt, *extra],
            capture_output=True, text=True, timeout=60)
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            self.fail("not JSON: stdout=%r stderr=%r" % (proc.stdout, proc.stderr))
        self.assertEqual(sorted(result), ["problems", "skipped", "status"])
        self.assertEqual(proc.returncode, 0 if result["status"] == "PASS" else 1)
        return result

    def assertFailsWith(self, result, fragment):
        self.assertEqual(result["status"], "FAIL", result)
        self.assertTrue(any(fragment in p for p in result["problems"]), result["problems"])

    def test_missing_receipt_fails(self):
        self.assertFailsWith(self.run_check(), "receipt")

    def test_empty_receipt_fails(self):
        self.write(self.receipt, "")
        self.assertFailsWith(self.run_check(), "empty")

    def test_aborted_fails(self):
        self.make_run(status="ABORTED", report=report_lines(3))
        self.assertFailsWith(self.run_check(), "ABORTED")

    def test_pass_with_empty_dir_fails(self):
        os.makedirs(self.evidence)
        self.write(self.receipt, "PASS\n%s\n" % self.evidence)
        result = self.run_check()
        self.assertFailsWith(result, "empty")
        self.assertFailsWith(result, "report.txt")

    def test_report_line_fail_fails(self):
        report = report_lines(3) + "tap-gameplay\tFAIL\tno tap registered\n"
        self.make_run(report=report)
        self.assertFailsWith(self.run_check(), "tap-gameplay")

    def test_unknown_status_in_report_fails(self):
        self.make_run(report="level-1\tPASSED\tok\n")
        self.assertFailsWith(self.run_check(), "level-1")

    def test_bad_png_signature_fails(self):
        self.make_run(report=report_lines(3))
        self.write(os.path.join(self.evidence, "level-1-portrait.png"), b"GIF89a-not-a-png" * 4)
        self.assertFailsWith(self.run_check("--require-images", "*.png"), "signature")

    def test_zero_size_png_fails(self):
        self.make_run(report=report_lines(3))
        self.write(os.path.join(self.evidence, "level-1-portrait.png"), b"")
        self.assertFailsWith(self.run_check("--require-images", "*.png"), "zero size")

    def test_required_image_glob_without_match_fails(self):
        self.make_run(report=report_lines(3), png=False)
        self.write(os.path.join(self.evidence, "note.txt"), "x")
        self.assertFailsWith(self.run_check("--require-images", "*landscape*.png"), "no file matches")

    def test_stale_artifact_fails(self):
        self.make_run(report=report_lines(3))
        old = time.time() - 7200
        os.utime(os.path.join(self.evidence, "level-1-portrait.png"), (old, old))
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.assertFailsWith(self.run_check("--since", since), "older than")

    def test_stale_receipt_fails(self):
        self.make_run(report=report_lines(3))
        old = time.time() - 7200
        os.utime(self.receipt, (old, old))
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.assertFailsWith(self.run_check("--since", since), "older than")

    def test_since_accepts_z_suffix_and_naive_time(self):
        self.make_run(report=report_lines(3))
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        self.assertEqual(self.run_check("--since", past.strftime("%Y-%m-%dT%H:%M:%SZ"))["status"], "PASS")
        naive_local = datetime.now() - timedelta(hours=1)
        self.assertEqual(self.run_check("--since", naive_local.isoformat())["status"], "PASS")

    def test_invalid_since_fails(self):
        self.make_run(report=report_lines(3))
        self.assertFailsWith(self.run_check("--since", "yesterday-ish"), "--since")

    def test_too_few_levels_fails(self):
        self.make_run(report=report_lines(2))
        self.assertFailsWith(self.run_check("--expect-levels", "3"), "fewer than 3")

    def test_duplicate_level_ids_do_not_count_twice(self):
        self.make_run(report="level-1\tPASS\ta\nlevel-1\tPASS\tb\nlevel-2\tPASS\tc\n")
        self.assertFailsWith(self.run_check("--expect-levels", "3"), "fewer than 3")

    def test_level_id_gap_fails(self):
        self.make_run(report="level-1\tPASS\ta\nlevel-2\tPASS\tb\nlevel-5\tPASS\tc\n")
        self.assertFailsWith(self.run_check("--expect-levels", "3"), "level-3")

    def test_complete_pass(self):
        self.make_run(report=report_lines(3))
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = self.run_check("--require-images", "*.png", "--since", since, "--expect-levels", "3")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["problems"], [])

    def test_relative_evidence_dir_resolves_next_to_receipt(self):
        self.make_run(report=report_lines(3))
        self.write(self.receipt, "PASS\nevidence\n")
        self.assertEqual(self.run_check("--expect-levels", "3")["status"], "PASS")

    # ---- helpers for the fix-round tests ---------------------------------------------------------------

    def run_raw(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, timeout=60)

    def make_level_images(self, orientation, numbers):
        for n in numbers:
            self.write(os.path.join(self.evidence, "level-%d-%s-582x1280.png" % (n, orientation)), png_1x1())

    def make_model(self, lines=None):
        self.model = os.path.join(self.root, "model.txt")
        if lines is None:
            lines = ("levels-count\tPASS\tok\nlevel-1-data\tPASS\tok\nlevel-2-data\tPASS\tok\nlevel-3-data\tPASS\tok\n"
                     "ice.claim1.reject\tPASS\tok\ncoverage.ice.accept\tPASS\tok\n")
        self.write(self.model, lines)

    def make_sources(self):
        self.src = os.path.join(self.root, "src")
        self.write(os.path.join(self.src, "a.cs"), "class A {}")
        self.write(os.path.join(self.src, "sub", "b.cs"), "class B {}")
        self.manifest = os.path.join(self.root, "sources.sha256")

    def write_manifest(self):
        proc = self.run_raw("--write-sources-manifest", self.manifest, "--sources", self.src)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    # ---- --strict, --require-checks, skipped ----------------------------------------------------------------

    def test_strict_requires_flags(self):
        self.make_run(report=report_lines(3))
        proc = self.run_raw("--receipt", self.receipt, "--strict")
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("--strict", proc.stderr)
        self.make_model()
        proc = self.run_raw("--receipt", self.receipt, "--strict", "--since", "2000-01-01T00:00:00Z",
                            "--expect-levels", "3", "--require-checks", "level-*")
        self.assertEqual(proc.returncode, 2)  # --model is still missing
        self.assertIn("--model", proc.stderr)

    def test_strict_with_everything_passes(self):
        self.make_run(report=report_lines(3))
        self.make_model()
        result = self.run_check("--strict", "--since", "2000-01-01T00:00:00Z", "--expect-levels", "3",
                                "--require-checks", "level-*", "--model", self.model)
        self.assertEqual(result["status"], "PASS", result)

    def test_require_checks_missing_fails(self):
        self.make_run(report=report_lines(3))
        self.assertFailsWith(self.run_check("--require-checks", "sample-win"), "sample-win")

    def test_require_checks_needs_a_pass_line(self):
        self.make_run(report=report_lines(3) + "sample-win\tFAIL\tno win\n")
        result = self.run_check("--require-checks", "sample-win")
        self.assertFailsWith(result, "no PASS line matches required check 'sample-win'")

    def test_require_checks_glob_pass(self):
        report = report_lines(3) + "".join(
            "%s\tPASS\tok\n" % name for name in
            ("switch-next", "switch-previous", "mechanic-ice", "mechanic-key", "sample-win", "ui-blocks-gameplay", "console"))
        self.make_run(report=report)
        result = self.run_check("--require-checks", "switch-*", "mechanic-*", "sample-win", "ui-blocks-gameplay", "console")
        self.assertEqual(result["status"], "PASS", result)

    def test_skipped_reported(self):
        self.make_run(report=report_lines(3))
        self.assertEqual(self.run_check()["skipped"], ALL_DIMENSIONS)
        self.make_level_images("portrait", [1, 2, 3])
        self.make_model()
        self.make_sources()
        self.write_manifest()
        old = time.time() - 7200
        for base, _dirs, names in os.walk(self.src):
            for name in names:
                os.utime(os.path.join(base, name), (old, old))
        full = self.run_check("--since", "2000-01-01T00:00:00Z", "--expect-levels", "3", "--require-checks", "level-*",
                              "--require-images", "*.png", "--per-level-images", "level-{n}-portrait-*.png",
                              "--sources", self.src, "--sources-manifest", self.manifest, "--model", self.model)
        self.assertEqual(full["status"], "PASS", full)
        self.assertEqual(full["skipped"], [])
        partial = self.run_check("--expect-levels", "3")
        self.assertNotIn("expect-levels", partial["skipped"])
        self.assertIn("since", partial["skipped"])

    def test_documented_strict_command_passes_with_nothing_skipped(self):
        # The flags below are hard-coded copies of the judge command in SKILL.md Procedure step 5
        # (orientation "portrait"); keep both in step. The SKILL.md check guards against drift.
        report = report_lines(3) + "".join("%s\tPASS\tok\n" % name for name in (
            "switch-next", "switch-previous", "ui-blocks-gameplay", "mechanic-ice", "sample-win", "console"))
        self.make_run(report=report, png=False)
        self.make_level_images("portrait", [1, 2, 3])
        self.make_model()
        self.make_sources()
        self.write_manifest()
        old = time.time() - 7200
        for base, _dirs, names in os.walk(self.src):
            for name in names:
                os.utime(os.path.join(base, name), (old, old))
        cutoff = datetime.fromtimestamp(old).astimezone().isoformat()  # newest source mtime, at judge time
        documented = ["--strict", "--receipt", self.receipt, "--since", cutoff, "--expect-levels", "3",
                      "--require-checks", "level-*", "switch-*", "ui-blocks-gameplay", "mechanic-*", "sample-win",
                      "console", "--per-level-images", "level-{n}-portrait-*.png", "--model", self.model,
                      "--sources", self.src, "--sources-manifest", self.manifest]
        skill = os.path.join(os.path.dirname(SCRIPT), "..", "SKILL.md")
        with open(skill, encoding="utf-8") as handle:
            text = handle.read()
        for flag in ("--strict", "--receipt", "--since", "--expect-levels", "--require-checks", '"level-*"',
                     '"switch-*"', '"ui-blocks-gameplay"', '"mechanic-*"', '"sample-win"', '"console"',
                     '--per-level-images "level-{n}-<o>-*.png"', "--model", "--sources <paths>",
                     "--sources-manifest"):
            self.assertIn(flag, text, "SKILL.md step 5 no longer documents %s" % flag)
        proc = self.run_raw(*documented)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["skipped"], [])

    # ---- --per-level-images ---------------------------------------------------------------------------------

    def test_per_level_images_missing_one_fails(self):
        self.make_run(report=report_lines(3))
        self.make_level_images("portrait", [1, 2])
        result = self.run_check("--expect-levels", "3", "--per-level-images", "level-{n}-portrait-*.png")
        self.assertFailsWith(result, "level 3")

    def test_per_level_images_complete_pass(self):
        self.make_run(report=report_lines(3))
        self.make_level_images("portrait", [1, 2, 3])
        self.make_level_images("landscape", [1, 2, 3])
        result = self.run_check("--expect-levels", "3", "--per-level-images", "level-{n}-portrait-*.png",
                                "--per-level-images", "level-{n}-landscape-*.png")
        self.assertEqual(result["status"], "PASS", result)

    def test_per_level_images_invalid_png_fails(self):
        self.make_run(report=report_lines(2))
        self.make_level_images("portrait", [1])
        self.write(os.path.join(self.evidence, "level-2-portrait-582x1280.png"), b"not a png at all, sorry")
        result = self.run_check("--expect-levels", "2", "--per-level-images", "level-{n}-portrait-*.png")
        self.assertFailsWith(result, "level 2")

    def test_per_level_images_needs_placeholder_and_expect_levels(self):
        self.make_run(report=report_lines(3))
        self.assertEqual(self.run_raw("--receipt", self.receipt, "--expect-levels", "3",
                                      "--per-level-images", "level-*.png").returncode, 2)
        self.assertEqual(self.run_raw("--receipt", self.receipt, "--per-level-images", "level-{n}.png").returncode, 2)

    # ---- freshness of sources ---------------------------------------------------------------------------------

    def test_source_newer_than_receipt_fails(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        old = time.time() - 7200
        os.utime(self.receipt, (old, old))
        self.assertFailsWith(self.run_check("--sources", self.src), "newer than the receipt")

    def test_sources_older_than_receipt_pass(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        old = time.time() - 7200
        for base, _dirs, names in os.walk(self.src):
            for name in names:
                os.utime(os.path.join(base, name), (old, old))
        self.assertEqual(self.run_check("--sources", self.src)["status"], "PASS")

    def test_sources_manifest_match_pass(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        self.write_manifest()
        with open(self.manifest, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(len(lines), 2)
        digest = hashlib.sha256(b"class A {}").hexdigest()
        self.assertIn(digest + "\ta.cs", lines)
        self.assertIn(hashlib.sha256(b"class B {}").hexdigest() + "\tsub/b.cs", lines)
        old = time.time() - 7200
        for base, _dirs, names in os.walk(self.src):
            for name in names:
                os.utime(os.path.join(base, name), (old, old))
        result = self.run_check("--sources", self.src, "--sources-manifest", self.manifest)
        self.assertEqual(result["status"], "PASS", result)

    def test_sources_manifest_detects_deletion(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        self.write_manifest()
        os.remove(os.path.join(self.src, "sub", "b.cs"))
        result = self.run_check("--sources", self.src, "--sources-manifest", self.manifest)
        self.assertFailsWith(result, "removed")

    def test_sources_manifest_detects_change_and_addition(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        self.write_manifest()
        self.write(os.path.join(self.src, "a.cs"), "class A { int changed; }")
        self.write(os.path.join(self.src, "c.cs"), "class C {}")
        result = self.run_check("--sources", self.src, "--sources-manifest", self.manifest)
        self.assertFailsWith(result, "changed")
        self.assertFailsWith(result, "added")

    def test_sources_manifest_requires_sources(self):
        self.make_run(report=report_lines(3))
        self.make_sources()
        self.write_manifest()
        self.assertEqual(self.run_raw("--receipt", self.receipt, "--sources-manifest", self.manifest).returncode, 2)

    # ---- --model ---------------------------------------------------------------------------------------------

    def test_model_missing_fails(self):
        self.make_run(report=report_lines(3))
        self.assertFailsWith(self.run_check("--model", os.path.join(self.root, "model.txt")), "model")

    def test_model_fail_line_fails(self):
        self.make_run(report=report_lines(3))
        self.make_model("level-1-data\tPASS\tok\nice.claim1.reject\tFAIL\twrong ice\n")
        self.assertFailsWith(self.run_check("--model", self.model), "ice.claim1.reject")

    def test_model_without_contract_line_fails(self):
        self.make_run(report=report_lines(3))
        self.make_model("levels-count\tPASS\tok\nlevel-1-data\tPASS\tok\ncoverage.ice.accept\tPASS\tok\n")
        self.assertFailsWith(self.run_check("--model", self.model), "contract")

    def test_model_too_few_level_lines_fails(self):
        self.make_run(report=report_lines(3))
        self.make_model("level-1-data\tPASS\tok\nice.claim1.reject\tPASS\tok\n")
        result = self.run_check("--model", self.model, "--expect-levels", "3")
        self.assertFailsWith(result, "level-2-data")
        self.assertFailsWith(result, "level-3-data")

    def test_model_missing_one_level_data_fails(self):
        self.make_run(report=report_lines(3))
        self.make_model("level-1-data\tPASS\tok\nlevel-3-data\tPASS\tok\nice.claim1.reject\tPASS\tok\n"
                        "coverage.ice.accept\tPASS\tok\ncoverage.ice.reject\tPASS\tok\ncoverage.ice.boundary\tPASS\tok\n")
        result = self.run_check("--model", self.model, "--expect-levels", "3")
        self.assertFailsWith(result, "level-2-data")
        self.assertFalse(any("level-1-data" in p or "level-3-data" in p for p in result["problems"]), result["problems"])

    def test_model_pass(self):
        self.make_run(report=report_lines(3))
        self.make_model()
        result = self.run_check("--model", self.model, "--expect-levels", "3")
        self.assertEqual(result["status"], "PASS", result)

    def test_model_stale_fails_under_since(self):
        self.make_run(report=report_lines(3))
        self.make_model()
        old = time.time() - 7200
        os.utime(self.model, (old, old))
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.assertFailsWith(self.run_check("--model", self.model, "--since", since), "older than")

    # ---- usage and safety ----------------------------------------------------------------------------------------

    def test_expect_levels_below_one_is_usage_error(self):
        self.make_run(report=report_lines(3))
        for value in ("0", "-2"):
            proc = self.run_raw("--receipt", self.receipt, "--expect-levels", value)
            self.assertEqual(proc.returncode, 2, value)
            self.assertIn("--expect-levels", proc.stderr)

    def test_evidence_dir_outside_receipt_tree_fails(self):
        outside = tempfile.mkdtemp(prefix="check_evidence_outside_")
        self.addCleanup(shutil.rmtree, outside, True)
        self.write(os.path.join(outside, "report.txt"), report_lines(3))
        self.write(os.path.join(outside, "level-1.png"), png_1x1())
        self.write(self.receipt, "PASS\n%s\n" % outside)
        self.assertFailsWith(self.run_check(), "outside")

    def test_image_pattern_outside_receipt_tree_fails(self):
        self.make_run(report=report_lines(3))
        self.write(os.path.join(self.root, "stray.png"), png_1x1())
        self.assertFailsWith(self.run_check("--require-images", "../*.png"), "outside")

    def test_oserror_is_a_problem_not_a_traceback(self):
        self.make_run(report=report_lines(3))
        module = load_module()
        target = os.path.join(self.evidence, "level-1-portrait.png")
        real = os.path.getmtime

        def flaky(path):
            if os.path.abspath(path) == os.path.abspath(target):
                raise PermissionError("denied")
            return real(path)

        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with mock.patch("os.path.getmtime", side_effect=flaky):
            result = module.evaluate(["--receipt", self.receipt, "--since", since])
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("level-1-portrait.png" in p and "denied" in p for p in result["problems"]), result["problems"])

    def test_broken_symlink_under_since_is_a_problem(self):
        self.make_run(report=report_lines(3))
        link = os.path.join(self.evidence, "dangling.png")
        try:
            os.symlink(os.path.join(self.root, "no-such-target"), link)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("symlinks are not available here")
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.assertFailsWith(self.run_check("--since", since), "dangling.png")


if __name__ == "__main__":
    unittest.main()
