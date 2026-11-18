#!/usr/bin/env python3
"""Probe how an extracted level/config blob is encoded.

Tries, recursively up to --max-depth transforms: UTF-8 BOM strip, Unity aligned
string (int32 length prefix), base64, gzip, zlib, raw deflate, brotli (only if the
optional `brotli` module imports), and a JSON parse. Prints one JSON object:

  {"chain": [...], "result": "json|text|binary|undecoded", "preview": str,
   "sha256_raw": str, "sha256_decoded": str|null, "warnings": [str]}

"json" is reported only when json.loads succeeded and returned an object or array.
--out writes the decoded bytes only for a "json" result.
Exit codes: 0 probe ran (any result), 1 error (for example, file not found).
Python 3 standard library only; brotli is optional.
"""
import argparse
import base64
import binascii
import gzip
import hashlib
import json
import re
import struct
import sys
import zlib

try:
    import brotli
except ImportError:
    brotli = None

BOM = b"\xef\xbb\xbf"
B64_RE = re.compile(rb"^[A-Za-z0-9+/]+={0,2}$")
B64URL_RE = re.compile(rb"^[A-Za-z0-9_-]+={0,2}$")
WS = b" \t\r\n"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def as_text(data):
    """Return str if data looks like printable UTF-8 text, else None."""
    if not data:
        return None
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    printable = sum(1 for c in s if c.isprintable() or c in "\r\n\t")
    return s if printable >= 0.95 * len(s) else None


def try_json(data):
    """Return (True, value) when data is UTF-8 JSON, else (False, None)."""
    try:
        return True, json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False, None


def t_bom(data, warn):
    return data[len(BOM):] if data.startswith(BOM) else None


def t_aligned(data, warn):
    if len(data) < 5:
        return None
    n = struct.unpack_from("<i", data, 0)[0]
    if n <= 0 or 4 + n > len(data):
        return None
    tail = data[4 + n:]
    if len(tail) > 3 or tail.strip(b"\0"):
        warn.add("aligned-string-trailing-bytes:%d" % len(tail))
    return data[4:4 + n]


def _b64(data, pattern, altchars):
    s = data.strip(WS)
    if len(s) < 4 or not pattern.match(s):
        return None
    s += b"=" * (-len(s) % 4)
    try:
        out = base64.b64decode(s, altchars=altchars, validate=True)
    except (binascii.Error, ValueError):
        return None
    return out or None


def t_base64(data, warn):
    return _b64(data, B64_RE, None)


def t_base64url(data, warn):
    s = data.strip(WS)
    if not (b"-" in s or b"_" in s):
        return None
    return _b64(data, B64URL_RE, b"-_")


def t_gzip(data, warn):
    if not data.startswith(b"\x1f\x8b"):
        return None
    try:
        return gzip.decompress(data) or None
    except (OSError, EOFError, zlib.error):
        return None


def t_zlib(data, warn):
    if len(data) < 2 or data[0] & 0x0F != 8 or ((data[0] << 8) | data[1]) % 31:
        return None
    try:
        return zlib.decompress(data) or None
    except zlib.error:
        return None


def t_raw_deflate(data, warn):
    d = zlib.decompressobj(-15)
    try:
        out = d.decompress(data) + d.flush()
    except zlib.error:
        return None
    if not d.eof or d.unused_data or d.unconsumed_tail:
        return None
    return out or None


def t_brotli(data, warn):
    if brotli is None:
        return None
    try:
        return brotli.decompress(data) or None
    except Exception:  # brotli raises its own error type
        return None


def t_json_string(data, warn):
    ok, value = try_json(data)
    if ok and isinstance(value, str) and value:
        return value.encode("utf-8")
    return None


TRANSFORMS = [
    ("utf8-bom", t_bom),
    ("json-string", t_json_string),
    ("unity-aligned-string", t_aligned),
    ("gzip", t_gzip),
    ("zlib", t_zlib),
    ("raw-deflate", t_raw_deflate),
    ("base64", t_base64),
    ("base64url", t_base64url),
    ("brotli", t_brotli),
]


class Search:
    def __init__(self, max_depth):
        self.max_depth = max_depth
        self.warn = set()  # global warnings, independent of the chosen chain
        self.endpoints = []  # (chain, data, step_warnings) for every non-JSON node reached
        self.seen = {}

    def run(self, data, chain, warns):
        """Depth-first search; return (chain, data, value, warns) on the first JSON hit."""
        ok, value = try_json(data)
        if ok and isinstance(value, (dict, list)):
            return chain + ["json"], data, value, warns
        key = sha256(data)
        remaining = self.max_depth - len(chain)
        if self.seen.get(key, -1) >= remaining:
            return None
        self.seen[key] = remaining
        self.endpoints.append((chain, data, warns))
        for name, fn in TRANSFORMS:
            local = set()
            out = fn(data, local)
            if out is None or out == data:
                continue
            if remaining <= 0:
                self.warn.add("max-depth")
                break
            hit = self.run(out, chain + [name], warns | local)
            if hit:
                return hit
        return None


def preview_bytes(data, limit=200):
    text = as_text(data)
    if text is not None:
        return text[:limit]
    return data[:64].hex()


def probe(raw, max_depth):
    search = Search(max_depth)
    if brotli is None:
        search.warn.add("brotli-unavailable")
    if not raw:
        search.warn.add("empty-input")
        return {"chain": [], "result": "undecoded", "preview": "", "sha256_raw": sha256(raw),
                "sha256_decoded": None, "warnings": sorted(search.warn)}, None
    hit = search.run(raw, [], frozenset())
    if hit:
        chain, data, value, warns = hit
        result = "json"
        preview = json.dumps(value, ensure_ascii=False)[:200]
        search.warn.discard("max-depth")  # the limit did not prevent a JSON result
    else:
        text_ends = [e for e in search.endpoints if as_text(e[1]) is not None]
        bin_ends = [e for e in search.endpoints if e[0]]
        if text_ends:
            chain, data, warns = max(text_ends, key=lambda e: len(e[0]))
            result = "text"
        elif bin_ends:
            chain, data, warns = max(bin_ends, key=lambda e: len(e[0]))
            result = "binary"
        else:
            chain, data, warns = [], None, frozenset()
            result = "undecoded"
        preview = preview_bytes(data if data is not None else raw)
        if result == "text" and try_json(data)[0]:
            warns = warns | {"json-scalar"}  # parses as JSON, but not an object or array
    out = {
        "chain": chain,
        "result": result,
        "preview": preview,
        "sha256_raw": sha256(raw),
        "sha256_decoded": sha256(data) if data is not None else None,
        "warnings": sorted(search.warn | warns),
    }
    return out, data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--max-depth", type=int, default=6, help="maximum number of decode transforms (default 6)")
    ap.add_argument("--out", help="for a json result only: write the decoded bytes here unchanged "
                                  "(so sha256_decoded matches); otherwise nothing is written")
    a = ap.parse_args(argv)
    try:
        with open(a.file, "rb") as f:
            raw = f.read()
        out, data = probe(raw, max(0, a.max_depth))
        if a.out:
            if out["result"] == "json":
                with open(a.out, "wb") as f:
                    f.write(data)
                out["out"] = a.out
            else:
                out["out"] = None
                out["warnings"] = sorted(out["warnings"] + ["out-not-written:" + out["result"]])
    except Exception as e:  # report, don't crash with a traceback
        print(json.dumps({"error": "%s: %s" % (type(e).__name__, e)}))
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
