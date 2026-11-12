# Biên bản sao lưu & khôi phục (học phần — backup/restore đã chạy thử)

## Công cụ

- Script: `backend/scripts/backup_restore.py`, dùng `pg_dump` / `pg_restore` của PostgreSQL 18. Đường dẫn tới hai lệnh này đặt qua biến `PG_BIN` (mặc định `C:/Program Files/PostgreSQL/18/bin`).
- **`backup`**:
  - đếm `count(*)` thật của mọi bảng trong schema `public` và ghi lại phiên bản `alembic_version`;
  - chạy `pg_dump -Fc --no-owner --no-privileges` (định dạng custom, có nén);
  - ghi kết quả đếm vào file `<bản sao lưu>.counts.json` nằm cạnh bản sao lưu.
- **`restore`**:
  - chạy `pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error` vào CSDL đích. `--clean` giúp chạy lại được trên một CSDL đã có dữ liệu cũ; `--exit-on-error` làm lệnh dừng ngay khi có lỗi thay vì bỏ qua;
  - sau đó so số dòng **từng bảng** với file đếm. Lệnh trả mã thoát 0 khi khớp, 1 khi không khớp.
- **`verify`**: chỉ so số dòng, không khôi phục.
- Bản sao lưu nằm trong `.data/backups/`. Thư mục này đã được gitignore, nên dữ liệu không bị đưa lên GitHub.
- CSDL đích `ticketnhip_restore` được tạo trống, do role `ticketnhip` sở hữu, bằng `database/create_extra_dbs.sql`.

```bash
cd backend
B=postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432
.venv/Scripts/python.exe scripts/backup_restore.py backup  --database-url $B/ticketnhip
.venv/Scripts/python.exe scripts/backup_restore.py restore --file ../.data/backups/<tên>.dump --database-url $B/ticketnhip_restore
```

## Lần 1 — CSDL dev `ticketnhip` (bộ demo, migration 0008) → `ticketnhip_restore` (trống)

Ngày 2026-11-08. Bản sao lưu `ticketnhip_20261108-173655.dump`: 0,1 MB, `pg_dump` chạy 0,13 s. Khôi phục mất 0,3 s.

| Bảng | Lúc sao lưu | Sau khôi phục |
|---|---:|---:|
| alembic_version (phiên bản) | 0008 | 0008 |
| categories | 6 | 6 |
| coupons | 1 | 1 |
| events | 42 | 42 |
| home_slots | 53 | 53 |
| map_groups | 23 | 23 |
| map_seats | 574 | 574 |
| map_zones | 51 | 51 |
| order_items | 38 | 38 |
| orders | 38 | 38 |
| organizers | 1 | 1 |
| password_resets | 0 | 0 |
| seat_holds | 850 | 850 |
| sessions | 11 | 11 |
| shows | 46 | 46 |
| ticket_tiers | 216 | 216 |
| tickets | 72 | 72 |
| tier_stock | 203 | 203 |
| users | 7 | 7 |
| venue_maps | 5 | 5 |
| withdrawals | 0 | 0 |
| **Tổng** | **2 238** | **2 238** |

**Kiểm thêm nội dung**, không chỉ số dòng. Hai bên giống nhau hoàn toàn ở mọi chỉ số:

| Chỉ số | `ticketnhip` | `ticketnhip_restore` |
|---|---|---|
| MD5 toàn bộ dòng `orders` (theo `id`) | `81bce90d2ac7e495473d183f58f822a1` | `81bce90d2ac7e495473d183f58f822a1` |
| MD5 toàn bộ dòng `tickets` (theo `code`) | `c33ec8dc69b3956fcca570a8f7cc44c9` | `c33ec8dc69b3956fcca570a8f7cc44c9` |
| MD5 toàn bộ dòng `users` (theo `id`) | `4bead5d0311043b76971551d95ea13b9` | `4bead5d0311043b76971551d95ea13b9` |
| MD5 toàn bộ dòng `events` (theo `id`) | `8aeb837f69c8d018c58eecece82b6edf` | `8aeb837f69c8d018c58eecece82b6edf` |
| Số VIEW / chỉ mục / ràng buộc trong `public` | 2 / 34 / 209 | 2 / 34 / 209 |
| Extension `pg_trgm` | có | có |
| Giá trị sequence `users_id_seq` / `events_id_seq` | 13 / 249 | 13 / 249 |

Sequence được khôi phục đúng giá trị, nên các bản ghi tạo mới sau khi khôi phục sẽ không bị trùng khoá chính.

## Lần 2 — bộ dữ liệu lớn `ticketnhip_large` → `ticketnhip_restore` (ghi đè bằng `--clean`)

Ngày 2026-11-08. Bản sao lưu `ticketnhip_large_20261108-173816.dump`: **8,6 MB** cho 507 096 dòng, `pg_dump` chạy 1,13 s. Khôi phục mất **4,8 s**. CSDL đích lúc này đang chứa dữ liệu của lần 1; `--clean` xoá đối tượng cũ trước khi nạp.

| Bảng | Lúc sao lưu | Sau khôi phục |
|---|---:|---:|
| tickets | 255 908 | 255 908 |
| order_items | 133 190 | 133 190 |
| orders | 100 000 | 100 000 |
| users | 12 061 | 12 061 |
| … (17 bảng còn lại, kể cả `withdrawals` 612) | khớp | khớp |
| **Tổng** | **507 096** | **507 096** |

| Chỉ số | `ticketnhip_large` | `ticketnhip_restore` |
|---|---|---|
| MD5 toàn bộ dòng `orders` | `50e91dfd2e410656f5caeebe7142fb69` | `50e91dfd2e410656f5caeebe7142fb69` |
| MD5 toàn bộ dòng `tickets` | `3acf530c6e00b4d33aa43e9cdb4549d4` | `3acf530c6e00b4d33aa43e9cdb4549d4` |
| `sum(orders.total)` (₫) | 120 387 600 000 | 120 387 600 000 |

Script kết luận: **"KHỚP — mọi bảng giữ nguyên số dòng"** (mã thoát 0) ở cả hai lần.

## Kết luận & quy trình đề xuất khi triển khai (3 máy ảo)

- Sao lưu và khôi phục bằng `pg_dump -Fc` / `pg_restore` đã chạy thử thành công ở hai quy mô: 2 238 dòng và 507 096 dòng. Dữ liệu, view, chỉ mục, ràng buộc, extension và sequence đều được giữ nguyên.
- Trên máy ảo CSDL, chạy `backup` theo lịch, ví dụ hằng đêm bằng cron hoặc Task Scheduler. Chép bản `.dump` cùng file `.counts.json` sang ổ hoặc máy lưu trữ riêng.
- Khi cần khôi phục:
  1. tạo CSDL trống;
  2. chạy `restore`;
  3. chỉ trỏ ứng dụng sang CSDL mới khi lệnh trả mã thoát 0.
- Trước mỗi lần migrate CSDL dev hay production, sao lưu trước. Lần nâng dev 0006 → 0008 ngày 2026-11-08 đã có bản sao lưu `ticketnhip_20261108-173112.dump` (ở 0006).
