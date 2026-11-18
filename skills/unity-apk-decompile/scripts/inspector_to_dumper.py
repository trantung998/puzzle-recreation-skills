#!/usr/bin/env python3
"""Turn Il2CppInspectorRedux output into the Il2CppDumper file layout the other scripts read.

Usage: python3 -I inspector_to_dumper.py <il2cpp-out-dir>

Reads  <dir>/metadata.json (Inspector --json-out) and <dir>/.cpp/appdata/il2cpp-types.h.
Writes <dir>/script.json        {ScriptMethod, ScriptString, ScriptMetadata, ScriptMetadataMethod, Addresses}
       <dir>/stringliteral.json [{value, address}]
       <dir>/il2cpp.h           (copy of il2cpp-types.h)

Inspector "virtualAddress" values for an Android ELF equal Il2CppDumper's RVA (the ELF links
at base 0), so addresses are copied unchanged. Method names follow Il2CppDumper's
"Namespace.Type$$Method" form (nested types joined with ".", generic args as <...>).
"""
import json
import os
import re
import shutil
import sys

_PRIMITIVES = {"Object": "object", "String": "string", "Boolean": "bool", "Char": "char", "Byte": "byte",
               "SByte": "sbyte", "Int16": "short", "UInt16": "ushort", "Int32": "int", "UInt32": "uint",
               "Int64": "long", "UInt64": "ulong", "Single": "float", "Double": "double",
               "Decimal": "decimal", "Void": "void"}
_KEYWORDS = dict({"System." + k: v for k, v in _PRIMITIVES.items()}, **_PRIMITIVES)
_ARGS = re.compile(r"(`\d+)?\[")


def _match(s, i, open_c, close_c):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == open_c:
            depth += 1
        elif s[j] == close_c:
            depth -= 1
            if depth == 0:
                return j
    return -1


def _split_top(s, sep):
    parts, depth, start = [], 0, 0
    for i, c in enumerate(s):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(s[start:i])
            start = i + 1
    parts.append(s[start:])
    return parts


def _render(t, keep_ns):
    """Inspector type text -> Il2CppDumper style: nested types joined with '.', the last generic
    argument list moved to the end as <...>, argument types short with C# keywords."""
    t = t.strip().replace("/", ".")
    arr = ""
    while t.endswith("[]"):
        arr, t = arr + "[]", t[:-2]
    bases, args = [], None
    for comp in _split_top(t, "+"):
        m = _ARGS.search(comp)
        if m and comp.endswith("]") and _match(comp, m.end() - 1, "[", "]") == len(comp) - 1:
            bases.append(comp[:m.start()])
            args = comp[m.end():-1]
        else:
            bases.append(comp)
    if not keep_ns:
        bases[0] = bases[0].rsplit(".", 1)[-1]
    name = ".".join(bases)
    if args is not None:
        name += "<" + ", ".join(short_type(a) for a in _split_top(args, ",")) + ">"
    elif not keep_ns and len(bases) == 1 and t in _KEYWORDS:
        name = _KEYWORDS[t]
    return name + arr


def short_type(t):
    """Generic argument form: `System.Collections.Generic.List`1[System.Int32]` -> `List<int>`."""
    return _render(t, keep_ns=False)


def type_name(group):
    """`Asm.dll/Ns/Sub/Outer+Inner` -> `Ns.Sub.Outer.Inner`; generic instances end in <args>."""
    path = group.split("/", 1)[1] if "/" in group else group
    return _render(path, keep_ns=True)


def _head(sig):
    """Text before the parameter list (first '(' outside [] and <>)."""
    depth = 0
    for i, c in enumerate(sig):
        if c in "[<":
            depth += 1
        elif c in "]>":
            depth -= 1
        elif c == "(" and depth == 0:
            return sig[:i]
    return sig


def _last_space(s):
    depth, pos = 0, -1
    for i, c in enumerate(s):
        if c in "[<":
            depth += 1
        elif c in "]>":
            depth -= 1
        elif c == " " and depth == 0:
            pos = i
    return pos


def method_name(dotnet_sig, c_sig):
    head = _head(dotnet_sig).strip()
    sp = _last_space(head)
    if sp < 0:  # constructors carry no return type
        return ".cctor" if "__cctor(" in c_sig else ".ctor"
    name = head[sp + 1:]
    k = name.find("[")
    if k > 0 and name.endswith("]") and _match(name, k, "[", "]") == len(name) - 1:
        name = name[:k] + "<" + ", ".join(short_type(a) for a in _split_top(name[k + 1:-1], ",")) + ">"
    return name


def _mangled_parts(mangled):
    """Leading <len><name> components of `_ZN...`, and whether they cover the whole name."""
    if not mangled.startswith("_ZN"):
        return [], False
    s, i, parts = mangled[3:], 0, []
    while i < len(s):
        m = re.match(r"\d+", s[i:])
        if not m:
            break
        n = int(m.group())
        i += len(m.group())
        parts.append(s[i:i + n])
        i += n
    return parts, s[i:] == "E"


def demangle_path(mangled):
    """`_ZN8TypeInfo6System6ObjectE` -> `System.Object`; None for anything but plain nested names."""
    parts, whole = _mangled_parts(mangled)
    return ".".join(parts[1:]) if whole and len(parts) > 1 else None


def type_label(mangled, dotnet):
    """Il2CppDumper-style class name for a TypeInfo/TypeRef slot."""
    if dotnet.endswith("]"):
        return dotnet
    parts, whole = _mangled_parts(mangled)
    if whole and len(parts) > 1:
        path = ".".join(parts[1:])
        return _KEYWORDS.get(path, path) if path.startswith("System.") else path
    if len(parts) > 1 and dotnet.startswith(parts[-1]):
        return ".".join(parts[1:-1] + [dotnet])
    return dotnet or mangled


def method_info_label(mangled, dotnet):
    """Label for a MethodInfo slot whose method has no address of its own (shared generic code)."""
    name = method_name(dotnet, "")
    comps = _mangled_parts(mangled)[0][1:]
    if comps and comps[-1] == name.split("<")[0]:
        comps = comps[:-1]
    head = _head(dotnet)
    params = []
    for p in _split_top(dotnet[len(head) + 1:].rstrip(")"), ","):
        p = p.strip()
        if p:
            ref = p.endswith(" ByRef")
            params.append(short_type(p[:-6] if ref else p) + ("&" if ref else ""))
    return "Method$" + ".".join(comps + [name]) + "(" + ", ".join(params) + ")"


def _addr(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def convert(out_dir):
    src = os.path.join(out_dir, "metadata.json")
    with open(src, encoding="utf-8") as f:
        am = json.load(f)["addressMap"]

    methods, by_addr = [], {}
    for m in am.get("methodDefinitions", []) + am.get("constructedGenericMethods", []):
        a = _addr(m["virtualAddress"])
        if not a:
            continue
        full = type_name(m.get("group", "")) + "$$" + method_name(m.get("dotNetSignature", ""), m.get("signature", ""))
        by_addr.setdefault(a, full)
        sig = m.get("signature", "")
        methods.append({"Address": a, "Name": full, "Signature": sig + ";" if sig else ""})

    strings = [{"Address": _addr(s["virtualAddress"]), "Value": s.get("string", "")}
               for s in am.get("stringLiterals", [])]

    meta = []
    for t in am.get("typeInfoPointers", []):
        name = type_label(t["name"], t.get("dotNetType", ""))
        meta.append({"Address": _addr(t["virtualAddress"]), "Name": name + "_TypeInfo", "Signature": "Il2CppClass*"})
    for t in am.get("typeRefPointers", []):
        name = type_label(t["name"], t.get("dotNetType", ""))
        meta.append({"Address": _addr(t["virtualAddress"]), "Name": name + "_var", "Signature": "Il2CppType*"})

    meta_methods = []
    for m in am.get("methodInfoPointers", []):
        target = _addr(m.get("methodAddress", "0x0"))
        full = by_addr.get(target)
        if full:
            label = "Method$" + full.replace("$$", ".") + "()"
        else:
            label = method_info_label(m["name"], m.get("dotNetSignature", ""))
        meta_methods.append({"Address": _addr(m["virtualAddress"]), "Name": label, "MethodAddress": target})

    addresses = sorted({a for a in map(_addr, am.get("functionAddresses", [])) if a})

    script = {"ScriptMethod": methods, "ScriptString": strings, "ScriptMetadata": meta,
              "ScriptMetadataMethod": meta_methods, "Addresses": addresses}
    with open(os.path.join(out_dir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False)
    with open(os.path.join(out_dir, "stringliteral.json"), "w", encoding="utf-8") as f:
        json.dump([{"value": s["Value"], "address": "0x%X" % s["Address"]} for s in strings], f,
                  ensure_ascii=False, indent=2)
    header = os.path.join(out_dir, ".cpp", "appdata", "il2cpp-types.h")
    if os.path.isfile(header):
        shutil.copyfile(header, os.path.join(out_dir, "il2cpp.h"))
    return {"methods": len(methods), "strings": len(strings), "metadata": len(meta) + len(meta_methods)}


def main(argv):
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    if not os.path.isfile(os.path.join(argv[0], "metadata.json")):
        print("missing %s" % os.path.join(argv[0], "metadata.json"), file=sys.stderr)
        return 1
    stats = convert(argv[0])
    print("converted: %(methods)d methods, %(strings)d strings, %(metadata)d metadata slots" % stats,
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
