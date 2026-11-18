import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import inspector_to_dumper as conv  # noqa: E402


def md(addr, group, dotnet, csig="void X(MethodInfo * method)"):
    return {"virtualAddress": addr, "name": "_ZN1X", "signature": csig, "dotNetSignature": dotnet, "group": group}


METADATA = {"addressMap": {
    "methodDefinitions": [
        md("0x04DABFDC", "Peak.MatchGame.dll/Global/Level/LevelDataService", "LevelDataService get_Instance()",
           "LevelDataService * LevelDataService_get_Instance(MethodInfo * method)"),
        md("0x04DAC0D8", "Peak.MatchGame.dll/Global/Level/LevelDataService", "LevelDataService()",
           "void LevelDataService__ctor(LevelDataService * this, MethodInfo * method)"),
        md("0x04CD0000", "Peak.MatchGame.dll/Util/Constants", "Constants()",
           "void Constants__cctor(MethodInfo * method)"),
        md("0x04CD0B94", "Peak.MatchGame.dll/Util/CoroutineConstants+<WaitForFrames>d__5", "Boolean MoveNext()"),
        md("0x04CD0C14", "Peak.MatchGame.dll/Util/CoroutineConstants+<WaitForFrames>d__5",
           "Void System.Collections.IEnumerator.Reset()"),
        md("0x04CD2EF8", "Peak.MatchGame.dll/Util/DirectionExtensions+<get_AllDirections>d__20",
           "IEnumerator`1[Util.Direction] System.Collections.Generic.IEnumerable<Util.Direction>.GetEnumerator()"),
        md("0x04CCDADC", "Peak.MatchGame.dll/UnitySourceGeneratedAssemblyMonoScriptTypes_v1",
           "UnitySourceGeneratedAssemblyMonoScriptTypes_v1+MonoScriptData Get()"),
        md("0x05000000", "Game.dll/Board", "Void Swap[T](T, T)"),
    ],
    "constructedGenericMethods": [
        md("0x0355E760", "mscorlib.dll/System/Collections/Generic/List`1[System/Int32]", "Void Add(Int32)"),
        md("0x0355E800", "mscorlib.dll/System/Threading/Tasks/TaskFactory`1[TResult]+<>c__DisplayClass35_0[System/Int64]",
           "TaskFactory`1[TResult]+<>c__DisplayClass35_0[System.Int64]()",
           "void TaskFactory_1_TResult_c_DisplayClass35_0_System_Int64___ctor(X * this, MethodInfo * method)"),
    ],
    "stringLiterals": [
        {"virtualAddress": "0x064AA9A8", "name": "StringLiteral__", "string": ""},
        {"virtualAddress": "0x064C6F88", "name": "StringLiteral_SocketManager", "string": "SocketManager"},
    ],
    "typeInfoPointers": [
        {"virtualAddress": "0x0644EE10", "name": "_ZN8TypeInfo6System6ObjectE", "type": "struct Object__Class *",
         "dotNetType": "object"},
        {"virtualAddress": "0x0645C4E0", "name": "_ZN8TypeInfo11UnityEngine10UIElements19UIToolkitConverters3__cE",
         "type": "struct X *", "dotNetType": "__c"},
        {"virtualAddress": "0x0645C4E8", "name": "_ZN8TypeInfo6System11Collections7Generic4ListIiEE",
         "type": "struct X *", "dotNetType": "List<int>"},
    ],
    "typeRefPointers": [
        {"virtualAddress": "0x06438DD8", "name": "_ZN7TypeRef6System9AttributeE", "dotNetType": "Attribute"},
    ],
    "methodInfoPointers": [
        {"virtualAddress": "0x0649F8B0", "name": "_ZN10MethodInfo1X", "dotNetSignature": "Void System.Collections.IEnumerator.Reset()",
         "methodAddress": "0x04CD0C14"},
        {"virtualAddress": "0x0649F8B8",
         "name": "_ZN10MethodInfo6System11Collections7Generic5QueueIN6Dialog25WarningContentServiceBaseEE7EnqueueEv",
         "dotNetSignature": "Void Enqueue(WarningContentServiceBase)", "methodAddress": "0x00000000"},
        {"virtualAddress": "0x0649F8C0",
         "name": "_ZN10MethodInfo6System4Linq10Enumerable5EmptyIN6Google8LocationEEEv",
         "dotNetSignature": "IEnumerable`1[Google.Location] Empty[Google.Location]()", "methodAddress": "0x00000000"},
        {"virtualAddress": "0x0649F8C8",
         "name": "_ZN10MethodInfo6System11Collections7Generic10DictionaryIA_N11UnityEngine7Vector2EN10FillSolver"
                 "8PolyMaskEE11TryGetValueEA_S5_RS7_",
         "dotNetSignature": "Boolean TryGetValue(Vector2[], FillSolver+PolyMask ByRef)", "methodAddress": "0x00000000"},
    ],
    "functionAddresses": ["0x00000000", "0x04CD0C14", "0x04CD0B94"],
}}


class NameTests(unittest.TestCase):
    def test_type_from_group(self):
        self.assertEqual(conv.type_name("Peak.MatchGame.dll/Global/Level/LevelDataService"),
                         "Global.Level.LevelDataService")
        self.assertEqual(conv.type_name("Peak.MatchGame.dll/Util/CoroutineConstants+<WaitForFrames>d__5"),
                         "Util.CoroutineConstants.<WaitForFrames>d__5")
        self.assertEqual(conv.type_name("mscorlib.dll/System/Collections/Generic/List`1[System/Int32]"),
                         "System.Collections.Generic.List<int>")
        self.assertEqual(conv.type_name("Game.dll/Board"), "Board")
        # Il2CppDumper style: generic args go on the innermost type, short names, C# keywords
        self.assertEqual(conv.type_name("Unity.Collections.dll/Unity/Collections/NativeArray`1[T]+Enumerator"
                                        "[UnityEngine/Rendering/ProbeBrickIndex+Brick]"),
                         "Unity.Collections.NativeArray.Enumerator<ProbeBrickIndex.Brick>")
        self.assertEqual(conv.type_name("mscorlib.dll/System/Collections/Generic/Dictionary`2"
                                        "[System/String,System/Collections/Generic/List`1[System/Object]]"),
                         "System.Collections.Generic.Dictionary<string, List<object>>")

    def test_generic_args(self):
        self.assertEqual(conv.short_type("KeyValuePair`2[System.Int32Enum,System.Single]"),
                         "KeyValuePair<Int32Enum, float>")
        self.assertEqual(conv.short_type("Collection.CardData.CollectionPackOpeningResult"),
                         "CollectionPackOpeningResult")
        self.assertEqual(conv.short_type("MeshGenerator+RepeatRectUV"), "MeshGenerator.RepeatRectUV")
        self.assertEqual(conv.short_type("System.Byte[]"), "byte[]")

    def test_method_names(self):
        self.assertEqual(conv.method_name("LevelDataService get_Instance()", "X"), "get_Instance")
        self.assertEqual(conv.method_name("LevelDataService()", "void A__ctor(A * this)"), ".ctor")
        self.assertEqual(conv.method_name("Constants()", "void Constants__cctor(MethodInfo * method)"), ".cctor")
        self.assertEqual(conv.method_name("Void System.Collections.IEnumerator.Reset()", "X"),
                         "System.Collections.IEnumerator.Reset")
        self.assertEqual(conv.method_name(
            "IEnumerator`1[Util.Direction] System.Collections.Generic.IEnumerable<Util.Direction>.GetEnumerator()", "X"),
            "System.Collections.Generic.IEnumerable<Util.Direction>.GetEnumerator")
        self.assertEqual(conv.method_name("Void Swap[T](T, T)", "X"), "Swap<T>")
        self.assertEqual(conv.method_name("Tweener SetEase[Object](Object, Ease)", "X"), "SetEase<object>")
        self.assertEqual(conv.method_name("TaskFactory`1[TResult]+<>c__DisplayClass35_0[System.Int64]()",
                                          "void T___ctor(X * this)"), ".ctor")

    def test_demangled_type_label(self):
        self.assertEqual(conv.demangle_path("_ZN8TypeInfo11UnityEngine10UIElements19UIToolkitConverters3__cE"),
                         "UnityEngine.UIElements.UIToolkitConverters.__c")
        self.assertIsNone(conv.demangle_path("_ZN8TypeInfo6System11Collections7Generic4ListIiEE"))
        self.assertEqual(conv.type_label("_ZN8TypeInfo6System11Collections7Generic4ListIiEE", "List<int>"),
                         "System.Collections.Generic.List<int>")
        self.assertEqual(conv.type_label("_ZN8TypeInfo6System4CharE", "char[]"), "char[]")


class ConvertTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        with open(os.path.join(self.out, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(METADATA, f)
        hdr = os.path.join(self.out, ".cpp", "appdata")
        os.makedirs(hdr)
        with open(os.path.join(hdr, "il2cpp-types.h"), "w") as f:
            f.write("struct Il2CppClass;\n")

    def tearDown(self):
        self._tmp.cleanup()

    def load(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as f:
            return json.load(f)

    def test_writes_dumper_layout(self):
        stats = conv.convert(self.out)
        script = self.load("script.json")
        names = {m["Address"]: m["Name"] for m in script["ScriptMethod"]}
        self.assertEqual(names[0x04DABFDC], "Global.Level.LevelDataService$$get_Instance")
        self.assertEqual(names[0x04DAC0D8], "Global.Level.LevelDataService$$.ctor")
        self.assertEqual(names[0x04CD0000], "Util.Constants$$.cctor")
        self.assertEqual(names[0x04CD0B94], "Util.CoroutineConstants.<WaitForFrames>d__5$$MoveNext")
        self.assertEqual(names[0x0355E760], "System.Collections.Generic.List<int>$$Add")
        self.assertEqual(names[0x0355E800], "System.Threading.Tasks.TaskFactory.<>c__DisplayClass35_0<long>$$.ctor")
        self.assertEqual(len(script["ScriptMethod"]), 10)
        self.assertTrue(all(isinstance(m["Address"], int) for m in script["ScriptMethod"]))
        sig = next(m["Signature"] for m in script["ScriptMethod"] if m["Address"] == 0x04DABFDC)
        self.assertIn("LevelDataService_get_Instance", sig)

        self.assertEqual(script["ScriptString"], [{"Address": 0x064AA9A8, "Value": ""},
                                                  {"Address": 0x064C6F88, "Value": "SocketManager"}])
        meta = {m["Address"]: m["Name"] for m in script["ScriptMetadata"]}
        self.assertEqual(meta[0x0644EE10], "object_TypeInfo")
        self.assertEqual(meta[0x0645C4E0], "UnityEngine.UIElements.UIToolkitConverters.__c_TypeInfo")
        self.assertEqual(meta[0x0645C4E8], "System.Collections.Generic.List<int>_TypeInfo")
        self.assertEqual(meta[0x06438DD8], "System.Attribute_var")
        mm = {m["Address"]: m for m in script["ScriptMetadataMethod"]}
        self.assertEqual(mm[0x0649F8B0]["Name"],
                         "Method$Util.CoroutineConstants.<WaitForFrames>d__5.System.Collections.IEnumerator.Reset()")
        self.assertEqual(mm[0x0649F8B0]["MethodAddress"], 0x04CD0C14)
        # shared generic code has no own address: type path from the mangled name, params from .NET
        self.assertEqual(mm[0x0649F8B8]["Name"],
                         "Method$System.Collections.Generic.Queue.Enqueue(WarningContentServiceBase)")
        self.assertEqual(mm[0x0649F8C0]["Name"], "Method$System.Linq.Enumerable.Empty<Location>()")
        self.assertEqual(mm[0x0649F8C8]["Name"], "Method$System.Collections.Generic.Dictionary.TryGetValue(Vector2[], FillSolver.PolyMask&)")
        self.assertEqual(script["Addresses"], [0x04CD0B94, 0x04CD0C14])

        self.assertEqual(self.load("stringliteral.json"), [{"value": "", "address": "0x64AA9A8"},
                                                           {"value": "SocketManager", "address": "0x64C6F88"}])
        with open(os.path.join(self.out, "il2cpp.h")) as f:
            self.assertEqual(f.read(), "struct Il2CppClass;\n")
        self.assertEqual(stats["methods"], 10)

    def test_select_targets_reads_converted_script(self):
        conv.convert(self.out)
        work = os.path.join(self.out, "work")
        p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "select_targets.py"), self.out, work,
                            r"LevelDataService\$\$get_Instance$"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(os.path.join(work, "targets.tsv")) as f:
            self.assertEqual(f.read(), "4dabfdc\tGlobal.Level.LevelDataService$$get_Instance\t"
                                       "Global.Level.LevelDataService$$get_Instance\n")
        with open(os.path.join(work, "labels.tsv"), encoding="utf-8") as f:
            labels = f.read()
        self.assertIn('64c6f88\tStringLiteral "SocketManager"\n', labels)
        self.assertIn("644ee10\tobject_TypeInfo\n", labels)

    def test_missing_metadata_json_fails(self):
        os.remove(os.path.join(self.out, "metadata.json"))
        p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "inspector_to_dumper.py"), self.out],
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("metadata.json", p.stderr)


if __name__ == "__main__":
    unittest.main()
