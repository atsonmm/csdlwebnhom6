# database/ — Tài nguyên cơ sở dữ liệu

| File / thư mục | Nội dung | Cách tạo lại |
|---|---|---|
| `create_db.sql` | Tạo role `ticketnhip` và 2 CSDL `ticketnhip` (dev) + `ticketnhip_test` (test) | chạy một lần bằng `psql -U postgres -f database/create_db.sql` hoặc pgAdmin → Query Tool |
| `schema.sql` | Lược đồ đầy đủ (bảng, khoá, CHECK, chỉ mục, VIEW, chú thích) xuất từ CSDL dev | `cd backend && bash scripts/export_schema.sh` |
| `docs/` | Minh chứng CSDL cho học phần: mô tả migration, biên bản migration trên dữ liệu thật, dữ liệu lớn (`du-lieu-lon.md`), chỉ mục & EXPLAIN (`hieu-nang.md`, `plans/`), 8 truy vấn (`truy-van.md`), transaction & đồng thời (`giao-dich-dong-thoi.md`), sao lưu / khôi phục (`sao-luu-khoi-phuc.md`) | xem từng file |
| `docs/erd.png`, `erd.pdf`, `erd.svg` | Sơ đồ ERD (20 bảng, 27 khoá ngoại) sinh từ lược đồ thật | `cd backend && .venv/Scripts/python.exe scripts/generate_erd.py` |
| `create_extra_dbs.sql` | Tạo CSDL `ticketnhip_large` (dữ liệu lớn) + `ticketnhip_restore` (đích thử khôi phục) | chạy một lần bằng `psql -U postgres -f database/create_extra_dbs.sql` |

## Lược đồ và migration

Nguồn gốc lược đồ là **Alembic** (`backend/alembic/versions/0001…0008`). `schema.sql` chỉ là bản xuất để đọc và để đưa vào báo cáo.

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head      # dựng / nâng lược đồ
.venv/Scripts/python.exe -m alembic downgrade -1      # hạ một phiên bản
```

## Dữ liệu mẫu (seed)

Dữ liệu mẫu được nạp bằng Python qua ORM, nên mọi ràng buộc đều được kiểm tra khi nạp:

```bash
cd backend
.venv/Scripts/python.exe -m app.seed            # danh mục: sự kiện, suất, hạng vé, sơ đồ khu/ghế, trang chủ, mã giảm giá
.venv/Scripts/python.exe -m app.seed --demo     # + tài khoản khach1..5@demo.ticketnhip.vn và đơn hàng rải 7 ngày
```

Nguồn dữ liệu danh mục: `backend/seed/catalog.json`.

`seed.sql` (bản SQL của bộ dữ liệu mẫu) và script sinh **bộ dữ liệu lớn** (≥ 100.000 đơn) sẽ được thêm ở Task G1 của plan `docs/plans/2026-11-07-organizer-dashboard-phase-2.md`.

## Minh chứng (`docs/`)

- [`migration-0006.md`](docs/migration-0006.md): migration huỷ sự kiện. Nội dung gồm thay đổi, cách kiểm tra dữ liệu cũ, phương án hạ phiên bản và test tự động.
- [`migration-0006-proof.md`](docs/migration-0006-proof.md): biên bản chạy migration trên CSDL dev đã có dữ liệu.
