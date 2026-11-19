---
name: unity-apk-decompile
description: Use when decompiling or reverse engineering an Android Unity game (APK, XAPK, APKS, APKM) to recover gameplay logic, level data, configs or assets - libil2cpp.so, global-metadata.dat, Il2CppInspectorRedux, Il2CppDumper, "not a supported version[39]" on Unity 6 metadata, Cpp2IL, Ghidra headless, AssetRipper, Assembly-CSharp.dll, IL2CPP vs Mono. Also for "dịch ngược / decompile game Unity", reading IL2CPP pseudocode, or Ghidra hanging/OOM/timeouts on a huge stripped libil2cpp.so.
---

# Decompile game Unity Android (IL2CPP / Mono)

## Nguyên tắc cốt lõi

**Metadata trước, decompile có mục tiêu sau. Không bao giờ auto-analyze cả `libil2cpp.so`.**
Tên class/method/field nằm trong `global-metadata.dat`; mã máy nằm trong `libil2cpp.so`
(100-200 MB, stripped). Lấy bản đồ tên → chọn vài method → import Ghidra `-noanalysis`
→ decompile đúng các địa chỉ đó. Đã đo: import + decompile 2 hàm = **10 s (armv7, 121 MB)**,
**45 s (arm64, 192 MB)**. Auto-analysis toàn bộ = hàng giờ, OOM với heap mặc định 2 GB.

Logic nằm trong code; **số liệu (level, cân bằng, màu, tốc độ) nằm trong asset** → lấy bằng AssetRipper, không đoán từ code.

## Quy trình

**Bước 0 – tái sử dụng:** xem thư mục dự án đã có `dump.cs`/`script.json`, `ghidra-project`,
export AssetRipper hoặc ghi chú `.md` chưa. Nếu cùng build (cùng version/SHA-256) thì dùng lại
(`dump_class.py` đọc được cả `dump.cs` cũ của Il2CppDumper).

**Dumper:** Il2CppInspectorRedux (Legacy CLI, cần .NET 10 runtime). Il2CppDumper dừng ở metadata
v31, nên không đọc được Unity 6 (v39): `Metadata file supplied is not a supported version[39]`.
`run_il2cppinspector.sh` chuyển output của Inspector sang đúng bộ file Il2CppDumper
(`dump.cs`, `script.json`, `stringliteral.json`, `il2cpp.h`) nên các bước sau không đổi.

**Nền tảng:** Windows → chạy trong Git Bash; macOS (Intel và Apple Silicon) → `/bin/bash` mặc
định là đủ; Linux → bash. `tools-env.sh` tự chọn layout (venv `Scripts/` hay `bin/`, `.exe`,
JDK `Contents/Home` trên macOS). Script Python chạy được từ Python 3.9 (`/usr/bin/python3` của
Xcode CLT). macOS báo `Permission denied`, `killed: 9` hoặc "cannot be opened" → xem mục macOS
trong `references/troubleshooting.md`.

```bash
source "<this skill directory>/scripts/tools-env.sh" # absolute path of the directory holding this SKILL.md; independent of $PWD
# 1. Triage: unpack mọi APK (base + split) vào $W/unpacked/, in ROUTE, ghi $W/paths.env
python3 -I $SK/unity_triage.py game.xapk /path/to/new-workdir
source /path/to/new-workdir/paths.env          # đặt W, SO (libil2cpp.so đã chọn ABI), META

# 2. Dump metadata (~30-70 s). Kết thúc phải có "OK: N methods"
bash $SK/run_il2cppinspector.sh "$SO" "$META" $W/il2cpp-out

# 3. Tìm mục tiêu: theo tên class rồi theo tên method (class trong namespace bị thụt lề)
grep -nE "^\s*(public|internal).*class .*(Passenger|Bus|Level|Board)" $W/il2cpp-out/dump.cs | head -40
python3 -I $SK/dump_class.py $W/il2cpp-out/dump.cs BusStopSlot            # field+offset, method+RVA
python3 -I $SK/select_targets.py $W/il2cpp-out $W/work 'Board|Match|Can[A-Z]|Try[A-Z]' --list | grep -v '^0x.* System\.' | head -60

# 4. Ghi targets.tsv (regex nhiều mục tiêu, nháy đơn để shell không đụng tới $$) rồi decompile
python3 -I $SK/select_targets.py $W/il2cpp-out $W/work \
  'TapBoardingService\$\$TryBoard$|BusStopSlot\$\$BoardingSeatsFor$|BusStopSlot\$\$MatchWithPassenger$'
bash $SK/ghidra_decompile.sh "$SO" $W/work      # -> $W/work/native-code/*.c, _index.tsv

# 5-6. Asset/level (vài chục giây – vài phút) rồi đọc ScriptableObject
python3 -I $SK/assetripper_export.py game.xapk $W/export
python3 -I $SK/unity_yaml.py $W/export/ExportedProject/Assets script LevelCollection
```

| Bước | Kiểm chứng |
|---|---|
| 1 | In `backend`, ABI, metadata `magic 0xfab11baf version N`, Unity version, `protection`, **ROUTE** |
| 2 | Log in `IL2CPP binary version N`; `dump.cs script.json il2cpp.h stringliteral.json` tồn tại |
| 4 | `_index.tsv` toàn `OK`; cột 2 là **địa chỉ Ghidra = image base + RVA**, không phải RVA |
| 5 | In `OK: N files`; YAML ở `ExportedProject/Assets` |
| 7 | Báo cáo: mỗi kết luận gắn **quan sát** (asset/metadata/offset trong dump.cs) / **suy luận** (luồng pseudocode) / **chưa biết**, kèm RVA |

**Mở rộng mục tiêu:** logic thường trải qua nhiều class (service → slot → model). Sau lần
decompile đầu, đọc tên callee C# trong `.c`, thêm các callee quan trọng vào regex bước 4 và
chạy lại. Project Ghidra ở `$W/work/ghidra-project/il2cpp-<sha12>` (khoá theo hash của `.so`, đổi `.so` thì import lại) được tái dùng nên mỗi lần chạy chỉ mất vài
giây (`-readOnly`; `SAVE=1` để lưu tên vào project).

**Đổi offset thành tên field:** `param_1` là `this` của class chứa method.
`python3 -I $SK/dump_class.py $W/il2cpp-out/dump.cs --offset PassengerModel 0x18` tự tìm qua cả
chuỗi class cha. Với `*(*(this+0x10)+0x18)`: tra field `+0x10` trước để biết kiểu của nó, rồi
tra `+0x18` trên kiểu đó. Nếu class cha là generic (`Entity<TModel,...>`), field của nó nằm trong
class generic đó (`dump_class.py ... --bases`).

## Rẽ nhánh theo ROUTE của triage

- **Mono** (`Managed/Assembly-CSharp.dll` có thật, không có `libil2cpp.so`): đây là IL thật → `ilspycmd -p -o out Assembly-CSharp.dll` (`dotnet tool install -g ilspycmd`) cho ra C# gần như nguồn. Không cần Ghidra.
- **IL2CPP arm64**: quy trình trên. Thay thế/bổ sung: REA `inspect_il2cpp_metadata` với `binary_path` (chỉ 64-bit, metadata v24/27/29/31/39) cho tên + địa chỉ không cần .NET.
- **IL2CPP chỉ armv7**: quy trình trên (REA không link được binary 32-bit: `unsupported_target`). Nếu kiếm được split `arm64-v8a` **cùng version** thì dùng nó: pseudocode sạch hơn.
- **Metadata không có magic `0xFAB11BAF`** (bị mã hoá) hoặc không có file: dumper sẽ hỏng. Cần dump metadata từ bộ nhớ lúc chạy (Frida, thiết bị được phép) → xem `references/troubleshooting.md`.
- **Il2CppInspectorRedux báo version không hỗ trợ** (metadata mới hơn bản 2026.2): thử Cpp2IL (`~/.net/Cpp2IL` nếu có) hoặc REA `inspect_il2cpp_metadata`; không hạ version trong header metadata.

## Đọc pseudocode

Script tự chú thích: callee C# được đặt tên, `func_0x...` còn lại là hàm runtime IL2CPP
(init metadata, null check, `op_Inequality`/null test của UnityEngine.Object) – bỏ qua.
`il2cpp_throw_noreturn_*` là helper ném exception mà script tự nhận ra (ARM32), nên hàm dừng
đúng chỗ. Nếu hàm vẫn có vẻ chạy sang logic khác, so với RVA của method kế tiếp trong
`dump_class.py`: phần sau RVA đó là hàm khác. Ghi `(char)` vào địa chỉ vô lý ngay sau một lệnh
throw là code chết. Metadata hiện dạng `/* Method$...() */`,
`/* X_TypeInfo */`, `/* StringLiteral "..." */`. Offset field `param_1 + 0x50` → tra
`dump.cs` (dòng `// 0x50` trong class). Inspector đổi tên do compiler sinh trong `dump.cs`:
`<Seed>k__BackingField` → `_Seed_k__BackingField`, `<Load>d__5` → `_Load_d__5`; `script.json`
giữ tên gốc (`Ns.Outer.<Load>d__5$$MoveNext`). Chi tiết mẫu ARM32/ARM64, generic, virtual call:
`references/reading-il2cpp-pseudocode.md`.

## Sai lầm thường gặp (agent đã mắc khi không có skill này)

| Sai | Đúng |
|---|---|
| Import Ghidra rồi auto-analyze cả file, hoặc `-analysisTimeoutPerFile` | `-noanalysis` + decompile theo danh sách (script bước 4 đã làm) |
| Dùng Il2CppDumper cho Unity 6, hoặc sửa version trong `global-metadata.dat` xuống 31 cho nó chạy | Dumper không đọc v39; metadata bị sửa cho ra tên/địa chỉ sai. Dùng `run_il2cppinspector.sh` |
| Chạy `Il2CppInspector.Redux.CLI` | Bản đó cần cả ASP.NET Core. Dùng Legacy CLI `Il2CppInspector(.exe)` mà `ensure_tools.py` cài |
| `You must install or update .NET` khi chạy Inspector | Cần runtime .NET 10; `DOTNET_ROLL_FORWARD` không hạ được xuống 8/9. `ensure_tools.py` báo `manual` kèm lệnh cài user-scope vào `<root>/dotnet` |
| Lấy địa chỉ trong `il2cpp-functions.h` của Inspector | File đó trừ "global offset" (ví dụ `0x4000`) nên lệch RVA. Chỉ dùng `script.json`/`dump.cs` |
| Chạy script `il2cpp.py`/`ghidra_with_struct.py` của Inspector hay Il2CppDumper ở headless | Cần GUI/PyGhidra, `askFile()` hỏng ở headless. Dùng `DecompileIl2cppTargets.java` (đọc TSV, đặt tên callee + metadata) |
| Giả định image base = 0 hoặc luôn `0x100000` | Ghidra: ARM32 ELF → `0x10000`, AArch64 → `0x100000`. Script lấy `currentProgram.getImageBase()` + RVA |
| Giả định `script.json` có bit Thumb | `Address` là số nguyên RVA, không có bit Thumb (đã kiểm 132 506 method armv7 từ Inspector: không có số lẻ) |
| `export MAXMEM=...` | Biến đúng: `GHIDRA_HEADLESS_MAXMEM` (script mặc định `16G`) |
| Lấy `libil2cpp.so` trong base APK của XAPK | `.so` nằm trong split `config.<abi>.apk`; metadata nằm trong base APK – triage tự tìm |
| Click web UI AssetRipper | `assetripper_export.py` chạy `--headless` và gọi API `/LoadFile` → `/Export/UnityProject` |
| Đọc YAML Unity bằng `yaml.safe_load` trực tiếp | Phải bỏ tag `--- !u!114 &id` trước (`unity_yaml.load_docs`) |
| Gọi pseudocode là "source" | Ghi rõ: suy luận từ mã máy; xác nhận bằng asset hoặc runtime nếu được |

## Tham khảo

- `references/reading-il2cpp-pseudocode.md` – struct IL2CPP, mẫu PIC ARM32 / GOT ARM64, generic, interface call, cách dọn hàm.
- `references/troubleshooting.md` – lỗi Ghidra/REA/dumper/AssetRipper, metadata mã hoá, PairIP, gộp XAPK.
- Skill `reverse-engineer-anything` (REA) khi cần thao tác MCP: `inspect_il2cpp_metadata`, `procedure_pseudo_code`, Frida/adb.

Chỉ phân tích game bạn sở hữu hoặc được phép phân tích; mục tiêu là hiểu/tái hiện cơ chế, không crack, gỡ DRM hay giả mạo thanh toán.
