import contextlib
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import ensure_tools  # noqa: E402


def zip_bytes(members):
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def tar_bytes(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def entry(tid, folder, url, sha=None, archive="zip", detect=None, post="none", **extra):
    plat = {"url": url, "sha256": sha, "archive": archive}
    e = {
        "id": tid, "version": "1", "folder": folder, "required": True,
        "detect": detect or ["bin/tool.txt"],
        "windows": plat, "linux": plat, "macos": plat, "post": post,
    }
    e.update(extra)
    return e


class FakeFetch:
    def __init__(self, blobs):
        self.blobs = blobs
        self.calls = []

    def __call__(self, url, dest):
        self.calls.append(url)
        with open(dest, "wb") as f:
            f.write(self.blobs[url])


class EnsureToolsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.root = os.path.join(self.tmp, "tools")
        os.makedirs(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def ensure(self, tools, fetch, check=False, **kw):
        return ensure_tools.ensure(self.root, {"schema": 1, "tools": tools}, check=check, fetch=fetch,
                                   platform="windows", **kw)

    def make_present(self, folder, rel="bin/tool.txt"):
        p = os.path.join(self.root, folder, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("x")

    def test_root_resolution_order(self):
        pl = os.path.join(self.tmp, "pl")
        envdir = os.path.join(self.tmp, "envdir")
        cache = os.path.join(self.tmp, "cache")
        os.makedirs(pl)
        with mock.patch.object(ensure_tools, "PARKINGLOOP_TOOLS", pl), \
                mock.patch.object(ensure_tools, "cache_root", return_value=cache):
            with mock.patch.dict(os.environ, {"UNITY_DECOMPILE_TOOLS": envdir}):
                self.assertEqual(ensure_tools.resolve_root(), envdir)
            with mock.patch.dict(os.environ):
                os.environ.pop("UNITY_DECOMPILE_TOOLS", None)
                self.assertEqual(ensure_tools.resolve_root(), pl)
            with mock.patch.object(ensure_tools, "PARKINGLOOP_TOOLS", os.path.join(self.tmp, "missing")), \
                    mock.patch.dict(os.environ):
                os.environ.pop("UNITY_DECOMPILE_TOOLS", None)
                self.assertEqual(ensure_tools.resolve_root(), cache)

    def test_present_tools_not_downloaded(self):
        self.make_present("a-1")
        self.make_present("b-1")
        fetch = FakeFetch({})
        res = self.ensure([entry("a", "a-1", "https://x.invalid/a.zip"),
                           entry("b", "b-1", "https://x.invalid/b.zip")], fetch)
        self.assertEqual(fetch.calls, [])
        self.assertEqual(res["tools"]["a"]["status"], "present")
        self.assertEqual(res["tools"]["b"]["status"], "present")
        self.assertEqual(res["tools"]["a"]["path"], os.path.join(self.root, "a-1"))

    def test_partial_dir_installs_only_missing(self):
        self.make_present("jdk-1")
        url = "https://x.invalid/ghidra.zip"
        fetch = FakeFetch({url: zip_bytes({"ghidra-1/bin/tool.txt": b"hi"})})
        res = self.ensure([entry("jdk", "jdk-1", "https://x.invalid/jdk.zip"),
                           entry("ghidra", "ghidra-1", url)], fetch)
        self.assertEqual(fetch.calls, [url])
        self.assertEqual(res["tools"]["jdk"]["status"], "present")
        self.assertEqual(res["tools"]["ghidra"]["status"], "installed")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "ghidra-1", "bin", "tool.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "ghidra-1.partial")))

    def test_single_top_level_dir_stripped_only_when_single(self):
        url = "https://x.invalid/t.zip"
        fetch = FakeFetch({url: zip_bytes({"bin/tool.txt": b"1", "other.txt": b"2"})})
        res = self.ensure([entry("t", "t-1", url)], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "installed")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "t-1", "bin", "tool.txt")))

    def test_hash_mismatch_rejected_and_removed(self):
        url = "https://x.invalid/ghidra.zip"
        fetch = FakeFetch({url: zip_bytes({"ghidra-1/bin/tool.txt": b"hi"})})
        res = self.ensure([entry("ghidra", "ghidra-1", url, sha="0" * 64)], fetch)
        self.assertEqual(res["tools"]["ghidra"]["status"], "failed")
        self.assertIn("sha256", res["tools"]["ghidra"]["detail"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "ghidra-1")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "ghidra-1.partial")))
        dl = os.path.join(self.root, "downloads")
        self.assertEqual(os.listdir(dl) if os.path.isdir(dl) else [], [])

    def test_null_sha_records_computed_hash(self):
        url = "https://x.invalid/ghidra.zip"
        blob = zip_bytes({"ghidra-1/bin/tool.txt": b"hi"})
        res = self.ensure([entry("ghidra", "ghidra-1", url, sha=None)], FakeFetch({url: blob}))
        self.assertEqual(res["tools"]["ghidra"]["status"], "installed")
        self.assertIn(hashlib.sha256(blob).hexdigest(), res["tools"]["ghidra"]["detail"])

    def test_matching_sha_installs(self):
        url = "https://x.invalid/ghidra.zip"
        blob = zip_bytes({"ghidra-1/bin/tool.txt": b"hi"})
        res = self.ensure([entry("ghidra", "ghidra-1", url, sha=hashlib.sha256(blob).hexdigest().upper())],
                          FakeFetch({url: blob}))
        self.assertEqual(res["tools"]["ghidra"]["status"], "installed")

    def test_stale_corrupt_archive_never_reused(self):
        url = "https://x.invalid/ghidra.zip"
        blob = zip_bytes({"ghidra-1/bin/tool.txt": b"hi"})
        dl = os.path.join(self.root, "downloads")
        os.makedirs(dl)
        with open(os.path.join(dl, "ghidra-1.zip"), "wb") as f:
            f.write(b"corrupt leftovers")
        os.makedirs(os.path.join(self.root, "ghidra-1.partial"))
        fetch = FakeFetch({url: blob})
        res = self.ensure([entry("ghidra", "ghidra-1", url, sha=hashlib.sha256(blob).hexdigest())], fetch)
        self.assertEqual(fetch.calls, [url])
        self.assertEqual(res["tools"]["ghidra"]["status"], "installed")

    def test_check_mode_never_fetches(self):
        fetch = FakeFetch({})
        res = self.ensure([entry("ghidra", "ghidra-1", "https://x.invalid/g.zip")], fetch, check=True)
        self.assertEqual(fetch.calls, [])
        self.assertEqual(res["tools"]["ghidra"]["status"], "failed")
        self.assertFalse(os.path.exists(os.path.join(self.root, "ghidra-1")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "downloads")))

    def test_check_mode_exit_code_3(self):
        mpath = os.path.join(self.tmp, "m.json")
        with open(mpath, "w") as f:
            json.dump({"schema": 1, "tools": [entry("ghidra", "ghidra-1", "https://x.invalid/g.zip")]}, f)
        fetch = FakeFetch({})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ensure_tools.main(["--check", "--root", self.root, "--manifest", mpath], fetch=fetch)
        self.assertEqual(code, 3)
        self.assertEqual(fetch.calls, [])
        self.assertEqual(json.loads(out.getvalue())["tools"]["ghidra"]["status"], "failed")

    def test_zip_slip_rejected(self):
        url = "https://x.invalid/evil.zip"
        fetch = FakeFetch({url: zip_bytes({"ok/bin/tool.txt": b"1", "../evil": b"pwn"})})
        res = self.ensure([entry("evil", "evil-1", url)], fetch)
        self.assertEqual(res["tools"]["evil"]["status"], "failed")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil-1")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil-1.partial")))

    def test_zip_absolute_and_backslash_traversal_rejected(self):
        for bad in ("/abs/evil", "a\\..\\..\\evil", "C:/evil", "C:\\evil"):
            url = "https://x.invalid/evil.zip"
            fetch = FakeFetch({url: zip_bytes({bad: b"pwn"})})
            res = self.ensure([entry("evil", "evil-1", url)], fetch)
            self.assertEqual(res["tools"]["evil"]["status"], "failed", bad)
            self.assertFalse(os.path.exists(os.path.join(self.root, "evil-1.partial")), bad)

    def test_tar_slip_rejected(self):
        url = "https://x.invalid/evil.tar.gz"
        fetch = FakeFetch({url: tar_bytes({"ok/bin/tool.txt": b"1", "../evil": b"pwn"})})
        res = self.ensure([entry("evil", "evil-1", url, archive="tar.gz")], fetch)
        self.assertEqual(res["tools"]["evil"]["status"], "failed")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil-1.partial")))

    def test_tar_installs(self):
        url = "https://x.invalid/t.tar.gz"
        fetch = FakeFetch({url: tar_bytes({"t-1/bin/tool.txt": b"1"})})
        res = self.ensure([entry("t", "t-1", url, archive="tar.gz")], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "installed")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "t-1", "bin", "tool.txt")))

    def test_non_https_url_rejected_without_fetch(self):
        fetch = FakeFetch({})
        res = self.ensure([entry("t", "t-1", "http://x.invalid/t.zip")], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "failed")
        self.assertEqual(fetch.calls, [])

    def test_folder_with_separator_rejected(self):
        fetch = FakeFetch({})
        res = self.ensure([entry("t", "../t-1", "https://x.invalid/t.zip")], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "failed")
        self.assertEqual(fetch.calls, [])

    def test_missing_detect_after_extract_fails_and_cleans(self):
        url = "https://x.invalid/t.zip"
        fetch = FakeFetch({url: zip_bytes({"t-1/other.txt": b"1"})})
        res = self.ensure([entry("t", "t-1", url)], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "failed")
        self.assertFalse(os.path.exists(os.path.join(self.root, "t-1")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "t-1.partial")))

    def test_existing_incomplete_folder_not_overwritten(self):
        os.makedirs(os.path.join(self.root, "t-1"))
        with open(os.path.join(self.root, "t-1", "mine.txt"), "w") as f:
            f.write("user data")
        url = "https://x.invalid/t.zip"
        fetch = FakeFetch({url: zip_bytes({"t-1/bin/tool.txt": b"1"})})
        res = self.ensure([entry("t", "t-1", url)], fetch)
        self.assertEqual(res["tools"]["t"]["status"], "failed")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "t-1", "mine.txt")))

    def test_fetch_error_reported_as_failed(self):
        def boom(url, dest):
            with open(dest, "wb") as f:
                f.write(b"half")
            raise OSError("network down")
        res = self.ensure([entry("t", "t-1", "https://x.invalid/t.zip")], boom)
        self.assertEqual(res["tools"]["t"]["status"], "failed")
        self.assertIn("network down", res["tools"]["t"]["detail"])
        dl = os.path.join(self.root, "downloads")
        self.assertEqual(os.listdir(dl) if os.path.isdir(dl) else [], [])

    def test_exec_bits_post_marks_apphost_executable(self):
        # Il2CppInspectorRedux release zips store the Linux/macOS apphost as 0644
        url = "https://x.invalid/i.zip"
        fetch = FakeFetch({url: zip_bytes({"Il2CppInspectorRedux.Legacy.CLI-linux-x64/Il2CppInspector": b"elf",
                                           "Il2CppInspectorRedux.Legacy.CLI-linux-x64/Il2CppInspector.pdb": b"p"})})
        e = entry("il2cppinspector", "i-1", url, detect={"linux": ["Il2CppInspector"]}, post="exec-bits",
                  exec=["Il2CppInspector"])
        res = ensure_tools.ensure(self.root, {"schema": 1, "tools": [e]}, fetch=fetch, platform="linux")
        self.assertEqual(res["tools"]["il2cppinspector"]["status"], "installed", res)
        exe = os.path.join(self.root, "i-1", "Il2CppInspector")
        self.assertTrue(os.path.isfile(exe))
        if os.name != "nt":
            self.assertTrue(os.access(exe, os.X_OK))

    def test_exec_bits_post_missing_file_fails(self):
        url = "https://x.invalid/i.zip"
        fetch = FakeFetch({url: zip_bytes({"other": b"x"})})
        e = entry("il2cppinspector", "i-1", url, detect={"linux": ["other"]}, post="exec-bits",
                  exec=["Il2CppInspector"])
        res = ensure_tools.ensure(self.root, {"schema": 1, "tools": [e]}, fetch=fetch, platform="linux")
        self.assertEqual(res["tools"]["il2cppinspector"]["status"], "failed")
        self.assertIn("Il2CppInspector", res["tools"]["il2cppinspector"]["detail"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "i-1")))

    def test_venv_post_uses_runner_and_cleans_on_failure(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            if argv[1:3] == ["-m", "venv"]:
                py = os.path.join(argv[3], "Scripts", "python.exe")
                os.makedirs(os.path.dirname(py))
                with open(py, "w") as f:
                    f.write("")
                return 0, ""
            return 1, "pip exploded"
        e = entry("python-venv", "py-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv-pyyaml",
                  pip=["PyYAML==6.0.3"])
        del e["windows"], e["linux"], e["macos"]
        res = self.ensure([e], FakeFetch({}), runner=runner)
        self.assertEqual(res["tools"]["python-venv"]["status"], "failed")
        self.assertIn("pip exploded", res["tools"]["python-venv"]["detail"])
        self.assertEqual(calls[0][:3], [sys.executable, "-m", "venv"])
        self.assertEqual(calls[1][1:], ["-m", "pip", "install", "PyYAML==6.0.3"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "py-1")))

    def test_venv_pip_spec_comes_from_manifest_field(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            if argv[1:3] == ["-m", "venv"]:
                py = os.path.join(argv[3], "Scripts", "python.exe")
                os.makedirs(os.path.dirname(py))
                with open(py, "w") as f:
                    f.write("")
            return 0, ""
        e = entry("python-venv", "py-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv-pyyaml",
                  pip=["PyYAML==9.9.9", "other==1.0"])
        del e["windows"], e["linux"], e["macos"]
        res = self.ensure([e], FakeFetch({}), runner=runner)
        self.assertEqual(res["tools"]["python-venv"]["status"], "installed")
        self.assertEqual(calls[1][1:], ["-m", "pip", "install", "PyYAML==9.9.9", "other==1.0"])

    def test_venv_without_exact_pin_fails_without_running_pip(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            if argv[1:3] == ["-m", "venv"]:
                py = os.path.join(argv[3], "Scripts", "python.exe")
                os.makedirs(os.path.dirname(py))
                with open(py, "w") as f:
                    f.write("")
            return 0, ""
        for pip in (None, ["PyYAML"], ["PyYAML>=6"]):
            kw = {} if pip is None else {"pip": pip}
            e = entry("python-venv", "py-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv-pyyaml", **kw)
            del e["windows"], e["linux"], e["macos"]
            res = self.ensure([e], FakeFetch({}), runner=runner)
            self.assertEqual(res["tools"]["python-venv"]["status"], "failed", pip)
            self.assertFalse(any(c[1:3] == ["-m", "pip"] for c in calls), pip)
            self.assertFalse(os.path.exists(os.path.join(self.root, "py-1")), pip)

    def test_detect_glob_pattern(self):
        rel = "lib/python*/site-packages/Pkg/__init__.py"
        e = entry("dec", "dec-1", "https://x.invalid/d.zip", detect={"windows": [rel, "bin/tool.txt"]})
        self.make_present("dec-1")
        res = self.ensure([e], FakeFetch({}), check=True)
        self.assertEqual(res["tools"]["dec"]["status"], "failed")
        self.make_present("dec-1", "lib/python3.12/site-packages/Pkg/__init__.py")
        res = self.ensure([e], FakeFetch({}), check=True)
        self.assertEqual(res["tools"]["dec"]["status"], "present")
        self.assertFalse(ensure_tools.folder_is_complete(os.path.join(self.root, "dec-1"),
                                                         {"detect": ["lib/python*/site-packages/Other/x.py"]},
                                                         "windows"))

    def test_venv_min_python_too_old_fails_without_running_anything(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, ""
        e = entry("dec", "dec-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv",
                  pip=["A==1.0"], required=False, min_python=[99, 0])
        del e["windows"], e["linux"], e["macos"]
        res = self.ensure([e], FakeFetch({}), runner=runner)
        t = res["tools"]["dec"]
        self.assertEqual(t["status"], "failed")
        self.assertIn("Python >= 99.0", t["detail"])
        self.assertIn("re-run ensure_tools.py", t["detail"])
        self.assertEqual(calls, [])
        self.assertFalse(os.path.exists(os.path.join(self.root, "dec-1")))

    def test_venv_min_python_satisfied_installs(self):
        def runner(argv):
            if argv[1:3] == ["-m", "venv"]:
                py = os.path.join(argv[3], "Scripts", "python.exe")
                os.makedirs(os.path.dirname(py))
                open(py, "w").close()
            return 0, ""
        e = entry("dec", "dec-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv",
                  pip=["A==1.0"], required=False, min_python=[3, 0])
        del e["windows"], e["linux"], e["macos"]
        res = self.ensure([e], FakeFetch({}), runner=runner)
        self.assertEqual(res["tools"]["dec"]["status"], "installed")

    def test_manifest_level_decoders_needs_python_310(self):
        m = ensure_tools.load_manifest(ensure_tools.MANIFEST_PATH)
        dec = next(t for t in m["tools"] if t["id"] == "level-decoders")
        self.assertEqual(dec.get("min_python"), [3, 10])

    def test_manifest_rejects_bad_min_python(self):
        for bad in ("3.10", [3], [3, "10"]):
            path = os.path.join(self.root, "m.json")
            os.makedirs(self.root, exist_ok=True)
            with open(path, "w") as f:
                json.dump({"schema": 1, "tools": [{"id": "v", "folder": "v", "post": "venv",
                                                    "pip": ["A==1"], "min_python": bad}]}, f)
            with self.assertRaises(ValueError, msg=bad):
                ensure_tools.load_manifest(path)

    def test_generic_venv_post_installs_exact_pins(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            if argv[1:3] == ["-m", "venv"]:
                py = os.path.join(argv[3], "Scripts", "python.exe")
                os.makedirs(os.path.dirname(py))
                with open(py, "w") as f:
                    f.write("")
            return 0, ""
        e = entry("dec", "dec-1", None, detect={"windows": ["Scripts/python.exe"]}, post="venv",
                  pip=["A==1.0", "b==2"], required=False)
        del e["windows"], e["linux"], e["macos"]
        res = self.ensure([e], FakeFetch({}), runner=runner)
        self.assertEqual(res["tools"]["dec"]["status"], "installed")
        self.assertEqual(calls[1][1:], ["-m", "pip", "install", "A==1.0", "b==2"])
        for pip in (None, ["A"], ["A>=1"]):
            bad = {"id": "v", "folder": "v", "post": "venv", "detect": []}
            if pip is not None:
                bad["pip"] = pip
            with self.assertRaises(ValueError, msg=str(pip)):
                ensure_tools.load_manifest(self.write_manifest([bad]))

    def test_optional_tool_failure_keeps_exit_zero(self):
        self.make_present("req-1")
        opt = entry("opt", "opt-1", "https://x.invalid/o.zip", required=False)
        req = entry("req", "req-1", "https://x.invalid/r.zip")
        mpath = self.write_manifest([req, opt])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ensure_tools.main(["--check", "--root", self.root, "--manifest", mpath])
        res = json.loads(out.getvalue())
        self.assertEqual(res["tools"]["opt"]["status"], "failed")
        self.assertEqual(res["tools"]["req"]["status"], "present")
        self.assertEqual(code, 0)
        with contextlib.redirect_stdout(io.StringIO()):
            code = ensure_tools.main(["--root", self.root, "--manifest", mpath],
                                     fetch=FakeFetch({"https://x.invalid/o.zip": b"not a zip"}))
        self.assertEqual(code, 0)
        mpath = self.write_manifest([req, dict(opt, required=True)])
        with contextlib.redirect_stdout(io.StringIO()):
            code = ensure_tools.main(["--check", "--root", self.root, "--manifest", mpath])
        self.assertEqual(code, 3)

    def write_manifest(self, tools):
        path = os.path.join(self.tmp, "m-%d.json" % len(os.listdir(self.tmp)))
        with open(path, "w") as f:
            json.dump({"schema": 1, "tools": tools}, f)
        return path

    def test_load_manifest_rejects_unpinned_pip(self):
        for pip in (None, [], ["PyYAML"], ["PyYAML>=6"]):
            e = {"id": "v", "folder": "v", "post": "venv-pyyaml", "detect": []}
            if pip is not None:
                e["pip"] = pip
            with self.assertRaises(ValueError, msg=str(pip)):
                ensure_tools.load_manifest(self.write_manifest([e]))

    def test_load_manifest_requires_sha256_source(self):
        good = entry("a", "a-1", "https://x.invalid/a.zip", sha="a" * 64)
        good["windows"]["sha256_source"] = "publisher-api"
        ensure_tools.load_manifest(self.write_manifest([good]))
        for sha, source in (("a" * 64, None), ("a" * 64, "made-up"), (None, "publisher-api")):
            bad = entry("a", "a-1", "https://x.invalid/a.zip", sha=sha)
            bad["windows"]["sha256_source"] = source
            with self.assertRaises(ValueError, msg=str((sha, source))):
                ensure_tools.load_manifest(self.write_manifest([bad]))

    def test_redirect_to_http_refused(self):
        import urllib.error
        import urllib.request
        handler = ensure_tools.HttpsOnlyRedirectHandler()
        req = urllib.request.Request("https://x.invalid/a.zip")
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(req, io.BytesIO(), 302, "Found", {}, "http://evil.invalid/a.zip")
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(req, io.BytesIO(), 301, "Moved", {}, "HTTP://evil.invalid/a.zip")
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(req, io.BytesIO(), 302, "Found", {}, "ftp://evil.invalid/a.zip")
        nxt = handler.redirect_request(req, io.BytesIO(), 302, "Found", {}, "https://cdn.invalid/a.zip")
        self.assertEqual(nxt.full_url, "https://cdn.invalid/a.zip")

    def test_default_fetch_uses_https_only_opener_and_refuses_http_url(self):
        opener = ensure_tools.make_opener()
        self.assertTrue(any(isinstance(h, ensure_tools.HttpsOnlyRedirectHandler) for h in opener.handlers))

        class FakeOpener:
            def open(self, req, timeout=None):
                return io.BytesIO(b"payload")
        dest = os.path.join(self.tmp, "dl.bin")
        with mock.patch.object(ensure_tools, "make_opener", return_value=FakeOpener()):
            ensure_tools.default_fetch("https://x.invalid/a.zip", dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"payload")
            with self.assertRaises(ValueError):
                ensure_tools.default_fetch("http://x.invalid/a.zip", dest)

    def test_dotnet_missing_is_manual(self):
        e = {"id": "dotnet", "version": "8+", "folder": None, "required": True, "post": "none",
             "detect_command": "dotnet", "detect": [],
             "manual": {"windows": "stop: hand to the user \u2014 dotnet-install.ps1 -Version 8.0.1 -InstallDir \"{root}/dotnet\"",
                        "linux": "x", "macos": "y"}}
        with mock.patch.object(ensure_tools.shutil, "which", return_value=None):
            res = self.ensure([e], FakeFetch({}))
        self.assertEqual(res["tools"]["dotnet"]["status"], "manual")
        detail = res["tools"]["dotnet"]["detail"]
        self.assertTrue(detail.startswith("Not found. stop: hand to the user \u2014 "), detail)
        self.assertIn('-InstallDir "%s/dotnet"' % self.root, detail)
        self.assertNotIn("{root}", detail)
        self.assertNotIn("Install manually", detail)

    def test_detect_extra_under_tool_root(self):
        e = {"id": "dotnet", "version": "8+", "folder": None, "required": True, "post": "none",
             "detect_command": "dotnet", "detect": [],
             "detect_extra": {"windows": ["{root}/dotnet/dotnet.exe"]}, "manual": {"windows": "x"}}
        self.make_present("dotnet", "dotnet.exe")
        with mock.patch.object(ensure_tools.shutil, "which", return_value=None):
            res = self.ensure([e], FakeFetch({}))
        self.assertEqual(res["tools"]["dotnet"]["status"], "present", res)
        self.assertEqual(os.path.normcase(os.path.normpath(res["tools"]["dotnet"]["path"])),
                         os.path.normcase(os.path.join(self.root, "dotnet", "dotnet.exe")))

    def dotnet10(self, **extra):
        e = {"id": "dotnet", "version": "10+", "folder": None, "required": True, "post": "none",
             "detect_command": "dotnet", "detect": [], "min_runtime": {"name": "Microsoft.NETCore.App", "major": 10},
             "manual": {"windows": "stop: hand to the user \u2014 install into \"{root}/dotnet\""}}
        e.update(extra)
        return e

    def test_dotnet_runtime_too_old_is_manual(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            return 0, ("Microsoft.AspNetCore.App 8.0.14 [/x]\nMicrosoft.NETCore.App 8.0.14 [/x]\n"
                       "Microsoft.NETCore.App 9.0.7 [/x]\nMicrosoft.WindowsDesktop.App 9.0.7 [/x]\n")
        with mock.patch.object(ensure_tools.shutil, "which", return_value="/usr/bin/dotnet"):
            res = self.ensure([self.dotnet10()], FakeFetch({}), runner=runner)
        t = res["tools"]["dotnet"]
        self.assertEqual(t["status"], "manual", t)
        self.assertIn("Microsoft.NETCore.App 10+", t["detail"])
        self.assertIn("8.0.14, 9.0.7", t["detail"])
        self.assertIn('"%s/dotnet"' % self.root, t["detail"])
        self.assertEqual(calls, [["/usr/bin/dotnet", "--list-runtimes"]])

    def test_dotnet_runtime_new_enough_under_root_wins_over_old_path(self):
        self.make_present("dotnet", "dotnet.exe")
        mine = os.path.join(self.root, "dotnet", "dotnet.exe")

        def runner(argv):
            new = os.path.normcase(os.path.normpath(argv[0])) == os.path.normcase(mine)
            return 0, "Microsoft.NETCore.App %s [/x]\n" % ("10.0.15" if new else "9.0.7")
        e = self.dotnet10(detect_extra={"windows": ["{root}/dotnet/dotnet.exe"]})
        with mock.patch.object(ensure_tools.shutil, "which", return_value="/usr/bin/dotnet"):
            res = self.ensure([e], FakeFetch({}), runner=runner)
        t = res["tools"]["dotnet"]
        self.assertEqual(t["status"], "present", t)
        self.assertEqual(os.path.normcase(os.path.normpath(t["path"])), os.path.normcase(mine))

    def test_default_runner_keeps_full_output(self):
        code, out = ensure_tools.default_runner([sys.executable, "-c", "print('x' * 2000)"])
        self.assertEqual((code, len(out.strip())), (0, 2000))

    def test_relative_env_root_made_absolute(self):
        with mock.patch.dict(os.environ, {"UNITY_DECOMPILE_TOOLS": os.path.join("rel", "tools")}):
            root = ensure_tools.resolve_root()
        self.assertTrue(os.path.isabs(root), root)
        self.assertEqual(root, os.path.abspath(os.path.join("rel", "tools")))

    def test_real_manifest_manual_hints_are_pinned_user_scope_stops(self):
        manifest = ensure_tools.load_manifest(os.path.join(SCRIPTS, "tools-manifest.json"))
        by_id = {t["id"]: t for t in manifest["tools"]}
        self.assertEqual(set(by_id["dotnet"]["manual"]), {"windows", "linux", "macos"})
        for tid in ("dotnet", "git-bash"):
            for plat, hint in by_id[tid]["manual"].items():
                self.assertTrue(hint.startswith("stop: hand to the user \u2014 "), (tid, plat, hint))
                for banned in ("winget", "sudo", "brew", "apt ", "latest", "Program Files"):
                    self.assertNotIn(banned, hint, (tid, plat))
                self.assertIn("{root}", hint, (tid, plat))
        self.assertIn("dotnet-install.ps1 -Runtime dotnet -Version 10.0.15 -InstallDir", by_id["dotnet"]["manual"]["windows"])
        for plat in ("linux", "macos"):
            self.assertIn("dotnet-install.sh --runtime dotnet --version 10.0.15 --install-dir",
                          by_id["dotnet"]["manual"][plat])
        # Il2CppInspectorRedux 2026.2 is built for .NET 10 and cannot roll back to an older runtime
        self.assertEqual(by_id["dotnet"]["min_runtime"], {"name": "Microsoft.NETCore.App", "major": 10})
        self.assertIn("{root}/dotnet/dotnet.exe", by_id["dotnet"]["detect_extra"]["windows"])
        git = by_id["git-bash"]["manual"]["windows"]
        self.assertIn("PortableGit-2.56.1-64-bit.7z.exe", git)
        self.assertIn("9dd04a608ceb5f6ab32a73709e0ecb159d211da71b697c45ff81f6dd0c6b49c7", git)
        self.assertIn("{root}/PortableGit/bin/bash.exe", by_id["git-bash"]["detect_extra"]["windows"])

    def test_dotnet_found_on_path_is_present(self):
        e = {"id": "dotnet", "version": "8+", "folder": None, "required": True, "post": "none",
             "detect_command": "dotnet", "detect": [], "manual": {"windows": "x"}}
        with mock.patch.object(ensure_tools.shutil, "which", return_value="/usr/bin/dotnet"):
            res = self.ensure([e], FakeFetch({}))
        self.assertEqual(res["tools"]["dotnet"]["status"], "present")
        self.assertEqual(res["tools"]["dotnet"]["path"], "/usr/bin/dotnet")

    def test_windows_only_tool_skipped_elsewhere(self):
        e = {"id": "git-bash", "version": "any", "folder": None, "required": True, "post": "none",
             "only": ["windows"], "detect_command": "bash", "detect": [], "manual": {"windows": "winget install Git.Git"}}
        res = ensure_tools.ensure(self.root, {"schema": 1, "tools": [e]}, check=True, fetch=FakeFetch({}),
                                  platform="linux")
        self.assertNotIn("git-bash", res["tools"])

    def test_progress_written(self):
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        with open(os.path.join(work, "progress.json"), "w") as f:
            json.dump({"schema": 1, "inputs": {"n": 1}, "slug": "G", "tools": {}, "phases": {}}, f)
        self.make_present("a-1")
        mpath = os.path.join(self.tmp, "m.json")
        with open(mpath, "w") as f:
            json.dump({"schema": 1, "tools": [entry("a", "a-1", "https://x.invalid/a.zip")]}, f)
        with contextlib.redirect_stdout(io.StringIO()):
            code = ensure_tools.main(["--root", self.root, "--manifest", mpath, "--progress", work],
                                     fetch=FakeFetch({}))
        self.assertEqual(code, 0)
        with open(os.path.join(work, "progress.json")) as f:
            data = json.load(f)
        self.assertEqual(data["tools"]["a"]["status"], "present")
        self.assertEqual(data["slug"], "G")
        self.assertEqual(data["inputs"], {"n": 1})
        self.assertEqual([n for n in os.listdir(work) if n != "progress.json"], [])

    def test_real_manifest_shape(self):
        manifest = ensure_tools.load_manifest(os.path.join(SCRIPTS, "tools-manifest.json"))
        by_id = {t["id"]: t for t in manifest["tools"]}
        self.assertEqual({k: v["folder"] for k, v in by_id.items() if v.get("folder")}, {
            "python-venv": "decompile-python", "jdk": "jdk-25", "ghidra": "ghidra-12.2",
            "il2cppinspector": "Il2CppInspectorRedux-2026.2", "assetripper": "AssetRipper_2.0.0",
            "ilspycmd": "ilspycmd-9.1.0", "level-decoders": "level-decoders-venv",
            "ghidra-natives": "ghidra-12.2"})
        self.assertIn("dotnet", by_id)
        self.assertEqual(by_id["git-bash"]["only"], ["windows"])
        self.assertEqual(by_id["python-venv"]["pip"], ["PyYAML==6.0.3"])
        self.assertNotIn("UnityPy", by_id["python-venv"]["version"])
        dec = by_id["level-decoders"]
        self.assertIs(dec["required"], False)
        self.assertEqual(dec["post"], "venv")
        self.assertIn("UnityPy==1.25.4", dec["pip"])
        self.assertIn("brotli==1.2.1", dec["pip"])
        self.assertTrue(all("==" in p for p in dec["pip"]))
        self.assertEqual(len({p.split("==")[0].lower() for p in dec["pip"]}), len(dec["pip"]))
        self.assertIn("Lib/site-packages/UnityPy/__init__.py", dec["detect"]["windows"])
        self.assertIn("lib/python3*/site-packages/UnityPy/__init__.py", dec["detect"]["linux"])
        for t in manifest["tools"]:
            if t["id"] != "level-decoders":
                self.assertIs(t.get("required", True), True, t["id"])
        for tid, keys in (("jdk", ("windows", "linux", "macos", "linux-arm64", "macos-arm64")),
                          ("assetripper", ("windows", "linux", "macos", "linux-arm64", "macos-arm64")),
                          ("ghidra", ("windows", "linux", "macos")),
                          ("il2cppinspector", ("windows", "linux", "macos", "linux-arm64", "macos-arm64")),
                          ("ilspycmd", ("windows",))):
            for key in keys:
                self.assertIsNotNone(by_id[tid][key]["sha256"], (tid, key))
        self.assertNotIn("il2cppdumper", by_id)
        ins = by_id["il2cppinspector"]
        self.assertEqual((ins["post"], ins["exec"]), ("exec-bits", ["Il2CppInspector"]))
        self.assertEqual(ins["detect"]["windows"], ["Il2CppInspector.exe"])
        for key in ("windows", "linux", "macos", "linux-arm64", "macos-arm64"):
            self.assertEqual(by_id["assetripper"][key]["sha256_source"], "publisher-api")
            self.assertEqual(ins[key]["sha256_source"], "publisher-api")
            self.assertIn("/releases/download/2026.2/Il2CppInspectorRedux.Legacy.CLI-", ins[key]["url"])
            if key != "windows":
                self.assertEqual(by_id["jdk"][key]["sha256_source"], "publisher-checksum-file")
        for t in manifest["tools"]:
            for key in ("windows", "linux", "macos", "linux-arm64", "macos-arm64"):
                p = t.get(key)
                if p:
                    self.assertTrue(p["url"].startswith("https://"), t["id"])
                    self.assertTrue(p["sha256"] is None or len(p["sha256"]) == 64, t["id"])
                    self.assertIn(p["archive"], ("zip", "tar.gz", "tar.xz", "nupkg"))


GRADLE_URL = "https://services.gradle.org/distributions/gradle-9.8.0-bin.zip"
GRADLE_SHA = "bafd5ce9cfaea0fbccfdc8439a1ac42fbd4cd9c89dc9a988228d8a2639a58e6c"
NATIVE = "Ghidra/Features/Decompiler/build/os/mac_arm_64/decompile"


def natives_entry():
    return {"id": "ghidra-natives", "version": "1", "folder": "ghidra-12.2", "required": True,
            "only": ["macos"], "post": "ghidra-natives", "jdk_folder": "jdk-25",
            "gradle": {"url": GRADLE_URL, "sha256": GRADLE_SHA, "sha256_source": "publisher-checksum-file"},
            "detect": {"macos": ["Ghidra/Features/Decompiler/build/os/mac_*/decompile"]}}


class GhidraNativesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self._tmp.name, "tools")
        self.ghidra = os.path.join(self.root, "ghidra-12.2")
        self.props = os.path.join(self.ghidra, "support", "gradle", "gradle-wrapper.properties")
        os.makedirs(os.path.dirname(self.props))
        with open(os.path.join(self.ghidra, "support", "gradle", "gradlew"), "w") as f:
            f.write("#!/bin/sh\n")
        with open(self.props, "w") as f:
            f.write("distributionUrl=https\\://services.gradle.org/distributions/gradle-9.8.0-bin.zip\n")
        java = os.path.join(self.root, "jdk-25", "Contents", "Home", "bin", "java")
        os.makedirs(os.path.dirname(java))
        open(java, "w").close()
        self.calls = []

    def tearDown(self):
        self._tmp.cleanup()

    def runner(self, build_ok=True, xcode_ok=True):
        def run(argv):
            self.calls.append(argv)
            if argv[0] == "xcode-select":
                return (0 if xcode_ok else 2), "/Library/Developer/CommandLineTools"
            if "buildNatives" in argv and build_ok:
                p = os.path.join(self.ghidra, *NATIVE.split("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w").close()
            return (0 if build_ok else 1), "BUILD FAILED" if not build_ok else "BUILD SUCCESSFUL"
        return run

    def ensure(self, runner, check=False, platform="macos"):
        return ensure_tools.ensure(self.root, {"schema": 1, "tools": [natives_entry()]}, check=check,
                                   fetch=FakeFetch({}), platform=platform, runner=runner)["tools"]

    def test_builds_natives_with_pinned_gradle_inside_tool_root(self):
        t = self.ensure(self.runner())["ghidra-natives"]
        self.assertEqual(t["status"], "installed", t)
        build = next(c for c in self.calls if "buildNatives" in c)
        self.assertIn("JAVA_HOME=" + os.path.join(self.root, "jdk-25", "Contents", "Home"), build)
        self.assertIn("GRADLE_USER_HOME=" + os.path.join(self.root, "gradle-home"), build)
        with open(self.props) as f:
            self.assertIn("distributionSha256Sum=" + GRADLE_SHA, f.read())

    def test_present_when_natives_exist(self):
        self.runner()(["x", "buildNatives"])
        self.calls.clear()
        t = self.ensure(self.runner())["ghidra-natives"]
        self.assertEqual(t["status"], "present")
        self.assertEqual(self.calls, [])

    def test_check_mode_never_builds(self):
        t = self.ensure(self.runner(), check=True)["ghidra-natives"]
        self.assertEqual(t["status"], "failed")
        self.assertEqual(self.calls, [])

    def test_missing_command_line_tools_is_a_manual_stop(self):
        t = self.ensure(self.runner(xcode_ok=False))["ghidra-natives"]
        self.assertEqual(t["status"], "manual")
        self.assertTrue(t["detail"].startswith("stop: hand to the user"))
        self.assertIn("xcode-select --install", t["detail"])
        self.assertFalse(any("buildNatives" in c for c in self.calls))

    def test_build_failure_is_reported(self):
        t = self.ensure(self.runner(build_ok=False))["ghidra-natives"]
        self.assertEqual(t["status"], "failed")
        self.assertIn("BUILD FAILED", t["detail"])

    def test_ghidra_not_installed_fails_without_building(self):
        import shutil
        shutil.rmtree(self.ghidra)
        t = self.ensure(self.runner())["ghidra-natives"]
        self.assertEqual(t["status"], "failed")
        self.assertFalse(any("buildNatives" in c for c in self.calls))
        self.assertFalse(os.path.exists(self.ghidra))

    def test_gradle_url_mismatch_refuses_to_build(self):
        with open(self.props, "w") as f:
            f.write("distributionUrl=https\\://services.gradle.org/distributions/gradle-9.9.0-bin.zip\n")
        t = self.ensure(self.runner())["ghidra-natives"]
        self.assertEqual(t["status"], "failed")
        self.assertIn("gradle-9.9.0", t["detail"])
        self.assertFalse(any("buildNatives" in c for c in self.calls))

    def test_skipped_on_other_platforms(self):
        for plat in ("windows", "linux"):
            self.assertNotIn("ghidra-natives", self.ensure(self.runner(), platform=plat))

    def test_shipped_manifest_has_macos_natives_entry_after_jdk_and_ghidra(self):
        m = ensure_tools.load_manifest(ensure_tools.MANIFEST_PATH)
        ids = [t["id"] for t in m["tools"]]
        self.assertLess(ids.index("jdk"), ids.index("ghidra-natives"))
        self.assertLess(ids.index("ghidra"), ids.index("ghidra-natives"))
        e = m["tools"][ids.index("ghidra-natives")]
        self.assertEqual(e["only"], ["macos"])
        self.assertEqual(e["gradle"]["sha256"], GRADLE_SHA)


if __name__ == "__main__":
    unittest.main()
