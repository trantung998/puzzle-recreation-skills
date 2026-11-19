#!/usr/bin/env python3
"""Detect and install the pinned decompile tools for puzzle-gameplay recreation.

Usage: python3 ensure_tools.py [--check] [--root DIR] [--progress WORKDIR]

Prints JSON {"root": ..., "tools": {id: {status, version, path, detail}}}.
status: present | installed | failed | manual. Exit codes: 0 all required tools
present/installed, 3 any required tool failed/manual, 1 usage or I/O error.
--check never downloads or creates anything.
"""
import argparse
import glob
import hashlib
import json
import os
import platform as _platform
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import urllib.error
import urllib.request
import zipfile

PARKINGLOOP_TOOLS = "H:/UGame/ParkingLoop/tools"
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools-manifest.json")
MAX_EXTRACT_BYTES = 8 * 1024 ** 3
SHA_SOURCES = ("local-file", "publisher-api", "publisher-checksum-file")
SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VENV_POSTS = ("venv-pyyaml", "venv")


def cache_root():
    return os.path.join(os.path.expanduser("~"), ".cache", "puzzle-recreation", "tools")


def resolve_root():
    env = os.environ.get("UNITY_DECOMPILE_TOOLS")
    if env:
        return os.path.abspath(env)
    if os.path.isdir(PARKINGLOOP_TOOLS):
        return PARKINGLOOP_TOOLS
    return cache_root()


def detect_platform():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("schema") != 1 or not isinstance(manifest.get("tools"), list):
        raise ValueError("manifest: expected {'schema': 1, 'tools': [...]}")
    seen = set()
    for tool in manifest["tools"]:
        if tool["id"] in seen:
            raise ValueError("manifest: duplicate id " + tool["id"])
        seen.add(tool["id"])
        for key, src in tool.items():
            if isinstance(src, dict) and "url" in src:
                sha = src.get("sha256")
                if not sha:
                    raise ValueError("manifest: %s/%s has a url but no sha256" % (tool["id"], key))
                if not isinstance(sha, str) or not SHA_RE.match(sha):
                    raise ValueError("manifest: bad sha256 for %s/%s" % (tool["id"], key))
                source = src.get("sha256_source")
                if (sha is None) != (source is None) or (source is not None and source not in SHA_SOURCES):
                    raise ValueError("manifest: sha256 needs a valid sha256_source for %s/%s" % (tool["id"], key))
        if "min_python" in tool:
            mp = tool["min_python"]
            if not (isinstance(mp, list) and len(mp) == 2 and all(isinstance(x, int) for x in mp)):
                raise ValueError("manifest: %s min_python must be [major, minor]" % tool["id"])
        if tool.get("post") in VENV_POSTS:
            pins = tool.get("pip")
            if not pins or not all(isinstance(p, str) and re.match(r"^[A-Za-z0-9_.\-]+==[A-Za-z0-9_.!+\-]+$", p)
                                   for p in pins):
                raise ValueError("manifest: %s needs an exact-pinned 'pip' list (name==version)" % tool["id"])
    return manifest


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rmtree(path):
    if not os.path.lexists(path):
        return

    def fix(func, p, *_):
        os.chmod(p, 0o700)
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=fix)
    else:
        shutil.rmtree(path, onerror=fix)


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


class HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise urllib.error.URLError("refusing redirect to non-https url: " + newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_opener():
    return urllib.request.build_opener(HttpsOnlyRedirectHandler)


def default_fetch(url, dest):
    if not url.lower().startswith("https://"):
        raise ValueError("refusing non-https url: " + url)
    req = urllib.request.Request(url, headers={"User-Agent": "recreate-puzzle-gameplay/ensure_tools"})
    with make_opener().open(req, timeout=60) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)


def default_runner(argv):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=1800)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def tail(out):
    return out[-500:]


class UnsafeArchive(Exception):
    pass


def safe_relpath(name):
    n = name.replace("\\", "/")
    parts = n.split("/")
    if (not n or "\0" in n or n.startswith("/") or re.match(r"^[A-Za-z]:", n)
            or ".." in parts or any(":" in p for p in parts)):
        raise UnsafeArchive("unsafe archive member: %r" % name)
    return n.rstrip("/")


def contained(dest_real, rel):
    target = os.path.realpath(os.path.join(dest_real, rel))
    if os.path.commonpath([dest_real, target]) != dest_real:
        raise UnsafeArchive("archive member escapes destination: %r" % rel)
    return target


def _norm_name(path):
    """The one component walk shared by every check: unify separators, drop "" and "." (keep "..").
    tarfile extracts "./x", "a//x" and "a/./x" at "x" / "a/x", so they must compare equal."""
    return "/".join(p for p in path.replace("\\", "/").split("/") if p not in ("", "."))


def _fs_key(path):
    """Compare names the way extraction and case- and normalization-insensitive filesystems (macOS,
    Windows) do."""
    return unicodedata.normalize("NFC", _norm_name(path)).casefold()


def _crosses(path, keys):
    parts = path.replace("\\", "/").split("/")
    stack = []
    for i, part in enumerate(parts):
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                return True
            stack.pop()
            continue
        stack.append(part)
        if i < len(parts) - 1 and _fs_key("/".join(stack)) in keys:
            return True
    return False


def crosses_symlink(path, symlinks):
    """True if resolving archive-relative `path` would follow a symlink in `symlinks` before its last
    component, or climb above the archive root. Lexical checks such as contained() cannot see
    symlinks that only exist once the archive is extracted (e.g. x -> . then x/y -> ..)."""
    return _crosses(path, {_fs_key(s) for s in symlinks})


def extract_zip(archive, dest):
    os.makedirs(dest)
    dest_real = os.path.realpath(dest)
    total = 0
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        plan = []
        for info in infos:
            rel = safe_relpath(info.filename)
            mode = info.external_attr >> 16
            if (mode & 0o170000) == 0o120000:
                raise UnsafeArchive("symlink in zip: %r" % info.filename)
            plan.append((info, rel, contained(dest_real, rel)))
        for info, rel, target in plan:
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_EXTRACT_BYTES:
                        raise UnsafeArchive("archive expands beyond size limit")
                    out.write(chunk)
            perm = (info.external_attr >> 16) & 0o777
            if perm and os.name != "nt":
                os.chmod(target, perm | 0o600)


def extract_tar(archive, dest):
    os.makedirs(dest)
    dest_real = os.path.realpath(dest)
    with tarfile.open(archive, "r:*") as tf:
        members = tf.getmembers()
        symlinks = set()
        for m in members:
            if m.issym():
                name = _norm_name(safe_relpath(m.name))
                if not name:
                    raise UnsafeArchive("symlink at the archive root: %r" % m.name)
                symlinks.add(_fs_key(name))
        total = 0
        for m in members:
            rel = _norm_name(safe_relpath(m.name))
            contained(dest_real, rel)
            if _crosses(rel, symlinks):
                raise UnsafeArchive("archive member passes through a symlink: %r" % m.name)
            if m.isdir() or m.isreg():
                total += m.size
            elif m.issym():
                link = m.linkname.replace("\\", "/")
                if link.startswith("/") or re.match(r"^[A-Za-z]:", link):
                    raise UnsafeArchive("absolute symlink: %r" % m.name)
                contained(dest_real, os.path.join(os.path.dirname(rel), link))
                if _crosses(posixpath.join(posixpath.dirname(rel), link), symlinks):
                    raise UnsafeArchive("symlink target passes through a symlink: %r" % m.name)
            elif m.islnk():
                target = _norm_name(safe_relpath(m.linkname))
                contained(dest_real, target)
                if _crosses(target, symlinks):
                    raise UnsafeArchive("hardlink target passes through a symlink: %r" % m.name)
            else:
                raise UnsafeArchive("unsupported tar member type: %r" % m.name)
        if total > MAX_EXTRACT_BYTES:
            raise UnsafeArchive("archive expands beyond size limit")
        if hasattr(tarfile, "data_filter"):
            tf.extractall(dest, members=members, filter="data")
        else:
            tf.extractall(dest, members=members)


def extract(archive, kind, dest):
    if kind in ("zip", "nupkg"):
        extract_zip(archive, dest)
    elif kind in ("tar.gz", "tar.xz"):
        extract_tar(archive, dest)
    else:
        raise ValueError("unknown archive type: " + kind)


def strip_single_top_dir(partial):
    entries = os.listdir(partial)
    if len(entries) != 1:
        return
    sub = os.path.join(partial, entries[0])
    if os.path.islink(sub) or not os.path.isdir(sub):
        return
    tmp = partial + ".strip"
    rmtree(tmp)
    os.rename(sub, tmp)
    os.rmdir(partial)
    os.rename(tmp, partial)


def detect_list(tool, platform):
    d = tool.get("detect") or []
    if isinstance(d, dict):
        return d.get(platform, [])
    return d


def detect_exists(base, rel):
    if any(c in rel for c in "*?["):
        return bool(glob.glob(os.path.join(glob.escape(base), *rel.split("/"))))
    return os.path.exists(os.path.join(base, *rel.split("/")))


def folder_is_complete(base, tool, platform):
    paths = detect_list(tool, platform)
    return bool(paths) and all(detect_exists(base, p) for p in paths)


def detect_arch():
    return "arm64" if _platform.machine().lower() in ("arm64", "aarch64") else "x64"


def pick_source(tool, platform, arch):
    key = platform
    if platform in ("linux", "macos") and not tool.get("neutral") and arch == "arm64":
        key = platform + "-arm64"
    return tool.get(key), key


def result(status, tool, path, detail):
    return {"status": status, "version": tool.get("version", ""), "path": path, "detail": detail}


def runtime_versions(path, name, runner):
    """Versions of runtime `name` listed by `<dotnet> --list-runtimes`."""
    try:
        rc, out = runner([path, "--list-runtimes"])
    except Exception:
        return []
    return re.findall(r"^%s (\d+\.\S+)" % re.escape(name), out or "", re.M) if rc == 0 else []


def detect_command_tool(tool, platform, root, runner):
    candidates = []
    found = shutil.which(tool["detect_command"]) if tool.get("detect_command") else None
    if found and not (platform == "windows" and "\\windows\\system32\\" in found.lower().replace("/", "\\")):
        candidates.append(found)
    for p in (tool.get("detect_extra") or {}).get(platform, []):
        p = os.path.normpath(os.path.expandvars(os.path.expanduser(p)).replace("{root}", root))
        if os.path.isfile(p) and os.path.normcase(p) not in {os.path.normcase(os.path.normpath(c)) for c in candidates}:
            candidates.append(p)
    need = tool.get("min_runtime")
    seen = []
    for p in candidates:
        if not need:
            return result("present", tool, p, "found on this machine")
        versions = runtime_versions(p, need["name"], runner)
        if any(int(v.split(".")[0]) >= need["major"] for v in versions):
            return result("present", tool, p, "found on this machine with %s %s" % (need["name"], ", ".join(versions)))
        seen.append("%s (%s)" % (p, ", ".join(versions) or "no %s" % need["name"]))
    # manual hints are user-scope stop instructions; the agent never runs them itself
    hint = (tool.get("manual") or {}).get(platform, "stop: hand to the user \u2014 see the tool's official download page")
    if seen:
        why = "No %s %d+ (found %s). " % (need["name"], need["major"], "; ".join(seen))
    else:
        why = "Not found. "
    return result("manual", tool, "", why + hint.replace("{root}", root))


def install_venv(tool, final, platform, runner):
    if os.path.exists(final):
        return result("failed", tool, final, "folder exists but is incomplete; delete it and re-run: " + final)
    need = tool.get("min_python")
    if need and tuple(sys.version_info[:2]) < tuple(need):
        return result("failed", tool, final, (
            "needs Python >= %d.%d to create this venv (this is %d.%d at %s); re-run ensure_tools.py "
            "with a newer python3 (macOS: Homebrew /opt/homebrew/bin/python3 or the python.org "
            "installer; the Xcode /usr/bin/python3 is 3.9)") % (
            need[0], need[1], sys.version_info[0], sys.version_info[1], sys.executable))
    try:
        rc, out = runner([sys.executable, "-m", "venv", final])
        if rc != 0:
            raise RuntimeError("venv creation failed: " + tail(out))
        sub = ("Scripts", "python.exe") if platform == "windows" else ("bin", "python")
        pins = tool.get("pip") or []
        if not pins or not all("==" in p for p in pins):
            raise RuntimeError("manifest has no exact-pinned 'pip' list")
        rc, out = runner([os.path.join(final, *sub), "-m", "pip", "install", *pins])
        if rc != 0:
            raise RuntimeError("pip install %s failed: %s" % (" ".join(pins), tail(out)))
        if not folder_is_complete(final, tool, platform):
            raise RuntimeError("venv missing expected files")
    except Exception as e:
        rmtree(final)
        return result("failed", tool, final, str(e))
    return result("installed", tool, final, "venv created with %s; pip installed %s" % (
        sys.executable, ", ".join(pins)))


def post_exec_bits(folder, tool, platform):
    """Release zips built on CI can store native executables without the exec bit."""
    for rel in tool.get("exec") or []:
        if platform == "windows":
            rel += ".exe"
        path = os.path.join(folder, *rel.split("/"))
        if not os.path.isfile(path):
            raise RuntimeError("archive layout unexpected: missing executable " + rel)
        if os.name != "nt":
            os.chmod(path, os.stat(path).st_mode | 0o755)


def build_ghidra_natives(tool, final, root, platform, runner):
    """Ghidra release zips ship decompiler binaries for linux_x86_64 and win_x86_64 only.

    On macOS, build them in place with Ghidra's own Gradle wrapper (support/gradle), using the
    pinned JDK from the tool root, a sha256-pinned Gradle distribution and a GRADLE_USER_HOME
    inside the tool root. Needs the Xcode Command Line Tools (clang) and network access.
    """
    gradle_dir = os.path.join(final, "support", "gradle")
    gradlew = os.path.join(gradle_dir, "gradlew")
    props = os.path.join(gradle_dir, "gradle-wrapper.properties")
    if not (os.path.isfile(gradlew) and os.path.isfile(props)):
        return result("failed", tool, final, "Ghidra is not installed at %s (support/gradle missing); "
                      "install the ghidra entry first" % final)
    jdk = os.path.join(root, tool.get("jdk_folder", "jdk-25"))
    if platform == "macos":
        jdk = os.path.join(jdk, "Contents", "Home")
    if not os.path.isfile(os.path.join(jdk, "bin", "java")):
        return result("failed", tool, final, "pinned JDK missing at %s; install the jdk entry first" % jdk)
    gradle = tool.get("gradle") or {}
    if platform == "macos":
        rc, _ = runner(["xcode-select", "-p"])
        if rc != 0:
            return result("manual", tool, final, "stop: hand to the user — install the Xcode Command Line "
                          "Tools (C/C++ compiler for Ghidra's decompiler): xcode-select --install ; "
                          "then re-run ensure_tools.py")
    with open(props, encoding="utf-8") as f:
        lines = f.read().splitlines()
    url_line = next((l for l in lines if l.startswith("distributionUrl=")), "")
    url = url_line.split("=", 1)[1].replace("\\:", ":") if url_line else ""
    if url != gradle.get("url"):
        return result("failed", tool, final, "Ghidra's Gradle wrapper wants %r but the manifest pins %r; "
                      "refusing an unpinned download" % (url, gradle.get("url")))
    lines = [l for l in lines if not l.startswith("distributionSha256Sum=")]
    lines.append("distributionSha256Sum=" + gradle["sha256"])
    with open(props, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    rc, out = runner(["/usr/bin/env", "JAVA_HOME=" + jdk, "GRADLE_USER_HOME=" + os.path.join(root, "gradle-home"),
                      "bash", gradlew, "-p", gradle_dir, "--no-daemon", "buildNatives"])
    if rc != 0:
        return result("failed", tool, final, "gradlew buildNatives failed: " + tail(out))
    if not folder_is_complete(final, tool, platform):
        return result("failed", tool, final, "buildNatives finished but %s is missing"
                      % ", ".join(detect_list(tool, platform)))
    return result("installed", tool, final, "decompiler natives built with Gradle from %s (sha256 %s pinned)"
                  % (gradle["url"], gradle["sha256"]))


def install_archive(tool, root, platform, fetch, src):
    folder = tool["folder"]
    final = os.path.join(root, folder)
    partial = final + ".partial"
    strip = partial + ".strip"
    downloads = os.path.join(root, "downloads")
    archive = os.path.join(downloads, "%s.%s" % (folder, src["archive"]))
    url = src["url"]
    if not isinstance(url, str) or not url.lower().startswith("https://"):
        return result("failed", tool, final, "refusing non-https url: %s" % url)
    want = src.get("sha256")
    if not want:
        return result("failed", tool, final, "no pinned sha256 for %s; refusing an unverified download" % url)
    if os.path.exists(final):
        return result("failed", tool, final, "folder exists but is incomplete; delete it and re-run: " + final)
    ok = False
    try:
        os.makedirs(downloads, exist_ok=True)
        rmtree(partial)
        rmtree(strip)
        remove_file(archive)
        fetch(url, archive)
        digest = sha256_file(archive)
        if digest.lower() != want.lower():
            raise RuntimeError("sha256 mismatch for %s: expected %s, got %s" % (url, want.lower(), digest))
        extract(archive, src["archive"], partial)
        strip_single_top_dir(partial)
        if tool.get("post") == "exec-bits":
            post_exec_bits(partial, tool, platform)
        if not folder_is_complete(partial, tool, platform):
            raise RuntimeError("archive layout unexpected: missing %s" % ", ".join(detect_list(tool, platform)))
        os.rename(partial, final)
        ok = True
    except Exception as e:
        return result("failed", tool, final, "%s: %s" % (type(e).__name__, e))
    finally:
        remove_file(archive)
        rmtree(strip)
        if not ok:
            rmtree(partial)
        try:
            os.rmdir(downloads)
        except OSError:
            pass
    return result("installed", tool, final, "from %s; sha256=%s (verified against manifest)" % (url, digest))


def process_tool(tool, root, platform, check, fetch, runner, arch):
    if not tool.get("folder"):
        return detect_command_tool(tool, platform, root, runner)
    folder = tool["folder"]
    if folder in (".", "..") or re.search(r"[\\/:\0]", folder):
        return result("failed", tool, "", "manifest folder must be a plain directory name: %r" % folder)
    final = os.path.join(root, folder)
    if folder_is_complete(final, tool, platform):
        return result("present", tool, final, "all expected files exist")
    if check:
        return result("failed", tool, final, "missing: %s (--check does not download; re-run without --check)"
                      % ", ".join(detect_list(tool, platform)))
    if tool.get("post") == "ghidra-natives":
        return build_ghidra_natives(tool, final, root, platform, runner)
    os.makedirs(root, exist_ok=True)
    if tool.get("post") in VENV_POSTS:
        return install_venv(tool, final, platform, runner)
    src, key = pick_source(tool, platform, arch)
    if not src:
        return result("failed", tool, final, "no pinned download for platform " + key)
    return install_archive(tool, root, platform, fetch, src)


def ensure(root, manifest, check=False, fetch=None, platform=None, runner=None, arch=None):
    platform = platform or detect_platform()
    arch = arch or detect_arch()
    fetch = fetch or default_fetch
    runner = runner or default_runner
    tools = {}
    for tool in manifest["tools"]:
        if tool.get("only") and platform not in tool["only"]:
            continue
        try:
            tools[tool["id"]] = process_tool(tool, root, platform, check, fetch, runner, arch)
        except Exception as e:
            tools[tool["id"]] = result("failed", tool, "", "%s: %s" % (type(e).__name__, e))
    return {"root": root, "tools": tools}


def exit_code(res, manifest):
    required = {t["id"]: t.get("required", True) for t in manifest["tools"]}
    bad = [i for i, t in res["tools"].items()
           if t["status"] in ("failed", "manual") and required.get(i, True)]
    return 3 if bad else 0


def write_progress(workdir, tools):
    path = os.path.join(workdir, "progress.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["tools"] = tools
    fd, tmp = tempfile.mkstemp(dir=workdir, prefix=".progress-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        remove_file(tmp)
        raise


def main(argv=None, fetch=None, runner=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="detect only; never download")
    ap.add_argument("--root", help="tool directory (default: $UNITY_DECOMPILE_TOOLS, ParkingLoop tools, cache)")
    ap.add_argument("--progress", metavar="WORKDIR", help="write the result into WORKDIR/progress.json")
    ap.add_argument("--manifest", default=MANIFEST_PATH, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        root = os.path.abspath(args.root) if args.root else resolve_root()
        res = ensure(root, manifest, check=args.check, fetch=fetch, runner=runner)
        code = exit_code(res, manifest)
        print(json.dumps(res, indent=2))
        if args.progress:
            write_progress(args.progress, res["tools"])
    except (OSError, ValueError, KeyError) as e:
        print("ensure_tools: error: %s" % e, file=sys.stderr)
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
