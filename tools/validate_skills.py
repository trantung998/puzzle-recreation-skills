"""Lint agent skill directories against the plan's Global Constraints."""
import glob
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TOOL_RES = [re.compile(r"\b(TodoWrite|todowrite|Task\(|subagent_type|Bash\()"),
            re.compile(r"\btodo tool\b")]
AT_RE = re.compile(r"(^|\s)@[\w./-]+\.md")
SPAN_RE = re.compile(r"`([^`\n]*)`")
SCRIPT_RE = re.compile(r"(?<!python3 )(?<!bash )(?<![\w/.-])scripts/[\w./-]*\.(?:py|sh)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)[^)]*\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def read_lines(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read().split("\n")


def parse_frontmatter(lines):
    """Return (end_index, {key: (line_no, value)}, length) or None."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            keys = {}
            cur = None
            for j in range(1, i):
                m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", lines[j])
                if m:
                    cur = m.group(1)
                    keys[cur] = [j + 1, m.group(2).strip()]
                elif cur and lines[j].strip():
                    keys[cur][1] += " " + lines[j].strip()
            length = len("\n".join(lines[1:i]))
            return i, keys, length
    return None


def unquote(v):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def lint_skill(d):
    out = []
    skill_md = os.path.join(d, "SKILL.md")

    def add(path, line, rule, msg):
        out.append("%s:%d: %s: %s" % (path, line, rule, msg))

    fm = parse_frontmatter(read_lines(skill_md))
    if fm is None:
        add(skill_md, 1, "frontmatter-keys", "missing frontmatter block")
    else:
        _, keys, length = fm
        for k, (ln, _) in keys.items():
            if k not in ("name", "description"):
                add(skill_md, ln, "frontmatter-keys", "unexpected key '%s'" % k)
        for k in ("name", "description"):
            if k not in keys:
                add(skill_md, 1, "frontmatter-keys", "missing key '%s'" % k)
        if "name" in keys:
            ln, v = keys["name"]
            v = unquote(v)
            if not NAME_RE.match(v):
                add(skill_md, ln, "name-format", "'%s' is not kebab-case" % v)
            if v != os.path.basename(os.path.normpath(d)):
                add(skill_md, ln, "name-matches-dir",
                    "name '%s' != directory '%s'" % (v, os.path.basename(os.path.normpath(d))))
        if "description" in keys:
            ln, v = keys["description"]
            if not unquote(v).startswith("Use when"):
                add(skill_md, ln, "description-prefix", "must start with 'Use when'")
        if length >= 1024:
            add(skill_md, 1, "frontmatter-length", "frontmatter is %d chars (limit <1024)" % length)

    files = [skill_md] + sorted(glob.glob(os.path.join(d, "references", "*.md")))
    for path in files:
        for n, line in enumerate(read_lines(path), 1):
            for r in TOOL_RES:
                m = r.search(line)
                if m:
                    add(path, n, "harness-tool-name", "harness-specific token '%s'" % m.group(0))
            if AT_RE.search(line):
                add(path, n, "at-link", "@file link not allowed")
            for span in SPAN_RE.findall(line):
                m = SCRIPT_RE.search(span)
                if m:
                    add(path, n, "bare-script",
                        "'%s' needs a python3/bash interpreter prefix" % m.group(0))
            for target in LINK_RE.findall(line):
                if SCHEME_RE.match(target) or target.startswith("#"):
                    continue
                t = target.split("#", 1)[0]
                if t and not os.path.exists(os.path.join(os.path.dirname(path), t)):
                    add(path, n, "missing-ref", "link target '%s' does not exist" % t)
    return out


def main(argv):
    violations = []
    count = 0
    for d in argv:
        if not os.path.isfile(os.path.join(d, "SKILL.md")):
            violations.append("%s:1: no-skill-md: directory has no SKILL.md" % d)
            continue
        count += 1
        violations.extend(lint_skill(d))
    if violations:
        print("\n".join(violations))
        return 1
    print("OK %d skills" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
