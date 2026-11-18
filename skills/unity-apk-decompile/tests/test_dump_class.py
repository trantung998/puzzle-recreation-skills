import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "dump_class.py")

# Il2CppInspectorRedux C# layout (types.cs): indented, namespace blocks, nested types inline,
# method address range as a trailing comment.
INSPECTOR = """\
namespace Global.Level
{
\tpublic class LevelBase // TypeDefIndex: 1428
\t{
\t\t// Fields
\t\tprotected int _baseId; // 0x10
\t}

\tpublic class LevelDataService : LevelBase // TypeDefIndex: 1429
\t{
\t\t// Fields
\t\t[CompilerGenerated]
\t\tprivate int _Seed_k__BackingField; // 0x18
\t\tprivate Dictionary<int, int> _levelTable; // 0x20
\t\tprivate static LevelDataService _instance; // 0x00
\t\tprivate const int FallbackLevel = 155; // Metadata: 0x008E23AE
\t
\t\t// Properties
\t\tpublic int Seed { [CompilerGenerated] get; [CompilerGenerated] private set; } // 0x04DAC0F4-0x04DAC0FC 0x04DAC0FC-0x04DAC104
\t
\t\t// Nested types
\t\tprivate sealed class _Load_d__5 : IEnumerator<object> // TypeDefIndex: 17
\t\t{
\t\t\t// Fields
\t\t\tprivate int __1__state; // 0x10
\t\t\tprivate bool MoveNext(); // 0x04CD0B94-0x04CD0C0C
\t\t}
\t
\t\t// Constructors
\t\tprivate LevelDataService(); // 0x04DAC0D8-0x04DAC0F4
\t
\t\t// Methods
\t\tpublic LevelData GetClientLevelData(int levelDataNo); // 0x04DAC410-0x04DAC48C
\t\tpublic abstract void Apply();
\t}
}

public class GlobalThing : MonoBehaviour // TypeDefIndex: 78
{
\t// Fields
\tpublic int count; // 0x18
}
"""

# Il2CppDumper layout (dump.cs): flat, "// Namespace:" line, "// RVA:" line before each method.
DUMPER = """\
// Namespace: Global.Level
public class LevelDataService : IService // TypeDefIndex: 1429
{
\t// Fields
\tprivate int <Seed>k__BackingField; // 0x18

\t// Methods

\t// RVA: 0x4DAC410 Offset: 0x4DA8410 VA: 0x4DAC410
\tpublic LevelData GetClientLevelData(int levelDataNo) { }
}
"""


def run(path, *args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, path, *args], capture_output=True, text=True)
    return p.returncode, p.stdout


class DumpClassTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ins = os.path.join(self._tmp.name, "ins.cs")
        self.dmp = os.path.join(self._tmp.name, "dmp.cs")
        with open(self.ins, "w", encoding="utf-8") as f:
            f.write(INSPECTOR)
        with open(self.dmp, "w", encoding="utf-8") as f:
            f.write(DUMPER)

    def tearDown(self):
        self._tmp.cleanup()

    def test_inspector_class_listing(self):
        rc, out = run(self.ins, "LevelDataService")
        self.assertEqual(rc, 0, out)
        self.assertIn("// Namespace: Global.Level", out)
        self.assertIn("0x18  private int _Seed_k__BackingField", out)
        self.assertIn("0x20  private Dictionary<int, int> _levelTable", out)
        self.assertIn("0x04DAC410  public LevelData GetClientLevelData(int levelDataNo);", out)
        self.assertIn("0x04DAC0D8  private LevelDataService();", out)
        self.assertIn("0x04DAC0F4  public int Seed", out)
        self.assertIn("private set; }  // 0x04DAC0F4, 0x04DAC0FC", out)
        # nested type members belong to the nested type, not the outer class
        outer = out.split("\n\n")[0]
        self.assertNotIn("__1__state", outer)
        self.assertNotIn("MoveNext", outer)
        self.assertNotIn("FallbackLevel", outer)

    def test_inspector_global_namespace_after_namespace_block(self):
        rc, out = run(self.ins, "GlobalThing")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Global.Level", out)
        self.assertIn("0x18  public int count", out)

    def test_inspector_methods_filter_and_nested(self):
        rc, out = run(self.ins, "LevelDataService", "--methods", "GetClient")
        self.assertIn("GetClientLevelData", out)
        self.assertNotIn("LevelDataService();", out)
        rc, out = run(self.ins, "_Load_d__5")
        self.assertEqual(rc, 0, out)
        self.assertIn("0x10  private int __1__state", out)
        self.assertIn("0x04CD0B94  private bool MoveNext();", out)

    def test_inspector_offset_walks_bases(self):
        rc, out = run(self.ins, "--offset", "LevelDataService", "0x20")
        self.assertEqual((rc, out.strip()), (0, "LevelDataService+0x20: private Dictionary<int, int> _levelTable"))
        rc, out = run(self.ins, "--offset", "LevelDataService", "0x10")
        self.assertEqual((rc, out.strip()), (0, "LevelBase+0x10: protected int _baseId"))
        rc, out = run(self.ins, "--offset", "LevelDataService", "0x0")
        self.assertNotIn("_instance", out)

    def test_dumper_layout_still_works(self):
        rc, out = run(self.dmp, "LevelDataService")
        self.assertEqual(rc, 0, out)
        self.assertIn("// Namespace: Global.Level", out)
        self.assertIn("0x18  private int <Seed>k__BackingField", out)
        self.assertIn("0x4DAC410  public LevelData GetClientLevelData(int levelDataNo) { }", out)
        rc, out = run(self.dmp, "--offset", "LevelDataService", "0x18")
        self.assertEqual(out.strip(), "LevelDataService+0x18: private int <Seed>k__BackingField")


if __name__ == "__main__":
    unittest.main()
