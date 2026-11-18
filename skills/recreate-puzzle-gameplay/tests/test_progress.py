import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "progress.py")
PHASES = ["intake", "decompile", "level-catalog", "mechanics", "visuals", "build", "verify", "game-notes", "handoff"]


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
    out = json.loads(p.stdout) if p.stdout.strip() else None
    return p.returncode, out


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.dir = os.path.join(self.tmp, "a b")
        os.makedirs(self.dir)
        self.apk = os.path.join(self.dir, "Parking+Loop_567_APKPure.xapk")
        with open(self.apk, "wb") as f:
            f.write(b"fake apk bytes")
        self.project = os.path.join(self.tmp, "proj")

    def tearDown(self):
        self._tmp.cleanup()

    def init(self):
        return run("init", "--apk", self.apk, "--levels", "50", "--project", self.project)

    def load(self, wd):
        with open(os.path.join(wd, "progress.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_init_creates_layout_and_progress(self):
        code, out = self.init()
        self.assertEqual(code, 0)
        wd = out["workdir"]
        for d in ["decompile", os.path.join("evidence", "levels"), os.path.join("evidence", "native"), "checks"]:
            self.assertTrue(os.path.isdir(os.path.join(wd, d)), d)
        self.assertTrue(os.path.isfile(os.path.join(wd, "decisions.md")))
        data = self.load(wd)
        self.assertEqual(data["schema"], 1)
        self.assertEqual(list(data["phases"]), PHASES)
        self.assertTrue(all(p["status"] == "pending" for p in data["phases"].values()))
        self.assertEqual(data["inputs"]["levels"], 50)
        self.assertEqual(data["tools"], {})
        self.assertEqual(out["next_phase"], "intake")

    def test_slug_and_workdir_from_awkward_path(self):
        code, out = self.init()
        self.assertEqual(out["slug"], "ParkingLoop")
        self.assertEqual(os.path.normcase(os.path.normpath(out["workdir"])),
                         os.path.normcase(os.path.join(self.dir, "ParkingLoop-recreation")))

    def test_complete_advances_next_phase(self):
        _, out = self.init()
        wd = out["workdir"]
        art = os.path.join(self.tmp, "art.txt")
        with open(art, "wb") as f:
            f.write(b"hello")
        code, res = run("complete", "--workdir", wd, "--phase", "intake", "--note", "n", "--artifact", art)
        self.assertEqual(code, 0)
        self.assertEqual(res["next_phase"], "decompile")
        ph = self.load(wd)["phases"]["intake"]
        self.assertEqual(ph["status"], "done")
        self.assertEqual(ph["note"], "n")
        self.assertTrue(ph["completed_at"])
        self.assertEqual(list(ph["artifacts"].values()), [hashlib.sha256(b"hello").hexdigest()])
        code, st = run("status", "--workdir", wd)
        self.assertEqual(code, 0)
        self.assertEqual(st["next_phase"], "decompile")

    def test_complete_unknown_phase_errors(self):
        _, out = self.init()
        code, _ = run("complete", "--workdir", out["workdir"], "--phase", "bogus")
        self.assertNotEqual(code, 0)

    def test_resume_rejects_changed_apk_hash(self):
        _, out = self.init()
        with open(self.apk, "wb") as f:
            f.write(b"different")
        code, res = run("resume", "--workdir", out["workdir"], "--apk", self.apk, "--levels", "50")
        self.assertEqual(code, 2)
        self.assertEqual(res["refused"], "apk_sha256")

    def test_resume_rejects_changed_level_count(self):
        _, out = self.init()
        code, res = run("resume", "--workdir", out["workdir"], "--apk", self.apk, "--levels", "51")
        self.assertEqual(code, 2)
        self.assertEqual(res["refused"], "levels")

    def test_resume_ok(self):
        _, out = self.init()
        code, res = run("resume", "--workdir", out["workdir"], "--apk", self.apk, "--levels", "50")
        self.assertEqual(code, 0)
        self.assertEqual(res["next_phase"], "intake")

    def test_init_on_existing_is_resume(self):
        _, out = self.init()
        run("complete", "--workdir", out["workdir"], "--phase", "intake")
        code, out2 = self.init()
        self.assertEqual(code, 0)
        self.assertEqual(out2["next_phase"], "decompile")
        self.assertEqual(self.load(out["workdir"])["phases"]["intake"]["status"], "done")

    def complete_all(self, wd, upto):
        art = os.path.join(self.tmp, "art.txt")
        with open(art, "wb") as f:
            f.write(b"artifact")
        for p in PHASES[:PHASES.index(upto) + 1]:
            code, _ = run("complete", "--workdir", wd, "--phase", p, "--note", "n-" + p, "--artifact", art)
            self.assertEqual(code, 0, p)

    def test_reset_from_phase_sets_later_pending(self):
        _, out = self.init()
        wd = out["workdir"]
        self.complete_all(wd, "visuals")
        code, res = run("reset", "--workdir", wd, "--from", "level-catalog")
        self.assertEqual(code, 0)
        self.assertEqual(res["next_phase"], "level-catalog")
        phases = self.load(wd)["phases"]
        self.assertEqual(list(phases), PHASES)
        for p in ("intake", "decompile"):
            self.assertEqual(phases[p]["status"], "done", p)
            self.assertEqual(phases[p]["note"], "n-" + p)
            self.assertEqual(len(phases[p]["artifacts"]), 1)
        for p in PHASES[PHASES.index("level-catalog"):]:
            self.assertEqual(phases[p], {"status": "pending", "completed_at": None, "note": None, "artifacts": {}}, p)
        self.assertEqual([n for n in os.listdir(wd) if n.startswith(".progress-")], [])

    def test_reset_unknown_phase_errors(self):
        _, out = self.init()
        wd = out["workdir"]
        self.complete_all(wd, "intake")
        before = self.load(wd)
        code, res = run("reset", "--workdir", wd, "--from", "bogus")
        self.assertEqual(code, 2)
        self.assertIn("error", res)
        self.assertEqual(self.load(wd), before)

    def test_reset_then_next_phase(self):
        _, out = self.init()
        wd = out["workdir"]
        self.complete_all(wd, "handoff")
        _, st = run("status", "--workdir", wd)
        self.assertIsNone(st["next_phase"])
        code, res = run("reset", "--workdir", wd, "--from", "verify")
        self.assertEqual((code, res["next_phase"]), (0, "verify"))
        _, st = run("status", "--workdir", wd)
        self.assertEqual(st["next_phase"], "verify")
        self.assertEqual(st["phases"]["build"], "done")
        self.assertEqual([st["phases"][p] for p in ("verify", "game-notes", "handoff")], ["pending"] * 3)
        code, res = run("complete", "--workdir", wd, "--phase", "verify")
        self.assertEqual((code, res["next_phase"]), (0, "game-notes"))

    def test_resume_project_path_normalized(self):
        code, out = run("init", "--apk", self.apk, "--levels", "50", "--project", self.project + os.sep)
        self.assertEqual(code, 0)
        self.assertEqual(set(out), {"workdir", "slug", "next_phase"})
        wd = out["workdir"]
        self.assertEqual(self.load(wd)["inputs"]["project"], os.path.abspath(self.project))
        same = os.path.join(self.project, "sub", "..")
        if os.name == "nt":
            same = same.upper()
        code, res = run("resume", "--workdir", wd, "--apk", self.apk, "--levels", "50", "--project", same)
        self.assertEqual(code, 0, res)
        code, res = run("init", "--apk", self.apk, "--levels", "50", "--project", same)
        self.assertEqual(code, 0, res)
        other = os.path.join(self.tmp, "other-proj")
        code, res = run("resume", "--workdir", wd, "--apk", self.apk, "--levels", "50", "--project", other)
        self.assertEqual((code, res["refused"]), (2, "project"))
        code, res = run("init", "--apk", self.apk, "--levels", "50", "--project", other)
        self.assertEqual((code, res["refused"]), (2, "project"))
        code, res = run("resume", "--workdir", wd, "--apk", self.apk, "--levels", "50")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
