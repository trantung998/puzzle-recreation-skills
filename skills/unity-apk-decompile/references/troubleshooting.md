# Troubleshooting

## Ghidra

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| Treo / OOM khi import | Heap mặc định 2 GB | `GHIDRA_HEADLESS_MAXMEM=16G` (script đã đặt; máy 16 GB RAM → `10G`) |
| `analyzeHeadless` không có trong PATH | Homebrew không tạo lệnh này | `/opt/homebrew/opt/ghidra/libexec/support/analyzeHeadless`, hoặc `ANALYZE_HEADLESS=...` |
| `ContextChangeException: Context register change conflicts` | Đặt TMode tại địa chỉ đã disassemble | Script chỉ đặt TMode khi chưa có lệnh – đừng gỡ điều kiện đó |
| Output toàn `halt_baddata` / lệnh vô nghĩa (ARM32) | Hàm ở Thumb mode nhưng được disassemble ARM | Xoá project (`rm -rf work/ghidra-project`) rồi sửa `ensureFunction` đặt TMode = 1 cho địa chỉ đó; kiểm tra trong GUI (`ghidraRun`, Ctrl+Shift+F để xem context) |
| `NO_FUNCTION` | Địa chỉ nằm giữa dữ liệu hoặc RVA sai build | Kiểm tra `script.json` và `.so` cùng build; method abstract / không có body không có `// 0x...-0x...` trong `dump.cs` (`RVA: 0x0` với dump.cs cũ của Il2CppDumper) |
| Muốn xem bằng GUI | | `ghidraRun`, mở `work/ghidra-project/il2cpp.gpr`; `G` → địa chỉ (`image base + RVA`) |
| Gọi lại bị chậm | Import lại mỗi lần | Script tái dùng project; chỉ import khi chưa có `il2cpp.rep` |

Analyzer đắt cần tắt nếu buộc phải auto-analyze (GUI): Decompiler Parameter ID, ARM Aggressive
Instruction Finder, Non-Returning Functions - Discovered, Stack.

## macOS

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| `_index.tsv` toàn `FAIL`, hoặc `ghidra_decompile.sh` báo `no macOS decompiler binary` | Zip phát hành của Ghidra chỉ có decompiler native `linux_x86_64`/`win_x86_64` | `ensure_tools.py` (entry `ghidra-natives`) build bằng Gradle wrapper của Ghidra; cần Xcode Command Line Tools (`xcode-select --install`). Tay: `JAVA_HOME=<root>/jdk-25/Contents/Home bash <ghidra>/support/gradle/gradlew -p <ghidra>/support/gradle buildNatives` (~40 s) |
| `python3: Permission denied` hoặc `python3` không phải venv | Wrapper `scripts/bin/*` mất bit exec khi chép | `in_env.sh` (nạp `tools-env.sh`) tự `chmod +x` mỗi lần chạy; nếu thư mục skill chỉ đọc: `chmod +x <skill>/scripts/bin/*` |
| `Unknown option: -P` | `/usr/bin/python3` của Xcode là 3.9 | Dùng `-I` (skill đã đổi); script hỗ trợ 3.9+ |
| `level-decoders` báo `needs Python >= 3.10` | Pin của UnityPy/pillow/fsspec cần 3.10+ | Chạy lại `ensure_tools.py` bằng `/opt/homebrew/bin/python3` hoặc Python từ python.org |
| "cannot be opened because the developer cannot be verified" / `killed: 9` với tool tải bằng trình duyệt | Gatekeeper gắn `com.apple.quarantine` | Ưu tiên để `ensure_tools.py` tải (không gắn quarantine). Tool tự tải: `xattr -dr com.apple.quarantine <thư mục tool>` |
| `JAVA_HOME` sai / `java` không chạy | JDK macOS có layout bundle | `tools-env.sh` đặt `JAVA_HOME=<root>/jdk-25/Contents/Home` |
| `source tools-env.sh` lỗi trong zsh | Script dựa vào `BASH_SOURCE` | Đừng `source` nó; chạy lệnh qua `bash "<skill>/scripts/in_env.sh" "<workdir>" '<command>'` |

## Il2CppInspectorRedux / Cpp2IL

| Triệu chứng | Xử lý |
|---|---|
| `You must install or update .NET` ... `Microsoft.NETCore.App 10.0.0` | Cần runtime .NET 10 (roll-forward không hạ xuống 8/9). `ensure_tools.py` in lệnh cài user-scope vào `<root>/dotnet`; `tools-env.sh` tự đặt `DOTNET_ROOT` |
| Cùng lỗi nhưng đòi `Microsoft.AspNetCore.App` | Đang chạy `Il2CppInspector.Redux.CLI`; dùng Legacy CLI `Il2CppInspector(.exe)` |
| `Permission denied` khi chạy `Il2CppInspector` (Linux/macOS) | Zip phát hành lưu file 0644; `ensure_tools.py` (post `exec-bits`) và `run_il2cppinspector.sh` tự `chmod +x` |
| `No exact match for IL2CPP APIs found in binary` | Vô hại: chỉ ảnh hưởng C++ scaffolding, không ảnh hưởng `dump.cs`/`script.json` |
| Il2CppDumper: `Metadata file supplied is not a supported version[39]` | Il2CppDumper dừng ở v31. Dùng `run_il2cppinspector.sh`; không sửa version trong header metadata |
| Metadata mới hơn mức Inspector hỗ trợ / crash khi đọc metadata | Cpp2IL; hoặc REA `inspect-il2cpp-metadata` (v24/27/29/31/39) |
| `CodeRegistration`/`MetadataRegistration` không tìm được | `.so` bị pack/mã hoá (kiểm tra triage `protection`) hoặc sai cặp so+metadata. Dump `.so` từ bộ nhớ (Inspector đọc được ELF dump với `--image-base`) |
| `dump.cs` có tên nhưng địa chỉ lệch | `.so` và metadata khác build – lấy cả hai từ cùng một XAPK |
| Vài `StringLiteral` rỗng trong `stringliteral.json` | Inspector cắt literal bắt đầu bằng ký tự `\0` (đo: 30/29 048 chuỗi); tra literal nhị phân trong asset |

## Metadata mã hoá / ẩn

Dấu hiệu: không có magic `AF 1B B1 FA` ở đầu file, file không tồn tại, hoặc version lạ.
1. Tìm trong `assets/`, OBB, Addressables bundle (`unity_triage.py` liệt kê data).
2. Trên thiết bị được phép (root/emulator): Frida hook `il2cpp_init` hoặc `open/mmap` → dump
   vùng metadata sau khi giải mã (magic xuất hiện) → đưa file dump cho dumper.
   Công cụ: `frida-il2cpp-bridge` (hook theo tên class/method), REA `start_frida_session`.
3. Ghi rõ trong báo cáo nguồn gốc file metadata (tĩnh hay dump runtime).

## REA

| Lỗi | Xử lý |
|---|---|
| `unsupported_target: only 64-bit little-endian images` | Binary armv7: dùng `run_il2cppinspector.sh` (REA vẫn đọc được metadata riêng) |
| `provider_timeout` (`ghidra.startup_timeout_ms`, 330 s) khi decompile | REA để Ghidra import + analyze; với lib lớn hãy dùng `ghidra_decompile.sh` của skill. Nếu vẫn dùng REA: `REA_GHIDRA_STARTUP_TIMEOUT_MS=1800000` và tăng timeout phía client; không lặp lại cùng một lời gọi đã timeout |
| `unsupported-pointer-encoding` | Android packed relocations (APS2) – dùng `run_il2cppinspector.sh` |

## AssetRipper

| Triệu chứng | Xử lý |
|---|---|
| Field MonoBehaviour trống | Phải nạp cả APK/XAPK (có `global-metadata.dat` + `libil2cpp.so`) để AssetRipper dựng type tree; không nạp riêng một bundle |
| Thiếu level | Có thể ở Addressables (`assets/aa/`) – vẫn nằm trong export; hoặc tải từ server (cache trên máy: `/sdcard/Android/data/<pkg>/files`) |
| Export chậm | `--mode primary` khi chỉ cần ảnh/âm thanh; `project` khi cần ScriptableObject/prefab/scene |
| `UNCONFIRMED` | Đọc `<out>.assetripper.log`; tìm `Finished post-export` |

## Gộp XAPK thành APK đơn (chỉ khi cần cài lên máy)

```bash
cp base.apk merged.apk && zip -d merged.apk 'META-INF/*.SF' 'META-INF/*.RSA' 'META-INF/MANIFEST.MF'
(cd split && zip -qr -X ../merged.apk lib)
$BT/zipalign -f -p 4 merged.apk aligned.apk && $BT/apksigner sign --ks my.keystore --out out.apk aligned.apk
```
Chữ ký mới ⇒ gỡ bản cũ trước. Có `libpairip`/`com.pairip.application.Application` ⇒ bản ký lại
thường crash khi mở; không phải lỗi gộp. Phân tích tĩnh không bị ảnh hưởng.
