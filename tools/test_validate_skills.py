import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "validate_skills.py")

GOOD_DESC = "Use when doing things. Dùng khi làm việc."


def make_skill(root, name, fm=None, body="# Body\n", files=None, dirname=None):
    d = os.path.join(root, dirname or name)
    os.makedirs(d)
    if fm is None:
        fm = "name: %s\ndescription: %s" % (name, GOOD_DESC)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\n%s\n---\n%s" % (fm, body))
    for rel, text in (files or {}).items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    return d


def run(*dirs):
    r = subprocess.run([sys.executable, SCRIPT, *dirs], capture_output=True,
                       text=True, encoding="utf-8")
    return r.returncode, r.stdout


class ValidateSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def expect(self, rule, d):
        code, out = run(d)
        self.assertEqual(code, 1, out)
        self.assertIn(": " + rule + ":", out)
        return out

    def test_valid(self):
        d = make_skill(self.root, "good-skill")
        code, out = run(d)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "OK 1 skills")

    def test_multiple_valid(self):
        a = make_skill(self.root, "aa")
        b = make_skill(self.root, "bb")
        self.assertEqual(run(a, b)[1].strip(), "OK 2 skills")

    def test_no_skill_md(self):
        d = os.path.join(self.root, "empty")
        os.makedirs(d)
        self.expect("no-skill-md", d)

    def test_frontmatter_keys(self):
        d = make_skill(self.root, "good", fm="name: good\ndescription: %s\nextra: x" % GOOD_DESC)
        out = self.expect("frontmatter-keys", d)
        self.assertIn("SKILL.md:4:", out)

    def test_name_format(self):
        d = make_skill(self.root, "Bad_Name")
        self.expect("name-format", d)

    def test_name_matches_dir(self):
        d = make_skill(self.root, "other", dirname="thedir")
        self.expect("name-matches-dir", d)

    def test_description_prefix(self):
        d = make_skill(self.root, "good", fm="name: good\ndescription: Does things")
        self.expect("description-prefix", d)

    def test_frontmatter_length(self):
        d = make_skill(self.root, "good", fm="name: good\ndescription: Use when " + "x" * 1100)
        self.expect("frontmatter-length", d)

    def test_harness_tool_name(self):
        for tok in ["TodoWrite", "Task(x)", "subagent_type", "Bash(ls)", "the todo tool"]:
            with self.subTest(tok=tok):
                d = make_skill(self.root, "s" + str(abs(hash(tok))), body="ok\n```\n%s\n```\n" % tok)
                out = self.expect("harness-tool-name", d)
                self.assertIn("SKILL.md:7:", out)

    def test_harness_tool_name_in_reference(self):
        d = make_skill(self.root, "good", files={"references/a.md": "x\nTodoWrite\n"})
        out = self.expect("harness-tool-name", d)
        self.assertIn("a.md:2:", out)

    def test_at_link(self):
        d = make_skill(self.root, "good", body="see @references/a.md now\n")
        self.expect("at-link", d)

    def test_bare_script(self):
        d = make_skill(self.root, "good", body="run `scripts/x.py` now\n")
        self.expect("bare-script", d)

    def test_script_with_interpreter_ok(self):
        d = make_skill(self.root, "good",
                       body="run `python3 scripts/x.py` and `bash scripts/y.sh`\n")
        self.assertEqual(run(d)[0], 0)

    def test_missing_ref(self):
        d = make_skill(self.root, "good", body="[a](references/nope.md)\n")
        self.expect("missing-ref", d)

    def test_ref_ok_and_ignored(self):
        d = make_skill(self.root, "good",
                       body="[a](references/a.md#sec) [w](https://x.y/z.md) [m](mailto:a@b.c) [h](#top)\n",
                       files={"references/a.md": "hi\n",
                              "templates/t.md": "[p](placeholder.md)\n"})
        code, out = run(d)
        self.assertEqual(code, 0, out)

    def test_missing_ref_in_reference_file(self):
        d = make_skill(self.root, "good", files={"references/a.md": "[x](gone.md)\n"})
        self.expect("missing-ref", d)


if __name__ == "__main__":
    unittest.main()
