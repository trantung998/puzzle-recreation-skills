import importlib.util
import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "unity_triage.py")
_spec = importlib.util.spec_from_file_location("unity_triage", SCRIPT)
unity_triage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unity_triage)


class PathsEnvTests(unittest.TestCase):
    def source(self, out, lib, meta):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "paths.env")
            with open(f, "w") as fh:
                fh.write(unity_triage.paths_env_text(out, lib, meta))
            r = subprocess.run(
                ["bash", "-c", 'source "$1"; printf "%s|%s|%s" "$W" "$SO" "${META-unset}"', "_", f],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_spaces_and_quotes_survive_source(self):
        self.assertEqual(
            self.source("/tmp/My Games/it's", "/x/lib il2cpp.so", None),
            "/tmp/My Games/it's|/x/lib il2cpp.so|unset")

    def test_windows_separators_normalised(self):
        self.assertEqual(
            self.source("H:\\UGame\\work", "H:\\UGame\\work\\unpacked\\libil2cpp.so", "H:\\m.dat"),
            "H:/UGame/work|H:/UGame/work/unpacked/libil2cpp.so|H:/m.dat")

    def test_write_paths_env_has_no_cr(self):
        with tempfile.TemporaryDirectory() as d:
            unity_triage.write_paths_env(d, "H:\\a\\lib.so", "H:\\m.dat")
            with open(os.path.join(d, "paths.env"), "rb") as fh:
                data = fh.read()
        self.assertNotIn(b"\r", data)
        self.assertEqual(data, b"W='%s'\nSO='H:/a/lib.so'\nMETA='H:/m.dat'\n" % d.replace("\\", "/").encode())


class HintTests(unittest.TestCase):
    def test_next_hint_uses_wrapper(self):
        hint = unity_triage.next_hint("/w/out")
        self.assertIn("in_env.sh", hint)
        self.assertIn(str(os.path.dirname(os.path.abspath(unity_triage.__file__))), hint)
        self.assertNotIn("source ", hint)


if __name__ == "__main__":
    unittest.main()
