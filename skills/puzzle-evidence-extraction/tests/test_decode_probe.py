import base64
import gzip
import hashlib
import importlib.util
import json
import os
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

try:
    import brotli
except ImportError:  # optional dependency
    brotli = None

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "decode_probe.py")
LEVEL = json.dumps({"stage": 7, "grid": {"width": 4, "height": 6, "tiles": [{"kind": 2, "color": 1}]}}).encode("utf-8")


def load_module():
    spec = importlib.util.spec_from_file_location("decode_probe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(b):
    return hashlib.sha256(b).hexdigest()


def aligned(payload):
    body = struct.pack("<i", len(payload)) + payload
    return body + b"\0" * (-len(body) % 4)


class DecodeProbeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self._tmp.name, "a b+c")
        os.makedirs(self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def probe(self, data, *args, prelude=None):
        path = os.path.join(self.dir, "level data.bin")
        with open(path, "wb") as f:
            f.write(data)
        if prelude:
            code = ("import runpy, sys; %s; sys.argv = sys.argv[1:]; "
                    "runpy.run_path(sys.argv[0], run_name='__main__')" % prelude)
            cmd = [sys.executable, "-c", code, SCRIPT, path, *args]
        else:
            cmd = [sys.executable, SCRIPT, path, *args]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["sha256_raw"], sha(data))
        for key in ("chain", "result", "preview", "sha256_raw", "sha256_decoded", "warnings"):
            self.assertIn(key, out)
        return out

    def test_plain_json(self):
        out = self.probe(LEVEL)
        self.assertEqual(out["chain"], ["json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))
        self.assertIn('"stage"', out["preview"])

    @unittest.skipIf(brotli is None, "brotli module not importable")
    def test_base64_brotli_json(self):
        out = self.probe(base64.b64encode(brotli.compress(LEVEL)))
        self.assertEqual(out["chain"], ["base64", "brotli", "json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))
        self.assertNotIn("brotli-unavailable", out["warnings"])

    def test_aligned_string_base64_gzip_json(self):
        out = self.probe(aligned(base64.b64encode(gzip.compress(LEVEL))))
        self.assertEqual(out["chain"], ["unity-aligned-string", "base64", "gzip", "json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_zlib_json(self):
        out = self.probe(zlib.compress(LEVEL))
        self.assertEqual(out["chain"], ["zlib", "json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_bom_json(self):
        out = self.probe(b"\xef\xbb\xbf" + LEVEL)
        self.assertEqual(out["chain"], ["utf8-bom", "json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_raw_deflate_json(self):
        c = zlib.compressobj(wbits=-15)
        out = self.probe(c.compress(LEVEL) + c.flush())
        self.assertEqual(out["chain"], ["raw-deflate", "json"])
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_json_scalar_is_text_not_json(self):
        out = self.probe(b"12345")
        self.assertEqual(out["result"], "text")
        self.assertNotIn("json", out["chain"])
        self.assertIn("json-scalar", out["warnings"])

    def test_max_depth_not_reported_when_json_found(self):
        mod = load_module()
        mod.TRANSFORMS = [
            ("dead-end", lambda d, w: d + b"x"),
            ("good", lambda d, w: LEVEL if d == b"start" else None),
        ]
        out, data = mod.probe(b"start", 2)
        self.assertEqual(out["result"], "json")
        self.assertEqual(out["chain"], ["good", "json"])
        self.assertNotIn("max-depth", out["warnings"])

    def test_random_bytes_undecoded(self):
        for seed in range(20):
            data = random.Random(seed).randbytes(512)
            out = self.probe(data)
            self.assertEqual(out["result"], "undecoded", seed)
            self.assertEqual(out["chain"], [], seed)
            self.assertIsNone(out["sha256_decoded"], seed)

    def test_depth_limit(self):
        data = LEVEL
        for _ in range(7):
            data = base64.b64encode(data)
        out = self.probe(data, "--max-depth", "6")
        self.assertNotEqual(out["result"], "json")
        self.assertNotIn("json", out["chain"])
        self.assertIn("max-depth", out["warnings"])

    def test_depth_limit_raised_reaches_json(self):
        data = LEVEL
        for _ in range(7):
            data = base64.b64encode(data)
        out = self.probe(data, "--max-depth", "8")
        self.assertEqual(out["chain"], ["base64"] * 7 + ["json"])
        self.assertEqual(out["result"], "json")

    def test_json_string_envelope(self):
        out = self.probe(json.dumps(base64.b64encode(zlib.compress(LEVEL)).decode()).encode())
        self.assertEqual(out["chain"], ["json-string", "base64", "zlib", "json"])
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_plain_text_is_text_not_json(self):
        out = self.probe(b"level 1: red red blue\nlevel 2: blue\n")
        self.assertEqual(out["result"], "text")
        self.assertEqual(out["chain"], [])

    def test_brotli_unavailable_is_reported_not_crash(self):
        payload = base64.b64encode(bytes(range(256)) * 4)
        out = self.probe(payload, prelude="sys.modules['brotli'] = None")
        self.assertIn("brotli-unavailable", out["warnings"])
        self.assertNotEqual(out["result"], "json")

    def test_out_writes_decoded_payload(self):
        dest = os.path.join(self.dir, "decoded level.json")
        out = self.probe(zlib.compress(LEVEL), "--out", dest)
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), LEVEL)
        self.assertEqual(out["sha256_decoded"], sha(LEVEL))

    def test_out_not_written_for_non_json(self):
        for data, result in ((b"plain words, not a level\n", "text"),
                             (gzip.compress(bytes(range(256)) * 2), "binary"),
                             (random.Random(99).randbytes(256), "undecoded")):
            dest = os.path.join(self.dir, "should not exist.json")
            out = self.probe(data, "--out", dest)
            self.assertEqual(out["result"], result)
            self.assertIsNone(out["out"])
            self.assertIn("out-not-written:" + result, out["warnings"])
            self.assertFalse(os.path.exists(dest), result)

    def test_missing_file_is_error(self):
        p = subprocess.run([sys.executable, SCRIPT, os.path.join(self.dir, "nope.bin")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("error", json.loads(p.stdout))


if __name__ == "__main__":
    unittest.main()
