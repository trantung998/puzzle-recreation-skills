import importlib.util
import io
import json
import os
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "install_links.py")
spec = importlib.util.spec_from_file_location("install_links", SCRIPT)
il = importlib.util.module_from_spec(spec)
spec.loader.exec_module(il)

SKILLS = [
    "recreate-puzzle-gameplay",
    "puzzle-evidence-extraction",
    "puzzle-gameplay-build",
    "puzzle-gameplay-verification",
    "unity-apk-decompile",
]


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.canonical = os.path.join(self.tmp, "agents", "skills")
        for s in SKILLS:
            os.makedirs(os.path.join(self.canonical, s))
        self.claude = os.path.join(self.tmp, "claude", "skills")
        self.codex = self.canonical  # Codex scans the canonical folder itself
        self.dirs = {"claude": self.claude, "codex": self.codex}
        self.calls = []

    def fake_link(self, link, target):
        self.calls.append((link, target))
        os.makedirs(link)  # stand-in; the real link functions are tested separately

    def run_main(self, argv, link_fn=None, dirs=None):
        out = io.StringIO()
        code = il.main(
            argv,
            harness_dirs=dirs or self.dirs,
            canonical_root=self.canonical,
            link_fn=link_fn or self.fake_link,
            out=out,
        )
        return code, json.loads(out.getvalue())

    def by(self, entries, harness, skill):
        (e,) = [x for x in entries if x["harness"] == harness and x["skill"] == skill]
        return e


class DryRunTests(Base):
    def test_dry_run_reports_would_create_and_changes_nothing(self):
        code, entries = self.run_main(["--harness", "claude", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(len(entries), 5)
        self.assertTrue(all(e["status"] == "would-create" for e in entries))
        self.assertEqual(self.calls, [])
        self.assertFalse(os.path.exists(self.claude))

    def test_dry_run_still_reports_existing_directory_as_skipped(self):
        os.makedirs(os.path.join(self.claude, "puzzle-gameplay-build"))
        code, entries = self.run_main(["--harness", "claude", "--dry-run"])
        self.assertEqual(self.by(entries, "claude", "puzzle-gameplay-build")["status"], "skipped-exists")
        self.assertEqual(self.by(entries, "claude", "unity-apk-decompile")["status"], "would-create")
        self.assertEqual(self.calls, [])


class CreateTests(Base):
    def test_creates_one_link_per_skill_and_makes_parent(self):
        code, entries = self.run_main(["--harness", "claude"])
        self.assertEqual(code, 0)
        self.assertEqual({e["skill"] for e in entries}, set(SKILLS))
        self.assertTrue(all(e["status"] == "created" for e in entries))
        self.assertEqual(len(self.calls), 5)
        link, target = [c for c in self.calls if c[0].endswith("unity-apk-decompile")][0]
        self.assertEqual(os.path.normcase(link), os.path.normcase(os.path.join(self.claude, "unity-apk-decompile")))
        self.assertEqual(os.path.normcase(target), os.path.normcase(os.path.join(self.canonical, "unity-apk-decompile")))

    def test_other_entries_in_harness_dir_are_untouched(self):
        other = os.path.join(self.claude, "task-routing")
        os.makedirs(other)
        with open(os.path.join(other, "SKILL.md"), "w") as f:
            f.write("keep")
        self.run_main(["--harness", "claude"])
        with open(os.path.join(other, "SKILL.md")) as f:
            self.assertEqual(f.read(), "keep")

    def test_missing_canonical_skill_is_an_error(self):
        os.rmdir(os.path.join(self.canonical, "puzzle-gameplay-build"))
        code, entries = self.run_main(["--harness", "claude"])
        self.assertEqual(code, 1)
        self.assertEqual(self.by(entries, "claude", "puzzle-gameplay-build")["status"], "error")
        self.assertEqual(self.by(entries, "claude", "unity-apk-decompile")["status"], "created")

    def test_link_function_failure_is_reported_not_raised(self):
        def boom(link, target):
            raise OSError("no")

        code, entries = self.run_main(["--harness", "claude"], link_fn=boom)
        self.assertEqual(code, 1)
        self.assertTrue(all(e["status"] == "error" for e in entries))
        self.assertIn("no", entries[0]["detail"])


class ExistingTests(Base):
    def test_second_run_is_ok_when_already_linked(self):
        # real links in the temp tree
        code, first = self.run_main(["--harness", "claude"], link_fn=il.create_link)
        if any(e["status"] == "error" for e in first):
            self.skipTest("cannot create links here: %s" % first[0].get("detail"))
        self.assertTrue(all(e["status"] == "created" for e in first))
        for s in SKILLS:
            self.assertTrue(os.path.isdir(os.path.join(self.claude, s)))
        code, second = self.run_main(["--harness", "claude"], link_fn=il.create_link)
        self.assertEqual(code, 0)
        self.assertTrue(all(e["status"] == "ok" for e in second))

    def test_real_directory_with_same_name_is_skipped_and_kept(self):
        existing = os.path.join(self.claude, "puzzle-evidence-extraction")
        os.makedirs(existing)
        with open(os.path.join(existing, "mine.txt"), "w") as f:
            f.write("x")
        code, entries = self.run_main(["--harness", "claude"])
        self.assertEqual(code, 0)
        e = self.by(entries, "claude", "puzzle-evidence-extraction")
        self.assertEqual(e["status"], "skipped-exists")
        self.assertTrue(os.path.isfile(os.path.join(existing, "mine.txt")))
        self.assertEqual(len(self.calls), 4)

    def test_link_to_a_different_target_is_skipped(self):
        elsewhere = os.path.join(self.tmp, "elsewhere")
        os.makedirs(elsewhere)
        os.makedirs(self.claude)
        link = os.path.join(self.claude, "puzzle-gameplay-build")
        try:
            il.create_link(link, elsewhere)
        except OSError:
            self.skipTest("cannot create links here")
        code, entries = self.run_main(["--harness", "claude"])
        self.assertEqual(self.by(entries, "claude", "puzzle-gameplay-build")["status"], "skipped-exists")
        self.assertTrue(os.path.isdir(elsewhere))


class HarnessSelectionTests(Base):
    def test_claude_only(self):
        code, entries = self.run_main(["--harness", "claude", "--dry-run"])
        self.assertEqual({e["harness"] for e in entries}, {"claude"})

    def test_codex_scanning_the_canonical_folder_needs_no_link(self):
        code, entries = self.run_main(["--harness", "codex"])
        self.assertEqual(code, 0)
        self.assertEqual({e["harness"] for e in entries}, {"codex"})
        self.assertTrue(all(e["status"] == "ok" for e in entries))
        self.assertEqual(self.calls, [])

    def test_codex_with_a_separate_folder_gets_links(self):
        dirs = {"claude": self.claude, "codex": os.path.join(self.tmp, "codex", "skills")}
        code, entries = self.run_main(["--harness", "codex"], dirs=dirs)
        self.assertTrue(all(e["status"] == "created" for e in entries))
        self.assertTrue(all(c[0].startswith(dirs["codex"]) for c in self.calls))

    def test_all_is_the_default_and_covers_both(self):
        code, entries = self.run_main(["--dry-run"])
        self.assertEqual({e["harness"] for e in entries}, {"claude", "codex"})
        self.assertEqual(len(entries), 10)
        code, entries = self.run_main(["--harness", "all", "--dry-run"])
        self.assertEqual(len(entries), 10)

    def test_unknown_harness_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_main(["--harness", "vim"])


class DefaultsTests(unittest.TestCase):
    def test_default_dirs_use_home(self):
        d = il.default_harness_dirs("/h")
        self.assertEqual(os.path.normpath(d["claude"]), os.path.normpath("/h/.claude/skills"))
        self.assertEqual(os.path.normpath(d["codex"]), os.path.normpath("/h/.agents/skills"))
        self.assertEqual(os.path.normpath(il.default_canonical_root("/h")), os.path.normpath("/h/.agents/skills"))


class RealLinkTests(unittest.TestCase):
    def test_create_link_and_detect(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "target dir")
            os.makedirs(target)
            link = os.path.join(tmp, "links", "l")
            os.makedirs(os.path.dirname(link))
            try:
                il.create_link(link, target)
            except OSError:
                self.skipTest("cannot create links here")
            self.assertTrue(il.points_to(link, target))
            self.assertFalse(il.points_to(link, os.path.join(tmp, "other")))
            self.assertFalse(il.points_to(target, target))  # a plain directory is not a link

    def check_metacharacter_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "t&x ^y %PATH% z")
            os.makedirs(target)
            link = os.path.join(tmp, "links & more", "l&k^%PATH%")
            os.makedirs(os.path.dirname(link))
            il.create_link(link, target)
            self.assertTrue(il.points_to(link, target))
            self.assertEqual(sorted(os.listdir(tmp)), ["links & more", "t&x ^y %PATH% z"])  # nothing stray

    def test_create_link_with_shell_metacharacters(self):
        self.check_metacharacter_paths()

    @unittest.skipUnless(os.name == "nt", "mklink fallback is Windows-only")
    def test_mklink_fallback_quotes_shell_metacharacters(self):
        from unittest import mock
        with mock.patch.object(il, "_winapi", None):
            self.check_metacharacter_paths()


if __name__ == "__main__":
    unittest.main()
