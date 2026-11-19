# Sửa các lỗi review (1–8) + 2 test fail — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa 8 lỗi ưu tiên cao tìm thấy trong lần review ngày 2026-11-19 và 2 test đang fail, mỗi lỗi có test chặn tái phát.

**Architecture:** Mỗi task sửa đúng một script (cộng test và tài liệu liên quan), không đổi kiến trúc skill. Bảo mật tải tool nằm trong `ensure_tools.py`; cổng "done" nằm trong `check_evidence.py`; pipeline decompile chuyển từ "một phiên bash liên tục" sang wrapper `in_env.sh` gọi mỗi bước.

**Tech Stack:** Python 3.9+ (stdlib, `unittest`), bash 3.2+ (macOS `/bin/bash`, Git Bash, Linux), Markdown skill.

**Spec:** Báo cáo review trong hội thoại 2026-11-19 (mục 🔴 1–5, 🟠 6–8 và 2 test fail). Danh sách lỗi được chép vào từng task bên dưới.

## Global Constraints

- Python scripts chạy được trên Python 3.9 (`/usr/bin/python3` của Xcode CLT): không `X | Y` type, không `match`, API ≥3.10 phải có guard.
- Shell scripts chạy được trên bash 3.2 (macOS), Git Bash (Windows) và bash Linux: không mảng kết hợp, không `${v,,}`, không `readarray`, không `sed -i`, không `realpath`.
- Không đổi CLI flag đang có của script (chỉ thêm flag mới).
- `python3 tools/validate_skills.py skills/*` phải in `OK 5 skills` sau mỗi task chạm SKILL.md hoặc `references/`.
- Bash script được gọi qua interpreter trong tài liệu (`bash "<skill>/scripts/x.sh"`), không gọi trần.
- Làm trên branch `fix/review-findings` (tạo từ `main` trước Task 1). Mỗi task một commit; message kết thúc bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Ngoài phạm vi (đừng sửa ở đây): git-bash PATH precedence, lock cho progress.json, decode_probe UTF-16, brace trong string literal của `dump_class.py`, đường chuyển level không phải JSON, path `H:/UGame/ParkingLoop`, validator chạy không tham số.

## Review Focus

1. Archive JDK macOS hợp lệ có symlink tương đối chứa `..` (`Contents/MacOS/libjli.dylib -> ../Home/lib/libjli.dylib`) — siết tar không được làm hỏng cài JDK thật (Task 2 có test dương tính).
2. Đường dẫn work dir có dấu cách hoặc dấu `'` trên macOS, và path Windows có `\` — `paths.env` + `in_env.sh` phải giữ nguyên giá trị (Task 6, Task 7).
3. Agent gọi mỗi bước từ zsh (shell mặc định macOS) trong tool call mới — wrapper phải chạy được và trả về exit code của lệnh bên trong (Task 7).
4. Hai lần decompile cùng work dir với hai `.so` khác nhau (armv7 rồi arm64) — không được dùng lại project cũ (Task 5).
5. `mechanics.md` thật dùng heading theo template `## <Name> (`<short-id>`)`; short-id có dấu `-` hoặc `_` phải được nhận (Task 3).

---

### Task 1: Chọn nguồn tải theo kiến trúc được truyền vào (sửa 2 test fail)

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 0 · Codebase 0 · Rủi ro 0 · Kiểm chứng 0 = **2**
- Luật sàn áp dụng: implementer làm từ mô tả bằng lời → tối thiểu T2
- Tier: **T2** → implementer `sonnet` / `medium`
- Reviewer: spec `sonnet`/`medium`, quality `sonnet`/`high`
- Lý do (1 câu): Thay đổi nhỏ, nhưng là chữ ký hàm dùng bởi Task 2 nên cần làm đúng ngay lần đầu.

**Files:**
- Modify: `skills/recreate-puzzle-gameplay/scripts/ensure_tools.py` (`pick_source` :264, `process_tool` :447, `ensure` :470)
- Test: `skills/recreate-puzzle-gameplay/tests/test_ensure_tools.py`

**Interfaces:**
- Produces: `detect_arch() -> str` (`"arm64"` khi `platform.machine()` là `arm64`/`aarch64`, ngược lại `"x64"`); `pick_source(tool, platform, arch) -> (src, key)`; `process_tool(tool, root, platform, check, fetch, runner, arch)`; `ensure(root, manifest, check=False, fetch=None, platform=None, runner=None, arch=None)` — `arch=None` → `detect_arch()`.

- [ ] **Step 1: Viết test hỏng**

```python
def test_pick_source_uses_given_arch(self):
    tool = {"linux": {"url": "x"}, "linux-arm64": {"url": "a"}, "macos": {"url": "m"}}
    self.assertEqual(ensure_tools.pick_source(tool, "linux", "x64")[1], "linux")
    self.assertEqual(ensure_tools.pick_source(tool, "linux", "arm64")[1], "linux-arm64")
    self.assertEqual(ensure_tools.pick_source(tool, "macos", "arm64")[1], "macos-arm64")
    self.assertEqual(ensure_tools.pick_source(dict(tool, neutral=True), "linux", "arm64")[1], "linux")
    self.assertEqual(ensure_tools.pick_source(tool, "windows", "arm64")[1], "windows")
```

Sửa hai test `test_exec_bits_post_marks_apphost_executable` và `test_exec_bits_post_missing_file_fails`: thêm `arch="x64"` vào lời gọi `ensure_tools.ensure(...)`.

- [ ] **Step 2: Chạy để thấy fail**

Run: `python3 -m unittest discover -s skills/recreate-puzzle-gameplay/tests -k pick_source -k exec_bits`
Expected: FAIL/ERROR (`pick_source()` nhận 2 tham số; `ensure()` không có `arch`).

- [ ] **Step 3: Cài đặt** — thêm `detect_arch`, truyền `arch` từ `ensure` → `process_tool` → `pick_source`; `pick_source` không còn gọi `_platform.machine()`.

- [ ] **Step 4: Chạy toàn bộ suite**

Run: `python3 -m unittest discover -s skills/recreate-puzzle-gameplay/tests`
Expected: `OK` (không còn 2 failure cũ).

- [ ] **Step 5: Commit** — `fix(ensure_tools): pick download source from an explicit arch`

---

### Task 2: Bắt buộc SHA-256 và chặn chuỗi symlink trong tar

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 1 · Codebase 1 · Rủi ro 2 · Kiểm chứng 1 = **7**
- Luật sàn áp dụng: Rủi ro = 2 → ≥T3; bảo mật (tải và giải nén file thực thi) → nâng **T4**
- Tier: **T4** → implementer `opus` / `high`
- Reviewer: spec `opus`/`high`, quality `opus`/`high` (trần T4)
- Lý do (1 câu): Lỗ hổng path traversal có PoC trên Python 3.9; sửa sai sẽ hoặc để lọt hoặc chặn luôn JDK macOS hợp lệ.

**Files:**
- Modify: `skills/recreate-puzzle-gameplay/scripts/ensure_tools.py` (`load_manifest` :56, `extract_tar` :195, `install_archive` :401)
- Test: `skills/recreate-puzzle-gameplay/tests/test_ensure_tools.py`

**Interfaces:**
- Consumes: `ensure(..., arch=...)` từ Task 1.
- Produces: `crosses_symlink(path: str, symlinks: set) -> bool` — đi từng thành phần của `path` (posix, đã ghép với thư mục của member): `"."` bỏ qua, `".."` pop (pop khi rỗng → `True`), thành phần khác push. Trả `True` nếu một prefix **không phải thành phần cuối** nằm trong `symlinks`.

- [ ] **Step 1: Sửa test helper cho hợp lệ khi hash là bắt buộc**

Thêm hàm module-level `pin(tools, fetch)`: với mọi source có `url` mà `sha256` là `None`, đặt `sha256 = sha256(fetch.blobs[url])` nếu `fetch` có `blobs` chứa url, ngược lại `"0" * 64`. Gọi nó trong `EnsureToolsTests.ensure` và trong hai lời gọi `ensure_tools.ensure` trực tiếp của Task 1. Thêm helper `tar_entries(entries)` nhận list `(name, kind, payload)` với `kind` ∈ `"file"`, `"sym"`, `"dir"` (`payload` là bytes cho file, linkname cho sym).

- [ ] **Step 2: Viết test hỏng**

```python
def test_unpinned_url_refused_without_fetch(self):
    url = "https://x.invalid/t.zip"
    fetch = FakeFetch({url: zip_bytes({"t-1/bin/tool.txt": b"1"})})
    res = ensure_tools.ensure(self.root, {"schema": 1, "tools": [entry("t", "t-1", url)]},
                              fetch=fetch, platform="windows")          # no pin()
    self.assertEqual(res["tools"]["t"]["status"], "failed")
    self.assertIn("sha256", res["tools"]["t"]["detail"])
    self.assertEqual(fetch.calls, [])

def test_load_manifest_rejects_url_without_sha256(self):
    # write a manifest file whose only url source has no sha256/sha256_source
    # -> assertRaises(ValueError) mentioning "sha256"

def test_tar_symlink_chain_rejected(self):
    # entries: ("x","sym","."), ("x/y","sym",".."), ("y/pwned.txt","file",b"p")
    # -> status "failed"; no pwned.txt anywhere under self.tmp outside root; no "*.partial" left

def test_tar_link_target_through_symlink_rejected(self):
    # entries: ("t-1/x","sym","."), ("t-1/z","sym","x/../../evil"), ("t-1/bin/tool.txt","file",b"1")
    # -> status "failed"

@unittest.skipIf(os.name == "nt", "symlink extraction needs privileges on Windows")
def test_tar_relative_symlink_like_macos_jdk_installs(self):
    # entries: ("jdk/Contents/Home/lib/libjli.dylib","file",b"l"),
    #          ("jdk/Contents/MacOS/libjli.dylib","sym","../Home/lib/libjli.dylib"),
    #          ("jdk/bin/tool.txt","file",b"1")   with detect ["bin/tool.txt"]
    # -> status "installed"; os.path.islink(<root>/<folder>/Contents/MacOS/libjli.dylib)
```

Xoá `test_null_sha_records_computed_hash` (hành vi đó bị cấm).

- [ ] **Step 3: Chạy để thấy fail**

Run: `python3 -m unittest discover -s skills/recreate-puzzle-gameplay/tests -k sha256 -k unpinned -k symlink`
Expected: các test mới FAIL (chuỗi symlink còn lọt trên Python không có `tarfile.data_filter`; trên 3.12+ `test_tar_symlink_chain_rejected` có thể đã pass nhờ filter — chấp nhận, test vẫn giữ để bảo vệ 3.9).

- [ ] **Step 4: Cài đặt**
  - `load_manifest`: source có `url` mà thiếu `sha256` → `ValueError("manifest: %s/%s has a url but no sha256")`.
  - `install_archive`: nếu `src.get("sha256")` rỗng → `result("failed", ..., "no pinned sha256 for <url>; refusing an unverified download")` **trước** khi fetch. Xoá nhánh `"computed; manifest has no pinned hash"`.
  - `extract_tar`: lượt 1 gom `symlinks = {safe_relpath(m.name) for m in members if m.issym()}`. Lượt 2 (vòng kiểm tra hiện có): từ chối (`UnsafeArchive`) member có `crosses_symlink(rel, symlinks)`; symlink có `crosses_symlink(dirname(rel) + "/" + linkname, symlinks)`; hardlink có `crosses_symlink(linkname, symlinks)`. Giữ nguyên các kiểm tra `contained()` hiện có.

- [ ] **Step 5: Chạy toàn bộ suite trên cả hai Python**

Run: `python3 -m unittest discover -s skills/recreate-puzzle-gameplay/tests && /usr/bin/python3 -m unittest discover -s skills/recreate-puzzle-gameplay/tests`
Expected: cả hai `OK`. Rồi `python3 skills/recreate-puzzle-gameplay/scripts/ensure_tools.py --check --root "$(mktemp -d)"` không báo lỗi manifest (exit 3 vì thiếu tool là đúng; exit 1 kèm `manifest:` là sai).

- [ ] **Step 6: Commit** — `fix(ensure_tools): require pinned sha256 and reject tar paths through symlinks`

---

### Task 3: `check_evidence --strict` đòi đủ từng check và từng mechanic

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 1 · Codebase 1 · Rủi ro 1 · Kiểm chứng 0 = **5**
- Luật sàn áp dụng: không (đã ≥T2)
- Tier: **T2** → implementer `sonnet` / `medium`
- Reviewer: spec `sonnet`/`medium`, quality `sonnet`/`high`
- Lý do (1 câu): Spec rõ, có test harness sẵn; cần khớp định dạng `mechanics.md` và `ModelContractRunner`.

**Files:**
- Modify: `skills/puzzle-gameplay-verification/scripts/check_evidence.py`
- Modify: `skills/puzzle-gameplay-verification/SKILL.md` (Procedure bước 5), và mọi lệnh `check_evidence.py --strict` trong `references/unity-control.md`, `templates/verification-report.md`, `skills/recreate-puzzle-gameplay/templates/handoff.md`, `skills/recreate-puzzle-gameplay/templates/game-notes/SKILL.md.txt` (tìm bằng `grep -rn "check_evidence.py" skills`)
- Test: `skills/puzzle-gameplay-verification/tests/test_check_evidence.py`

**Interfaces:**
- Produces:
  - `STRICT_CHECK_IDS = ["switch-next", "switch-previous", "switch-next-wrap", "switch-previous-wrap", "switch-retry-resets", "switch-clears-input", "ui-blocks-gameplay", "sample-win", "console"]` (đúng các id `PointerSmoke.cs.txt` ghi ra)
  - `COVERAGE_CASES = ("accept", "reject", "boundary")` (đúng `ModelContractRunner.cs.txt`)
  - `MECHANIC_HEADING = re.compile(r"^##\s+.*\(`([A-Za-z0-9_.-]+)`\)\s*$")` (template `mechanic-entry.md`)
  - `read_mechanic_ids(path) -> (list, list)` trả `(ids, problems)`; file thiếu hoặc không có heading nào → problem.
  - Flag mới `--mechanics FILE`; `"mechanics"` thêm vào `DIMENSIONS` và `STRICT_REQUIRED`.

- [ ] **Step 1: Viết test hỏng**

Cập nhật `ALL_DIMENSIONS` thêm `"mechanics"`. Thêm helper `make_mechanics(ids)` ghi `## Name (`<id>`)` cho mỗi id; mở rộng `make_model()` mặc định để có `coverage.ice.{accept,reject,boundary}\tPASS`. Cập nhật `test_strict_with_everything_passes` và `test_documented_strict_command_passes_with_nothing_skipped` để report có đủ `STRICT_CHECK_IDS` + `mechanic-ice`, truyền `--mechanics`, và kiểm SKILL.md có `--mechanics`. Test mới:

```python
def test_strict_missing_one_switch_id_fails(self):      # report lacks switch-previous-wrap
    ... self.assertFailsWith(result, "switch-previous-wrap")

def test_mechanic_without_probe_line_fails(self):       # mechanics: ice, rope; report has only mechanic-ice
    ... self.assertFailsWith(result, "mechanic-rope")

def test_model_missing_coverage_case_fails(self):       # model lacks coverage.ice.boundary
    ... self.assertFailsWith(result, "coverage.ice.boundary")

def test_mechanics_file_without_headings_fails(self):
    ... self.assertFailsWith(result, "short-id")

def test_strict_requires_mechanics_flag(self):          # usage error exit 2 mentioning --mechanics
```

- [ ] **Step 2: Chạy để thấy fail**

Run: `python3 -m unittest discover -s skills/puzzle-gameplay-verification/tests`
Expected: các test mới và hai test strict được cập nhật FAIL.

- [ ] **Step 3: Cài đặt** — trong `check()`: đọc mechanic ids một lần; với `--strict` mọi id trong `STRICT_CHECK_IDS` phải có trong `passed_ids`; mỗi mechanic id cần PASS `mechanic-<id>` trong report; khi có `--model`, `check_model` gom id PASS và đòi `coverage.<id>.<case>` cho mọi id × `COVERAGE_CASES`. Thông báo lỗi chứa nguyên id thiếu.

- [ ] **Step 4: Cập nhật tài liệu** — thêm `--mechanics <dir>/evidence/mechanics.md` vào lệnh judge ở SKILL.md bước 5 và các file đã liệt kê; bước 4 của SKILL.md ghi rõ `--strict` đòi đủ 6 id `switch-*`, `ui-blocks-gameplay`, `sample-win`, `console` và `mechanic-<id>` cho mọi short-id.

- [ ] **Step 5: Kiểm chứng**

Run: `python3 -m unittest discover -s skills/puzzle-gameplay-verification/tests && python3 tools/validate_skills.py skills/*`
Expected: `OK`, `OK 5 skills`.

- [ ] **Step 6: Commit** — `fix(check_evidence): strict mode requires every switch check, mechanic probe and coverage case`

---

### Task 4: `dump_class.py --offset` không lặp vô hạn khi base trùng tên

**Routing**
- Điểm: Phạm vi 1 · Spec 0 · Phán đoán 0 · Codebase 0 · Rủi ro 0 · Kiểm chứng 0 = **1**
- Luật sàn áp dụng: không (thuật toán được cho sẵn bên dưới)
- Tier: **T1** (nâng từ T0 vì phải viết fixture test) → implementer `haiku` / `medium`
- Reviewer: spec `sonnet`/`medium` (sàn T2), quality `sonnet`/`medium` (sàn T2)
- Lý do (1 câu): Một vòng lặp trong một file, thuật toán đã định.

**Files:**
- Modify: `skills/unity-apk-decompile/scripts/dump_class.py:98-109`
- Test: `skills/unity-apk-decompile/tests/test_dump_class.py`

- [ ] **Step 1: Viết test hỏng** — thêm `timeout=10` vào `subprocess.run` trong helper `run()`. Fixture Il2CppDumper-style (cùng layout `DUMPER` sẵn có):
  - `// Namespace: Game` / `public class Button : Button // TypeDefIndex: 9` có field `// 0x40` → `test_offset_self_named_base_stops`: `run(path, "--offset", "Button", "0x10")` trả `rc == 1` và stdout chứa `"loops"`.
  - Thêm vào cùng fixture `// Namespace: UnityEngine.UI` / `public class Button : Selectable` có field `// 0x10` **đặt sau** `Game.Button` → `test_offset_resolves_same_name_base_in_other_namespace`: `run(path, "--offset", "Button", "0x10")` trả `rc == 0`, stdout chứa tên field của `UnityEngine.UI.Button`, và stderr cảnh báo `2 classes named Button`. (Helper `run` cần trả thêm stderr; cập nhật các lời gọi cũ.)

- [ ] **Step 2: Chạy để thấy fail** — `python3 -m unittest discover -s skills/unity-apk-decompile/tests -k offset` → test đầu TIMEOUT (`subprocess.TimeoutExpired`).

- [ ] **Step 3: Cài đặt**

```python
visited, first = set(), True
while name:
    all_hits = find(lines, name)
    hits = [h for h in all_hits if (h[0], h[1]) not in visited]
    if not hits:
        print(f"{name}: not found" if not all_hits else
              f"base chain loops back to {name}; the real base is probably a {name} from another assembly not in this dump")
        return 1
    if first and len(hits) > 1:
        print(f"warning: {len(hits)} classes named {name}; using {hits[0][0] or 'global namespace'}", file=sys.stderr)
    first = False
    ns, n, b, block = hits[0]
    visited.add((ns, n))
    ... (field lookup unchanged) ...
    name = base_name(b)
```

- [ ] **Step 4: Chạy suite** — `python3 -m unittest discover -s skills/unity-apk-decompile/tests` → `OK`.

- [ ] **Step 5: Commit** — `fix(dump_class): stop --offset when the base chain revisits a class`

---

### Task 5: `ghidra_decompile.sh` — project theo hash của `.so` và exit status trung thực

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 1 · Codebase 1 · Rủi ro 1 · Kiểm chứng 1 = **6**
- Luật sàn áp dụng: không
- Tier: **T2** → implementer `sonnet` / `medium`
- Reviewer: spec `sonnet`/`medium`, quality `sonnet`/`high`
- Lý do (1 câu): Bash portable + test stub cho analyzeHeadless, spec rõ.

**Files:**
- Modify: `skills/unity-apk-decompile/scripts/ghidra_decompile.sh`
- Create: `skills/unity-apk-decompile/tests/test_ghidra_decompile.sh`
- Modify: `skills/unity-apk-decompile/SKILL.md` (đoạn "Mở rộng mục tiêu": project giờ tên `il2cpp-<sha12>`), `README.md` (Self-check thêm dòng `bash .../tests/test_ghidra_decompile.sh`)

**Interfaces:**
- Produces: project `$WORK/ghidra-project/il2cpp-<12 hex đầu của sha256(.so)>`; exit 0 chỉ khi `_index.tsv` không rỗng và mọi dòng có cột 3 đúng bằng `OK`; exit 1 kèm thông báo khi thiếu index hoặc có dòng không OK (in số dòng lỗi / tổng).

- [ ] **Step 1: Viết test hỏng** — `test_ghidra_decompile.sh` theo khuôn `test_tools_env.sh` (đếm `pass`/`total`, in `PASS n/n`). Dựng `$TMP/gh/support/analyzeHeadless` giả: ghi `"$@"` vào `$STUB_LOG`; đọc out-dir là đối số ngay sau `DecompileIl2cppTargets.java`; theo `STUB_MODE` ghi `_index.tsv`: `ok` → `A\t0x1\tOK`, `fail` → `UIOKButton\t0x2\tFAIL`, `none` → không ghi và `exit 1`. Trên Darwin tạo thêm `$TMP/gh/Ghidra/Features/Decompiler/os/mac_x86_64/decompile` (chmod +x). Tạo ELF giả 20 byte bằng `python3 -I -c` (byte 4 = 2, u16 LE tại 18 = 183) và `targets.tsv` một dòng. Các case:
  1. `ok` lần đầu → exit 0, log có `-import` và `il2cpp-<hash>`.
  2. `ok` lần hai cùng `.so` → log có `-process`.
  3. `.so` khác (đổi 1 byte cuối) cùng work dir → log có `-import` với tên project khác.
  4. `fail` → exit 1.
  5. Có `_index.tsv` cũ toàn `OK` từ lần trước, `none` → exit 1.

- [ ] **Step 2: Chạy để thấy fail** — `bash skills/unity-apk-decompile/tests/test_ghidra_decompile.sh` → `FAIL case3 case4 case5`.

- [ ] **Step 3: Cài đặt** — tính sha256 bằng `python3 -I` (đọc theo khối 1 MiB, bỏ `\r` như dòng `MACH`), `NAME="il2cpp-${SHA:0:12}"`; `rm -f "$OUT/_index.tsv"` trước khi gọi Ghidra; thay `grep -q "OK"` bằng kiểm tra từng dòng bằng `awk -F'\t' '$3 != "OK"'`. Giữ `|| true` sau lời gọi Ghidra (exit status giờ do index quyết định).

- [ ] **Step 4: Kiểm chứng** — chạy lại test → `PASS 5/5`; `bash skills/unity-apk-decompile/tests/test_tools_env.sh` → `PASS 10/10`; `python3 tools/validate_skills.py skills/*` → `OK 5 skills`.

- [ ] **Step 5: Commit** — `fix(ghidra_decompile): key the project by .so hash and fail unless every target is OK`

---

### Task 6: `paths.env` quote đầy đủ và chuẩn hoá path

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 0 · Codebase 0 · Rủi ro 1 · Kiểm chứng 0 = **3**
- Luật sàn áp dụng: implementer làm từ mô tả bằng lời → tối thiểu T2
- Tier: **T2** → implementer `sonnet` / `medium`
- Reviewer: spec `sonnet`/`medium`, quality `sonnet`/`high`
- Lý do (1 câu): Nhỏ nhưng là đầu vào của Task 7; quoting shell dễ sai tinh vi.

**Files:**
- Modify: `skills/unity-apk-decompile/scripts/unity_triage.py:154-160`
- Create: `skills/unity-apk-decompile/tests/test_unity_triage.py`

**Interfaces:**
- Produces: `sh_quote(s: str) -> str` (bọc `'…'`, `'` → `'\''`); `paths_env_text(out: str, lib: Optional[str], meta: Optional[str]) -> str` — các dòng `W=…`, `SO=…`, `META=…` (bỏ dòng khi giá trị `None`), mọi giá trị qua `sh_quote(p.replace("\\", "/"))`.

- [ ] **Step 1: Viết test hỏng** — load module bằng `importlib.util.spec_from_file_location`. Với mỗi bộ dữ liệu, ghi `paths_env_text(...)` ra file rồi chạy `bash -c 'source "$1"; printf "%s|%s|%s" "$W" "$SO" "${META-unset}"' _ <file>`:
  - `("/tmp/My Games/it's", "/x/lib il2cpp.so", None)` → `"/tmp/My Games/it's|/x/lib il2cpp.so|unset"`
  - `("H:\\UGame\\work", "H:\\UGame\\work\\unpacked\\libil2cpp.so", "H:\\m.dat")` → `"H:/UGame/work|H:/UGame/work/unpacked/libil2cpp.so|H:/m.dat"`

- [ ] **Step 2: Chạy để thấy fail** — `python3 -m unittest discover -s skills/unity-apk-decompile/tests -k triage` → ERROR (`paths_env_text` chưa có).

- [ ] **Step 3: Cài đặt** — thêm hai hàm, `main()` ghi `paths.env` bằng `paths_env_text(str(out), …)`.

- [ ] **Step 4: Chạy suite** — `python3 -m unittest discover -s skills/unity-apk-decompile/tests` → `OK`.

- [ ] **Step 5: Commit** — `fix(unity_triage): quote every paths.env value and normalise separators`

---

### Task 7: Wrapper `in_env.sh` — mỗi bước decompile chạy độc lập với shell của agent

**Routing**
- Điểm: Phạm vi 1 · Spec 1 · Phán đoán 1 · Codebase 1 · Rủi ro 1 · Kiểm chứng 1 = **6**
- Luật sàn áp dụng: không
- Tier: **T2** → implementer `sonnet` / `medium`
- Reviewer: spec `sonnet`/`medium`, quality `sonnet`/`high`
- Lý do (1 câu): Script ngắn nhưng phải viết lại khối lệnh chính của SKILL.md và đồng bộ 3 file tài liệu.

**Files:**
- Create: `skills/unity-apk-decompile/scripts/in_env.sh`
- Create: `skills/unity-apk-decompile/tests/test_in_env.sh`
- Modify: `skills/unity-apk-decompile/SKILL.md:35-57` và mọi lệnh `$SK/…`/`$W/…` trong phần còn lại; `references/troubleshooting.md:28`; `skills/recreate-puzzle-gameplay/references/compatibility.md:112-114`; `skills/recreate-puzzle-gameplay/references/run-layout.md:111`

**Interfaces:**
- Consumes: `paths.env` dạng quote của Task 6.
- Produces: `bash "<skill>/scripts/in_env.sh" <workdir> '<command>'` — source `tools-env.sh` (thoát với exit code của nó nếu lỗi); source `<workdir>/paths.env` nếu có; export `W` (mặc định `<workdir>`), `SO`, `META` (mặc định rỗng), `SK`; rồi `exec bash -c "<command>"`. Sai số đối số → usage ra stderr, exit 2. Không bật `set -u` trước khi source `tools-env.sh`.

- [ ] **Step 1: Viết test hỏng** — khuôn `test_tools_env.sh`. Setup `UNITY_DECOMPILE_TOOLS=$TMP/t1` (có `ghidra-12.2/`), workdir `"$TMP/My Work"` với `paths.env` chứa `W='…/My Work'` và `SO='/x/lib il2cpp.so'`. Case:
  1. `bash in_env.sh "$TMP/My Work" 'printf "%s|%s" "$W" "$SO"'` → `…/My Work|/x/lib il2cpp.so`.
  2. Như case 1 nhưng gọi từ `zsh -c '…'` khi có `zsh` (không có → tính pass).
  3. `'exit 7'` → exit code 7.
  4. `UNITY_DECOMPILE_TOOLS=/nonexistent` → exit ≠ 0 và stderr chứa `no tool directory`.
  5. Workdir chưa có `paths.env` → `$W` bằng workdir truyền vào, `$SK` trỏ tới thư mục `scripts`.
  6. Một đối số → exit 2.

- [ ] **Step 2: Chạy để thấy fail** — `bash skills/unity-apk-decompile/tests/test_in_env.sh` → fail (file chưa có).

- [ ] **Step 3: Cài đặt `in_env.sh`.**

- [ ] **Step 4: Viết lại tài liệu** — SKILL.md: một câu nói mỗi tool call là shell mới (trên macOS thường là zsh) nên mọi bước chạy qua `bash "<this skill directory>/scripts/in_env.sh" "<workdir>" '<command>'`, biến bên trong nháy đơn và luôn quote (`"$W"`, `"$SO"`, `"$META"`, `"$SK"`). Viết lại khối lệnh bước 1–6 theo dạng đó (bước 1 dùng workdir mới làm đối số). Thay hướng dẫn `bash -c 'source …/tools-env.sh && …'` ở troubleshooting/compatibility/run-layout bằng `in_env.sh`.

- [ ] **Step 5: Kiểm chứng** — `bash skills/unity-apk-decompile/tests/test_in_env.sh` → `PASS 6/6`; `python3 tools/validate_skills.py skills/*` → `OK 5 skills`; `grep -n 'source .*tools-env.sh' skills/*/SKILL.md skills/*/references/*.md` chỉ còn mô tả nội bộ của wrapper (không còn hướng dẫn agent tự source).

- [ ] **Step 6: Commit** — `fix(unity-apk-decompile): run each step through in_env.sh instead of a persistent shell`

---

### Task 8: Bỏ `GHIDRA_HEADLESS_MAXMEM=4G` cứng trong `tools-env.sh`

**Routing**
- Điểm: Phạm vi 1 · Spec 0 · Phán đoán 0 · Codebase 0 · Rủi ro 0 · Kiểm chứng 0 = **0**
- Luật sàn áp dụng: không (code cho sẵn)
- Tier: **T0** → implementer `haiku` / `low`
- Reviewer: spec `sonnet`/`medium` (sàn T2), quality `sonnet`/`medium` (sàn T2)
- Lý do (1 câu): Xoá một dòng và thêm một case test đã viết sẵn.

**Files:**
- Modify: `skills/unity-apk-decompile/scripts/tools-env.sh:73` (xoá dòng)
- Test: `skills/unity-apk-decompile/tests/test_tools_env.sh`

- [ ] **Step 1: Viết test hỏng** — đổi `total=10` thành `total=12`, thêm trước khối kết quả:

```bash
# case11: a value the user exported survives sourcing
out=$( (export UNITY_DECOMPILE_TOOLS="$TMP/t1" GHIDRA_HEADLESS_MAXMEM=12G; source "$ENVSH" 2>/dev/null; echo "$GHIDRA_HEADLESS_MAXMEM") )
[ "$out" = "12G" ] && ok || bad case11
# case12: unset stays unset so ghidra_decompile.sh applies its 16G default
out=$( (unset GHIDRA_HEADLESS_MAXMEM; export UNITY_DECOMPILE_TOOLS="$TMP/t1"; source "$ENVSH" 2>/dev/null; echo "${GHIDRA_HEADLESS_MAXMEM-unset}") )
[ "$out" = "unset" ] && ok || bad case12
```

- [ ] **Step 2: Chạy để thấy fail** — `bash skills/unity-apk-decompile/tests/test_tools_env.sh` → `FAIL case11 case12`.

- [ ] **Step 3: Xoá dòng `export GHIDRA_HEADLESS_MAXMEM=4G`.**

- [ ] **Step 4: Kiểm chứng** — chạy lại → `PASS 12/12`; `grep -n MAXMEM skills/unity-apk-decompile/SKILL.md skills/unity-apk-decompile/references/troubleshooting.md` vẫn nói mặc định `16G` (giờ đã đúng sự thật).

- [ ] **Step 5: Commit** — `fix(tools-env): stop overriding GHIDRA_HEADLESS_MAXMEM`

---

### Task 9: Kiểm chứng toàn nhánh

**Routing**
- Tier: **T4** → reviewer cuối nhánh `opus` / `high` (theo CLAUDE.md: review cuối toàn nhánh luôn T4)

- [ ] **Step 1: Chạy mọi suite trên Python mặc định và Python 3.9**

```bash
for py in python3 /usr/bin/python3; do
  for d in skills/*/tests tools; do $py -m unittest discover -s $d || echo "FAIL $py $d"; done
done
for t in skills/unity-apk-decompile/tests/*.sh; do bash "$t" || echo "FAIL $t"; done
python3 tools/validate_skills.py skills/*
```

Expected: không dòng `FAIL`; `OK 5 skills`.

- [ ] **Step 2: Review toàn nhánh** (`git diff main...HEAD`) bằng reviewer `opus`/`high`.
- [ ] **Step 3: Cập nhật `docs/routing-ledger.md`** — mỗi task một dòng (tier dự kiến/thực tế, số lần leo thang, kết quả) và 2–3 dòng nhận xét cuối plan.

---

## Ledger

Ghi vào `docs/routing-ledger.md` (mục "2026-11-19 — Sửa lỗi review").

| Task | Điểm | Tier dự kiến | Tier thực tế | Số lần leo thang | Kết quả | Ghi chú |
|------|------|--------------|--------------|------------------|---------|---------|
| 1 | 2 | T2 | | | | |
| 2 | 7 | T4 | | | | |
| 3 | 5 | T2 | | | | |
| 4 | 1 | T1 | | | | |
| 5 | 6 | T2 | | | | |
| 6 | 3 | T2 | | | | |
| 7 | 6 | T2 | | | | |
| 8 | 0 | T0 | | | | |
| 9 | — | T4 | | | | review cuối |
