# Bộ dữ liệu lớn (học phần — mục III.2 quy mô dữ liệu)

Yêu cầu: ≥ 3 bảng ≥ 10 000 dòng và ≥ 1 bảng ≥ 100 000 dòng, sinh bằng script (không nhập tay).
**Kết quả: đạt** — 4 bảng ≥ 10 000 dòng (`tickets`, `order_items`, `orders`, `users`), 3 bảng ≥ 100 000 dòng.

## Cách sinh

- Script: `backend/app/seed_large.py` — `python -m app.seed_large --scale 1.0 --seed 42 --database-url <URL>`.
- Chạy trên CSDL riêng **`ticketnhip_large`** (bộ demo ở `ticketnhip` giữ nguyên):
  ```bash
  # 1) tạo CSDL (một lần, bằng tài khoản postgres)
  psql -U postgres -h localhost -f database/create_extra_dbs.sql
  # 2) lược đồ + catalog
  cd backend
  export DATABASE_URL=postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip_large
  .venv/Scripts/python.exe -m alembic upgrade head
  .venv/Scripts/python.exe -m app.seed
  # 3) dữ liệu lớn
  .venv/Scripts/python.exe -m app.seed_large --scale 1.0 --seed 42 --database-url $DATABASE_URL
  # 4) đếm dòng
  psql -h localhost -U ticketnhip -d ticketnhip_large -f scripts/row_counts.sql
  ```
- Toàn bộ chạy trong **một transaction**, sinh bằng `INSERT … SELECT … FROM generate_series`, không lặp từng dòng trong Python.
- Script dùng `setseed()`, nên chạy lại cho ra đúng dữ liệu cũ.
- Chạy lại an toàn: script xoá trước những gì chính nó tạo (email `@lon.ticketnhip.vn`, mã đơn `TL…`, slug `lon-…`), không động tới catalog hay dữ liệu demo.
- Dữ liệu trông giống thật:
  - Họ tên tiếng Việt có dấu, email liên hệ ở gmail/yahoo/outlook…, SĐT giả ngẫu nhiên nhưng không trùng nhau.
  - Một số sự kiện "hot" bán rất chạy.
  - Ngày mua dồn về gần giờ diễn; khoảng 30 % đơn rơi vào thứ Bảy.
  - Khoảng 4 % đơn được hoàn tiền, khoảng 12 % dùng mã giảm giá.
  - Khoảng 70 % vé của sự kiện đã diễn đã được soát.
  - Có đủ các trạng thái sự kiện: chờ duyệt, bị trả lại, đã huỷ, sắp mở bán, đang bán, đã diễn.
- Kiểm thử: `backend/tests/test_seed_large.py` chạy ở scale 0.01 trên CSDL test. Các test kiểm:
  - ràng buộc nghiệp vụ;
  - kho khớp số vé đã bán;
  - yêu cầu rút tiền không vượt số dư;
  - chạy lại không làm đổi số dòng;
  - không chạm dữ liệu demo;
  - số dòng tăng tuyến tính theo scale.

## Kết quả chính thức (`ticketnhip_large`, 2026-11-08)

- Lệnh: `seed_large --scale 1.0 --seed 42`. Thời gian sinh: **39,1 giây** (Intel Core i5-12500H, RAM 15,6 GB, PostgreSQL 18.6, Windows 11).
- Dung lượng: CSDL 107 MB; bảng `orders` 15 MB; bảng `tickets` 18 MB.
- Số dòng lấy từ `scripts/row_counts.sql` (`count(*)` thật). Cột demo là số dòng của CSDL `ticketnhip` cùng ngày.

| Bảng | Vai trò | Bộ demo (`ticketnhip`) | **Bộ lớn (`ticketnhip_large`)** | Cách sinh | Truy vấn sử dụng |
|---|---|---|---|---|---|
| `tickets` | vé điện tử, mã check-in | 72 | **255 908** | mỗi đơn vị `qty` một vé; mã `L0XX-XXXX` (hoán vị số thứ tự rồi đổi sang cơ số 32, không trùng mã vé thật); ~70 % vé của sự kiện đã diễn có `checked_in_at` quanh giờ diễn | soát vé (C1), tra mã vé (C3), Q1–Q6 |
| `order_items` | dòng đơn: hạng × số lượng | 38 | **133 190** | 1–3 hạng / đơn, ưu tiên vé phổ thông, `qty` 1–4 | báo cáo theo hạng vé (Q5), `v_event_sales` |
| `orders` | đơn hàng | 38 | **100 000** | sự kiện được chọn lệch (vài sự kiện rất hot), ngày mua dồn về gần giờ diễn, ~4 % hoàn, ~12 % có mã giảm giá; sự kiện bị huỷ thì mọi đơn đã hoàn | sổ đơn (Q1), báo cáo (Q2–Q4), top khách (Q6), `v_daily_revenue` |
| `users` | khách + Ban tổ chức + admin | 7 | **12 061** | 12 000 khách + 60 Ban tổ chức (+ admin của catalog); mật khẩu băm một lần dùng chung | đăng nhập, Q6 |
| `ticket_tiers` | hạng vé | 216 | 1 414 | 3 hạng / sự kiện | |
| `tier_stock` | kho theo suất | 203 | 1 401 | `sold` = số vé đã bán (paid + refunded); sức chứa = đã bán × 1,2 + 20 | kho chung `stock.tier_stats` |
| `seat_holds` | ghế đã bán | 850 | 850 | (bán sẵn của catalog) | |
| `withdrawals` | yêu cầu rút tiền | 0 | 612 | chỉ trên thực nhận của sự kiện đã diễn (≤ 85 %); có đủ chờ xử lý / đã chuyển / từ chối | Q8, rút tiền (E1/E2) |
| `events` / `shows` | sự kiện / suất | 42 / 46 | 441 / 445 | 400 sự kiện sinh thêm, đủ các phase | trang chủ, dashboard, Q7 |
| `organizers` | hồ sơ Ban tổ chức | 1 | 60 | | |

Bản sao lưu của bộ dữ liệu này đã được thử khôi phục: số dòng và checksum khớp hoàn toàn. Xem `sao-luu-khoi-phuc.md`.
