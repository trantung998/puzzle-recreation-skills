import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "wait_for_file.py")


def run(*args, timeout=60):
    proc = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise AssertionError("not JSON: stdout=%r stderr=%r" % (proc.stdout, proc.stderr))
    return proc.returncode, data


class WaitForFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "checks run", "pointer-portrait.txt")
        os.makedirs(os.path.dirname(self.path))

    def test_existing_file_found(self):
        with open(self.path, "w") as f:
            f.write("PASS\nevidence\n")
        code, data = run("--path", self.path, "--timeout", "10", "--interval", "0.1")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "found")
        self.assertEqual(data["size"], os.path.getsize(self.path))
        self.assertEqual(os.path.normcase(data["path"]), os.path.normcase(os.path.abspath(self.path)))

    def test_file_appearing_later_found(self):
        def later():
            time.sleep(0.5)
            with open(self.path, "w") as f:
                f.write("PASS\n")

        t = threading.Thread(target=later)
        t.start()
        try:
            code, data = run("--path", self.path, "--timeout", "15", "--interval", "0.1")
        finally:
            t.join()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "found")

    def test_timeout_exits_4(self):
        start = time.time()
        code, data = run("--path", self.path, "--timeout", "1", "--interval", "0.2")
        self.assertEqual(code, 4, data)
        self.assertEqual(data["status"], "timeout")
        self.assertLess(time.time() - start, 30)

    def test_empty_file_below_min_size_times_out(self):
        open(self.path, "w").close()
        code, data = run("--path", self.path, "--timeout", "1", "--interval", "0.2", "--min-size", "1")
        self.assertEqual(code, 4, data)

    def test_waits_for_stable_size(self):
        stop = threading.Event()

        def grow():
            with open(self.path, "w") as f:
                for _ in range(8):
                    if stop.is_set():
                        return
                    f.write("x" * 100)
                    f.flush()
                    time.sleep(0.25)

        t = threading.Thread(target=grow)
        t.start()
        try:
            # the poll interval is longer than the write gap, so only the finished file is stable
            code, data = run("--path", self.path, "--timeout", "20", "--interval", "0.5")
        finally:
            stop.set()
            t.join()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["size"], 800, "returned while the file was still growing")

    def test_bad_arguments_exit_2(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--path", self.path, "--timeout", "-1"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
