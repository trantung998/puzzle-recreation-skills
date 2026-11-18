#!/usr/bin/env python3
"""Print a class from dump.cs: base class, fields with offsets, methods with RVA.

Reads both layouts: Il2CppInspectorRedux C# (run_il2cppinspector.sh writes it as dump.cs;
method address range in a trailing `// 0xSTART-0xEND`) and Il2CppDumper's dump.cs
(`// RVA: 0x...` line above each method).

Usage:
  python3 -I dump_class.py <dump.cs> <ClassName> [--methods REGEX] [--bases]
    --bases   also print each base class (inherited fields live at lower offsets)
  python3 -I dump_class.py <dump.cs> --offset <ClassName> 0x1c   # which field is at 0x1c (walks bases)

Use it to turn `*(param_1 + 0x1c)` into a field name: param_1 is `this` of the method's class.
Inspector escapes compiler names: `<Seed>k__BackingField` -> `_Seed_k__BackingField`,
nested `<Load>d__5` -> `_Load_d__5`.
"""
import re
import sys
from pathlib import Path

CLS = re.compile(r"^\s*(?:\[.*\]\s*)?(?:(?:public|private|internal|protected|sealed|abstract|static|readonly|ref|unsafe)\s+)*"
                 r"(?:class|struct|enum|interface)\s+([^\s:<]+(?:<[^>]*>)?)\s*(?::\s*([^{/]+))?")
NS = re.compile(r"^namespace\s+(\S+)")
FIELD = re.compile(r"^\s*(.*?);\s*//\s*(0x[0-9A-Fa-f]+)\s*$")
RANGE = re.compile(r"//\s*(0x[0-9A-Fa-f]+)-0x[0-9A-Fa-f]+")


def find(lines, name):
    out = []
    ns = ""
    for i, l in enumerate(lines):
        n = NS.match(l)
        if n:
            ns = "// Namespace: " + n.group(1)
            continue
        if l.startswith("}"):  # end of a top-level namespace block
            ns = ""
        m = CLS.match(l)
        if m and (m.group(1) == name or m.group(1).split("<")[0] == name):
            j, depth, started = i, 0, False
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                started |= "{" in lines[j]
                if started and depth <= 0:
                    break
                j += 1
            here = lines[i - 1] if i and lines[i - 1].startswith("// Namespace") else ns
            out.append((here, m.group(1), (m.group(2) or "").strip(), lines[i:j + 1]))
    return out


def own_lines(block):
    """(index, line) of members that belong to this class, skipping nested type bodies."""
    depth = 0
    for k, l in enumerate(block):
        if depth == 1 and k:
            yield k, l
        depth += l.count("{") - l.count("}")


def fields(block):
    res = []
    for _, l in own_lines(block):
        m = FIELD.search(l)
        if m and "(" not in m.group(1) and not CLS.match(l):
            res.append((int(m.group(2), 16), m.group(1).strip()))
    return res


def methods(block):
    res = []
    for k, l in own_lines(block):
        m = re.search(r"RVA: (0x[0-9A-Fa-f]+)", l)
        if m and k + 1 < len(block):
            res.append((m.group(1), block[k + 1].strip()))
            continue
        m = RANGE.search(l)
        if m:
            sig, comment = l.split("//", 1)
            extra = re.findall(r"(0x[0-9A-Fa-f]+)-0x", comment)
            tail = "  // " + ", ".join(extra) if len(extra) > 1 else ""
            res.append((m.group(1), sig.strip() + tail))
    return res


def base_name(b):
    b = b.split(",")[0].strip()
    return b.split("<")[0] if b else ""


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    lines = Path(a[0]).read_text(encoding="utf-8", errors="replace").splitlines()
    if a[1] == "--offset":
        name, off = a[2], int(a[3], 16)
        while name:
            hits = find(lines, name)
            if not hits:
                print(f"{name}: not found")
                return 1
            _, n, b, block = hits[0]
            for o, decl in fields(block):
                if o == off and "static" not in decl and "const" not in decl:
                    print(f"{n}+{hex(off)}: {decl}")
                    return 0
            name = base_name(b)
        print("no field at that offset (check the base chain / generic base)")
        return 1
    name = a[1]
    rx = re.compile(a[a.index("--methods") + 1], re.I) if "--methods" in a else None
    todo, seen = [name], set()
    while todo:
        n = todo.pop(0)
        if n in seen or n in ("", "object", "MonoBehaviour", "Object", "Component", "ScriptableObject"):
            continue
        seen.add(n)
        for ns, cname, b, block in find(lines, n):
            print(f"{ns}\n{block[0].strip()}")
            for o, decl in fields(block):
                print(f"   {hex(o):>7}  {decl}")
            for addr, sig in methods(block):
                if not rx or rx.search(sig):
                    print(f"   {addr:>11}  {sig}")
            print()
            if "--bases" in a and b:
                todo.append(base_name(b))
    if not seen - {""}:
        print(f"{name}: not found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
