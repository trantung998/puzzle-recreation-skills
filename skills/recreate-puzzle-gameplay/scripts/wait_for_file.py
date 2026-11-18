#!/usr/bin/env python3
"""Block once until a file exists and its size is stable, or a timeout passes.

Usage: python3 wait_for_file.py --path FILE --timeout SECONDS [--min-size BYTES] [--interval SECONDS]

The harness-neutral wait for an asynchronous receipt when the harness has no background or
monitor mechanism: one foreground call, a bounded poll inside the script. "Found" means the
file exists, is at least --min-size bytes (default 1) and has the same size on two
consecutive polls. Prints JSON {"status": "found"|"timeout", "path", "size", "waited_seconds"}.
Exit codes: 0 found, 4 timeout, 2 usage error.
"""
import argparse
import json
import os
import sys
import time


def non_negative(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("%r is not a number" % text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be 0 or more, got %s" % text)
    return value


def positive(text):
    value = non_negative(text)
    if value == 0:
        raise argparse.ArgumentTypeError("must be more than 0")
    return value


def size_of(path):
    try:
        return os.path.getsize(path) if os.path.isfile(path) else None
    except OSError:
        return None


def wait(path, timeout, min_size, interval):
    start = time.monotonic()
    deadline = start + timeout
    last = None
    while True:
        size = size_of(path)
        if size is not None and size >= min_size and size == last:
            return "found", size, time.monotonic() - start
        last = size
        now = time.monotonic()
        if now >= deadline:
            return "timeout", size, now - start
        time.sleep(min(interval, max(0.0, deadline - now)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", required=True, help="file to wait for")
    parser.add_argument("--timeout", required=True, type=non_negative, help="seconds before giving up")
    parser.add_argument("--min-size", type=int, default=1, help="minimum size in bytes (default 1)")
    parser.add_argument("--interval", type=positive, default=2.0, help="seconds between polls (default 2)")
    args = parser.parse_args(argv)
    if args.min_size < 0:
        parser.error("--min-size must be 0 or more")
    path = os.path.abspath(args.path)
    status, size, waited = wait(path, args.timeout, args.min_size, args.interval)
    print(json.dumps({"status": status, "path": path, "size": size, "waited_seconds": round(waited, 3)}, indent=2))
    return 0 if status == "found" else 4


if __name__ == "__main__":
    sys.exit(main())
