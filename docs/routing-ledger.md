# Routing ledger

## 2026-11-19 — Review toàn bộ skill set (read-only)

| Task | Điểm | Tier dự kiến | Tier thực tế | Số lần leo thang | Kết quả | Ghi chú |
|------|------|--------------|--------------|------------------|---------|---------|
| Review `recreate-puzzle-gameplay` | — | T4 | T4 (`opus`/`high`) | 0 | pass | Review toàn nhánh → luôn T4. 9 phát hiện |
| Review `unity-apk-decompile` | — | T4 | T4 (`opus`/`high`) | 0 | pass | 9 phát hiện |
| Review extraction + build + verification | — | T4 | T4 (`opus`/`high`) | 0 | pass | 12 phát hiện |

Nhận xét: T4 phù hợp — các reviewer tự dựng PoC (tar symlink chain, vòng lặp vô hạn `dump_class.py`,
quoting `paths.env`) mà tầng thấp hơn khó làm được. Gom 3 skill nhỏ vào một reviewer vẫn đủ sâu.

## 2026-11-19 — Sửa lỗi review (plan `docs/superpowers/plans/2026-11-19-review-fixes.md`)

| Task | Điểm | Tier dự kiến | Tier thực tế | Số lần leo thang | Kết quả | Ghi chú |
|------|------|--------------|--------------|------------------|---------|---------|
| 1 arch param | 2 | T2 | T2 (`sonnet`/`medium`) | 0 | pass | review sạch lần đầu |
| 2 sha256 + tar | 7 | T4 | T4 (`opus`/`high`) | 0 | pass | 1 fix round: reviewer `opus` tìm ra bypass `./x`, `a//x` trên py3.9 |
| 3 check_evidence strict | 5 | T2 | T2 | 0 | pass | 1 fix round: template thiếu `--mechanics`, coverage phải lấy từ mechanics.md |
| 4 dump_class loop | 1 | T1 | T1 (`haiku`/`medium`) | 0 | pass | review sạch |
| 5 ghidra project/exit | 6 | T2 | T2 | 0 | pass | 1 fix round: CRLF trong `_index.tsv` trên Windows |
| 6 paths.env quoting | 3 | T2 | T2 | 0 | pass | review sạch |
| 7 in_env.sh | 6 | T2 | T2 | 0 | pass | 1 fix round: tài liệu còn phụ thuộc biến shell giữa các call |
| 8 MAXMEM | 0 | T0 | T0 (`haiku`/`low`) | 0 | pass | review sạch |
| 9 review cuối | — | T4 | T4 (`opus`/`high`) | 0 | pass | 3 Important (CRLF paths.env, hint cũ, index thiếu dòng) → 1 đợt sửa T3 (`sonnet`/`high`), re-review sạch |

Nhận xét:
- Không task nào phải leo thang tier; mọi fix round đều xong ở vòng 1. T2 (`sonnet`/`medium`) đủ cho các task 3–7; T0/T1 `haiku` ổn khi plan có sẵn code.
- Lỗi thường lọt qua implementer là **đa nền tảng** (CRLF Windows) và **tài liệu sót**. Reviewer `sonnet`/`high` bắt được, nên giữ quality reviewer ở +1 tier.
- Task bảo mật chấm T4 là đúng: chỉ reviewer `opus` dựng được PoC vượt qua bản sửa đầu. Cân nhắc cho phép re-review của task bảo mật dùng T3+ thay vì giới hạn T1–T2.
