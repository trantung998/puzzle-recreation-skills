# Bộ skill tái tạo gameplay game puzzle Unity từ APK — Thiết kế

Ngày: 2026-11-17
Nguồn kinh nghiệm: `parkingloop-recreate-mechanics` (workflow bằng chứng, kiểm chứng)
và `unity-apk-decompile` (công cụ dịch ngược).

## 1. Ý định

Người dùng có một game puzzle Unity Android (APK/XAPK/APKS/APKM) và muốn có phần
gameplay **chơi được, nhìn và cảm giác giống bản gốc** bên trong một project Unity
của họ, cho **N level đầu tiên**, kèm khả năng **chuyển nhanh giữa các level**.

Kinh nghiệm từ Parking Loop cho thấy: agent dễ đoán luật thay vì lấy từ bằng chứng,
dễ coi một PASS cũ là kết quả hiện tại, dễ sửa visual bằng hằng số che lỗi. Bộ skill
này đóng gói quy trình đã chứng minh hiệu quả ở Parking Loop thành dạng tổng quát,
dùng được cho mọi game puzzle Unity.

## 2. Đầu vào / đầu ra

**Bắt buộc**
- Đường dẫn file APK/XAPK/APKS/APKM.
- Số level N.
- Đường dẫn project Unity đích (có thể đã có nội dung khác).

**Tuỳ chọn**
- Ảnh và/hoặc video gameplay gốc.

**Đầu ra**
- Trong project Unity: thư mục `Assets/<GameSlug>/` chứa scene gameplay, code
  runtime/editor, dữ liệu level gốc, asset đã import, công cụ kiểm chứng.
- Ngoài `Assets/`: thư mục làm việc chứa output decompile, bảng bằng chứng, báo cáo
  kiểm chứng, ảnh chụp, file tiến độ.
- Một skill ghi chú riêng cho game: `<project>/.agents/skills/<game-slug>-notes/SKILL.md`,
  đóng vai trò như `parkingloop-recreate-mechanics` cho game đó.
- Báo cáo bàn giao cuối (xem §8).

## 3. Mục tiêu, không mục tiêu, phản mục tiêu

**Mục tiêu**
- Visual của mọi thành phần gameplay giống bản gốc (mesh, sprite, material, màu,
  bố cục board, UI trong màn chơi).
- Đủ mọi cơ chế mà N level đó dùng; luật lấy từ bằng chứng gốc.
- VFX, SFX, shader, animation giống nhất có thể; dùng asset gốc khi trích được.
- Khi không có ảnh/video: tự tìm thông số logic/visual trong chính bản build
  (asset, prefab, material, AnimationClip, AudioClip, ParticleSystem, ScriptableObject,
  code native).
- Chuyển level nhanh: chọn level bất kỳ, next, prev, retry; trạng thái reset sạch.
- Tự chạy một mạch từ đầu đến bàn giao.

**Không mục tiêu**
- Store, IAP, quảng cáo, tài khoản, live event, meta-progression, lưu tiến độ người chơi.
- Biến thể level A/B test hoặc event (ví dụ hậu tố `_z`); chỉ lấy level cơ bản.
- Build standalone/thiết bị (không cấm, nhưng không phải điều kiện xong).
- Bộ giải tự động cho mọi level.

**Phản mục tiêu (chạy được nhưng vẫn là thất bại)**
- Luật đoán ra nhưng ghi như sự thật gốc; giá trị *Inferred* không được đánh dấu.
- Gọi shader dummy của AssetRipper là shader gốc, hoặc tuyên bố output shader y hệt.
- Import controller gameplay gốc đã dịch ngược làm logic thay vì tái tạo.
- Diễn giải dữ liệu vượt quá cái mà code gốc thực sự dùng (ví dụ phần tử vượt capacity).
- Sửa/ghi đè nội dung có sẵn của project đích, scene người dùng đang sửa, GUID/`.meta`.
- Báo PASS từ thư mục rỗng, lệnh mới chỉ được xếp hàng, hoặc kết quả của lần chạy trước.
- Che lỗi bằng retry, clamp, material dự phòng, xoay thêm khi chưa rõ nguyên nhân.

## 4. Định nghĩa "xong"

Chỉ tính kết quả của **lần chạy cuối, trên code và asset cuối**.

1. Mỗi level trong N: load không lỗi; số lượng, loại, vị trí, thuộc tính phần tử khớp
   dữ liệu gốc (so sánh ngữ nghĩa sau decode, không chỉ hash byte).
2. Mỗi cơ chế xuất hiện trong một level đều được tương tác ít nhất một lần bằng
   **input thật** (Unity Input System pointer event qua raycast/collider thật).
   Gọi hàm trực tiếp chỉ là setup, không tính là tương tác.
3. Một level mẫu được chơi tới màn thắng bằng input thật. Chuỗi thao tác lấy từ
   video nếu có; không thì agent tự tìm lời giải cho level đó.
4. Mỗi cơ chế có model contract độc lập (kể cả trường hợp bị từ chối và biên);
   kết quả mong đợi lấy từ bằng chứng gốc, không từ code vừa viết.
5. Ảnh chụp từng level ở dọc và ngang; có ảnh/video thì đặt cạnh nhau để so;
   không có thì so với prefab/asset gốc render trong Unity.
6. Chuyển level: chọn bất kỳ, next/prev (kể cả quay vòng ở hai đầu), retry; reset
   sạch trạng thái, input đang chờ, booster/inventory theo level.
7. Compile sạch; console cuối không có lỗi (cảnh báo được liệt kê).

## 5. Cấu trúc bộ skill

| Skill | Vai trò | Ghi chú |
|---|---|---|
| `recreate-puzzle-gameplay` | Điểm vào và điều phối: nhận đầu vào, tạo thư mục làm việc, chạy các pha, giữ file tiến độ, bàn giao | Mới |
| `unity-apk-decompile` | Triage, Il2CppDumper/ILSpy, Ghidra có mục tiêu, AssetRipper | Có sẵn, tái sử dụng; cần chuyển lên global (§9) |
| `puzzle-evidence-extraction` | Từ output decompile rút ra: danh mục level, schema, luật cơ chế, thông số visual/VFX/SFX/shader/animation, kèm nhãn bằng chứng | Mới |
| `puzzle-gameplay-build` | Dựng vào project Unity: kiến trúc model/view, loader, level switcher, import asset, tái tạo shader/VFX | Mới |
| `puzzle-gameplay-verification` | Model contract, pointer smoke, level mẫu tới thắng, ảnh so sánh, kiểm tra độ mới của bằng chứng | Mới |

Mỗi skill dùng được độc lập (ví dụ chỉ chạy verification lại), nhưng bình thường chỉ
cần gọi `recreate-puzzle-gameplay`.

Skill khác được tham chiếu bằng ID, có đường fallback nếu không cài:
`unity-pipeline` / `unity-cli` (điều khiển Editor), `test-driven-development`,
`verification-before-completion`, `systematic-debugging`, các skill UI (`ui-ugui`…),
`reverse-engineer-anything` (REA, tuỳ chọn).

### 5.1 Hợp đồng file giữa các skill

Các skill giao tiếp qua file trong thư mục làm việc, không qua trí nhớ hội thoại,
để chạy lại hoặc tiếp tục sau khi bị ngắt.

Thư mục làm việc mặc định: `<thư mục chứa APK>/<GameSlug>-recreation/`

```text
<GameSlug>-recreation/
|-- progress.json            # pha hiện tại, trạng thái từng pha, đầu vào, hash APK
|-- decisions.md             # mọi lựa chọn Inferred tự quyết, kèm lý do
|-- decompile/               # output unity-apk-decompile (tái sử dụng nếu cùng SHA-256)
|-- evidence/
|   |-- levels/manifest.json # N level đã chọn: tên, path ID, nguồn, hash raw/decoded
|   |-- levels/*.json        # dữ liệu level đã decode, giữ tên field gốc
|   |-- mechanics.md         # mỗi cơ chế: luật, nhãn bằng chứng, nguồn chính xác
|   |-- visuals.md           # mesh/sprite/material/shader/VFX/SFX/animation: nguồn, GUID, thông số
|   `-- native/              # pseudocode của các method đã decompile
|-- checks/<run-id>/         # mỗi lần kiểm chứng một thư mục mới
`-- handoff.md               # báo cáo bàn giao
```

Bảng bằng chứng dùng bốn nhãn của Parking Loop:

| Nhãn | Nghĩa |
|---|---|
| Proven | Byte gốc, schema, nhánh native, prefab hoặc khung hình tham chiếu chứng minh đúng khẳng định đó |
| Observed | Khung hình/video gốc hoặc tương tác Unity hiện tại cho thấy hành vi; ghi rõ là cái nào |
| Inferred | Lựa chọn tái tạo giải thích được bằng chứng nhưng không phải hành vi gốc đã khôi phục |
| Unknown | Thiếu, mâu thuẫn hoặc không đủ bằng chứng |

## 6. Các pha (do `recreate-puzzle-gameplay` điều phối)

1. **Tiếp nhận**: kiểm tra đầu vào, hash APK, đọc project đích (phiên bản Unity, render
   pipeline, Input System, package, scene đang mở/dirty), tạo/đọc `progress.json`.
2. **Dịch ngược** (`unity-apk-decompile`): triage → ROUTE (Mono/IL2CPP, ABI) → metadata →
   AssetRipper. Tái sử dụng nếu đã có cho cùng SHA-256.
3. **Danh mục level** (`puzzle-evidence-extraction`): tìm nơi chứa level (ScriptableObject,
   TextAsset, JSON nén/mã hoá, asset pack split), xác định thứ tự gốc, chọn N level cơ bản
   đầu tiên theo đúng tên/path ID, decode và lưu.
4. **Kiểm kê cơ chế**: từ dữ liệu N level, liệt kê mọi cơ chế/trường được dùng; với mỗi
   cơ chế, decompile có mục tiêu các method native liên quan và rút ra luật.
5. **Kiểm kê visual/âm thanh**: với mỗi thành phần: prefab đang hoạt động, mesh/sprite qua
   GUID, material và giá trị runtime, shader (ghi rõ khi phải tái tạo), ParticleSystem,
   AnimationClip/curve/timing, AudioClip và lúc phát; camera, bố cục board, UI trong màn.
6. **Dựng** (`puzzle-gameplay-build`): model chứa luật, view chứa trình bày, loader đọc
   dữ liệu gốc, level switcher, import asset tối thiểu cần thiết, HUD trong màn.
7. **Kiểm chứng** (`puzzle-gameplay-verification`): theo §4; lỗi thì quay lại pha 6 với
   `systematic-debugging`, không nới lỏng assertion.
8. **Ghi chú game**: sinh `<game-slug>-notes` skill (bản đồ nguồn, quy ước, bài học).
9. **Bàn giao**: `handoff.md` và tóm tắt trong chat.

Mỗi pha cập nhật `progress.json` khi xong. Khi khởi động lại, đọc file này, kiểm tra
đầu vào của pha đã xong còn khớp (hash), rồi làm tiếp.

## 7. Tự chạy và điểm dừng

- Không hỏi người dùng giữa chừng. Chỗ không chắc: chọn phương án hợp lý nhất, ghi
  `Inferred` vào `decisions.md` kèm lý do, đi tiếp.
- Thiếu tool thì **chủ động cài** (người dùng chọn), theo §7.1.
- Chỉ dừng sớm khi thật sự bị chặn: metadata bị mã hoá/bảo vệ mà không dump được,
  thiếu tool mà cài tự động thất bại, Unity không mở/compile được project, hoặc không tìm thấy
  dữ liệu level. Khi dừng: bàn giao những gì đã xong, nêu chính xác chỗ bị chặn và
  cách gỡ.
- Không commit, stash, reset git của người dùng.

### 7.1 Tự cài tool

- Một script Python (`ensure_tools.py`, thuộc `recreate-puzzle-gameplay`) phát hiện và cài
  tool còn thiếu: Python venv + PyYAML, .NET runtime, Il2CppDumper, ILSpy CLI, JDK, Ghidra,
  AssetRipper; Git Bash trên Windows nếu chưa có.
- Phiên bản và URL tải được **chốt** trong một file manifest đi kèm skill, kèm SHA-256
  khi nhà phát hành công bố; tải xong phải kiểm hash, sai thì không dùng.
- Thư mục cài: `UNITY_DECOMPILE_TOOLS` nếu đã đặt; nếu không, tool sẵn có ở
  `H:/UGame/ParkingLoop/tools` được dùng lại; còn không thì cài vào
  `~/.cache/puzzle-recreation/tools` (my call) và đặt biến cho phiên làm việc.
- Chỉ cài vào thư mục tool riêng: không sửa PATH hệ thống, không cần quyền admin.
  Thứ bắt buộc cài toàn hệ thống (ví dụ .NET runtime nếu không dùng được bản portable)
  thì cài theo cách không cần admin nếu có, không được thì dừng với hướng dẫn chính xác.
- Ghi lại tool nào đã cài, phiên bản, hash vào `progress.json`.
- Unity Editor không tự cài: project đích phải mở được bằng một Editor đã có sẵn.

## 8. Bàn giao

`handoff.md` và tin nhắn cuối gồm: các file đã thêm/sửa; danh sách cơ chế kèm nhãn
bằng chứng; kết quả kiểm chứng cuối (compile, model, pointer, level mẫu, chuyển level,
console); bảng so sánh visual; danh sách quyết định `Inferred`; mục chưa chạy được và
lý do; đường dẫn thư mục bằng chứng; trạng thái Editor đã khôi phục.

## 9. Tương thích Claude Code / OpenCode / Codex

- Mỗi skill: thư mục `<skill-id>/SKILL.md`, frontmatter chỉ `name` (kebab-case, trùng tên
  thư mục) và `description` (bắt đầu bằng "Use when…", chỉ nêu điều kiện kích hoạt,
  có từ khoá tiếng Việt và tiếng Anh, < 1024 ký tự).
- Cài đặt chuẩn: `~/.agents/skills/` (OpenCode và Codex tự quét). Claude Code: kèm lệnh
  tạo junction/symlink từ `~/.claude/skills/<id>`.
- Thân skill không phụ thuộc tool riêng của harness: không `@file`, không gọi tên cứng
  `todo`/`Task`/`subagent`. Chỗ cần sub-agent: "nếu harness có sub-agent…; nếu không, làm tuần tự".
  Chỗ cần chờ việc nền: dùng cơ chế nền/monitor của harness, không vòng lặp sleep.
- Script đi kèm gọi qua trình thông dịch; ưu tiên Python (chạy được cả Windows và Unix).
- `unity-apk-decompile` hiện nằm ở `H:\UGame\ParkingLoop\.agents\skills` và
  `scripts/tools-env.sh` suy ra thư mục tool bằng cách đi lên bốn cấp
  (`H:\UGame\ParkingLoop\Tools`). Khi chuyển lên global, đường dẫn tool phải lấy từ
  biến môi trường (ví dụ `UNITY_DECOMPILE_TOOLS`), mặc định về vị trí cũ, để không
  hỏng Parking Loop và dùng được ở project khác.
- Phần Unity: dùng `unity-pipeline`/`unity-cli` nếu có; fallback là Unity batchmode
  (`-batchmode -executeMethod`) cho compile, chạy model test, chụp ảnh. Pointer smoke cần
  Play Mode; skill phải nêu cách chạy được trong batchmode hoặc ghi rõ là không chạy được.

## 10. Ràng buộc với project Unity đích

- Mọi thứ trong `Assets/<GameSlug>/`, namespace riêng, scene riêng, Resources/Addressables
  riêng. Thêm package hoặc đổi build settings chỉ khi bắt buộc và phải ghi lại.
- Không lưu/ghi đè scene dirty của người dùng; ghi nhận và khôi phục trạng thái Editor
  tạm thời (Play Mode, Game View, auto-tick).
- Giữ GUID và `.meta` của asset có sẵn. Asset gốc import vào giữ tên và có file
  `PROVENANCE.md` ghi nguồn.
- Thích ứng render pipeline có sẵn của project (Built-in/URP/HDRP) thay vì chuyển đổi
  project; ghi lại khác biệt ảnh hưởng tới shader.

## 11. Kiểm thử bộ skill (bắt buộc theo writing-skills)

- **RED**: chạy agent không có skill trên kịch bản thực tế; ghi lại nguyên văn chỗ sai.
- **GREEN**: chạy lại có skill; agent phải tuân thủ.
- **Fixture có đáp án**: Parking Loop (XAPK build 567, phân tích và project tái tạo đã có)
  dùng để kiểm tra agent tìm đúng danh mục level, nhận đúng cơ chế, không coi biến thể
  `_z` là level cơ bản, không nói shader dummy là gốc. Kiểm thử chỉ đọc và lập kế hoạch,
  không chạy lại toàn bộ tái tạo trên project Parking Loop.
- Kịch bản áp lực cho các quy tắc kỷ luật: báo PASS từ kết quả cũ, đoán luật khi thiếu
  bằng chứng, sửa project ngoài thư mục được phép, dừng hỏi người dùng giữa chừng.
- **Mức kiểm thử đã chốt (người dùng chọn): Mức A.** Chỉ các bài kiểm thử trên, ở chế
  độ đọc và lập kế hoạch. Không chạy trọn một lần tái tạo trên game thật thứ hai.
  Hệ quả: code C# dùng chung mà skill mô tả (level switcher, pointer smoke driver,
  bộ chạy model test, fallback batchmode, tiếp tục từ `progress.json`) là **chưa được
  chạy thật**. Skill phải trình bày chúng như mẫu cần thích ứng và kiểm chứng tại
  project đích, không như code đã được chứng minh. Báo cáo bàn giao bộ skill ghi rõ
  giới hạn này.

## 12. Quyết định của mình (người dùng chưa trực tiếp chọn)

- Thân skill viết bằng tiếng Anh để trung lập giữa các model/harness; description có
  thêm từ khoá tiếng Việt.
- Thư mục làm việc mặc định đặt cạnh file APK, ngoài project Unity.
- Level switcher là overlay trong scene gameplay (chọn theo trang, next/prev quay vòng,
  retry), không phải scene menu riêng.
- `parkingloop-recreate-mechanics` giữ nguyên; nó trở thành ví dụ mẫu cho skill
  `<game-slug>-notes` mà bộ skill sinh ra.
- Bản thiết kế này đặt ở `C:\Users\melod\.agents\docs\specs\` vì bộ skill không thuộc repo nào.
- `unity-apk-decompile` được **sao chép** (không di chuyển) sang `~/.agents/skills/` thành
  một bản fork cục bộ. Bản project ở `H:\UGame\ParkingLoop\.agents\skills` và
  `tools/decompile-shell.cmd` giữ nguyên để Parking Loop không bị ảnh hưởng. Không đẩy
  lên upstream. Bản global chỉ đổi cách tìm tool: biến `UNITY_DECOMPILE_TOOLS`; nếu không
  đặt thì thử `H:/UGame/ParkingLoop/tools` (đường dẫn cứng, chấp nhận vì là fork cục bộ);
  không có nữa thì báo thiếu tool. Ghi rõ trong `INSTALLATION.md` của bản global rằng
  hai bản có thể lệch nhau.
- `unity-apk-decompile` được dùng lại nguyên trạng ngoài thay đổi đường dẫn tool: không
  dịch thân skill, không port script Bash sang Python. Quy tắc "tiếng Anh" và "ưu tiên
  Python" chỉ áp dụng cho bốn skill mới. Trên Windows, script Bash chạy qua Git Bash.

## 13. Để người xây dựng tự quyết

- Cách chia nội dung giữa SKILL.md và `references/`, `templates/`, `scripts/`.
- Kiến trúc C# cụ thể (miễn tách model/view và giữ luật ở model).
- Định dạng chi tiết của `progress.json` và các template.
- Cách tìm lời giải cho level mẫu khi không có video.
- Danh sách mẫu nơi chứa level phổ biến trong game puzzle Unity.
