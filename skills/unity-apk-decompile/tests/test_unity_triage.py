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


if __name__ == "__main__":
    unittest.main()
