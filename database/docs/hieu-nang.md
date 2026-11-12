# Chỉ mục & hiệu năng (học phần — mục III.5)

Hai chỉ mục mới (ngoài khoá chính / UNIQUE), mỗi cái phục vụ **một truy vấn thật đang chạy trong API**. Cả hai được thêm bằng migration có phiên bản `backend/alembic/versions/0008_perf_indexes.py`.

| Chỉ mục | Định nghĩa | Phục vụ |
|---|---|---|
| `ix_orders_buyer_trgm` | `GIN (lower(id \|\| ' ' \|\| buyer_name \|\| ' ' \|\| buyer_email \|\| ' ' \|\| buyer_phone) gin_trgm_ops)` — extension `pg_trgm` | Ô tìm của sổ đơn `GET /api/organizer/orders?q=`, `GET /api/admin/orders?q=` (Task A1/A3, truy vấn Q1) |
| `ix_orders_status_created` | `B-tree (status, created_at) INCLUDE (event_id, total)` | Báo cáo doanh thu theo khoảng ngày `GET /api/organizer/reports`, `GET /api/admin/reports` (Task B1/B3, Q2–Q4), view `v_daily_revenue` |

## Vì sao chọn hai chỉ mục này

- **Tìm đơn** dùng `LIKE '%…%'` (khách gõ một đoạn tên, email hay số điện thoại ở bất kỳ vị trí nào). B-tree chỉ giúp được khi tìm theo tiền tố. Vì vậy trước khi có chỉ mục, PostgreSQL phải **quét toàn bảng** `orders` và tính chuỗi `lower(…)` cho từng dòng. Chỉ mục trigram tách chuỗi thành các cụm 3 ký tự, nên tìm được "chứa chuỗi con" bằng chỉ mục.
  - Truy vấn trong ứng dụng gồm hai điều kiện ghép `AND`:
    1. biểu thức **trùng khớp** biểu thức của chỉ mục — planner dùng điều kiện này để thu hẹp;
    2. điều kiện chính xác như cũ: mã đơn khớp **tiền tố**, các cột khác "chứa".
  - Nhờ vậy kết quả API không đổi. Test `test_search_results_unchanged` so sánh với cách tính cũ trên 12 từ khoá, gồm cả `%`, `_`, `'`, `\` và chuỗi 500 ký tự.
- **Báo cáo doanh thu** chỉ lấy đơn `status = 'paid'` trong một khoảng ngày.
  - Trước đây chỉ có `ix_orders_event_created (event_id, created_at)`. Cột đầu là `event_id`, nên planner phải đọc toàn bộ chỉ mục (2 834 block).
  - Chỉ mục mới đặt `status` trước, `created_at` sau, nên chỉ quét đúng một khoảng liên tục.
  - Phần `INCLUDE (event_id, total)` chứa sẵn mọi cột truy vấn cần, nên đọc thẳng trên chỉ mục mà không phải vào bảng (**Index Only Scan**).

## Cách đo

- **Truy vấn:** `backend/perf/q1_order_search.sql` và `backend/perf/q2_revenue_report.sql`. Tham số cố định ghi ở đầu file:
  - Q1 tìm số điện thoại `0309772046` (có đúng một khách mang số này);
  - Q2 lấy doanh thu toàn sàn theo ngày trong 7 ngày gần nhất.
- **Công cụ:** `backend/scripts/explain_bench.py --database-url … --runs 5` (logic trong `app/perf_bench.py`). Trên cùng một CSDL và cùng dữ liệu, công cụ làm các bước:
  1. đọc định nghĩa chỉ mục từ `pg_indexes`;
  2. `DROP INDEX`, rồi `VACUUM ANALYZE orders`;
  3. chạy `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` 5 lần → đợt **trước**;
  4. tạo lại chỉ mục bằng đúng định nghĩa đã đọc, rồi `VACUUM ANALYZE`;
  5. chạy lại 5 lần → đợt **sau**.

  Kết quả gồm trung vị, min và max thời gian thực thi, node của kế hoạch, shared hit/read. Kế hoạch đầy đủ (JSON) lưu ở `database/docs/plans/`.
- **Kiểm thử tự động** (`backend/tests/test_perf_indexes.py`):
  - `test_plans_use_new_indexes`: kế hoạch Q1 có `Bitmap Index Scan on ix_orders_buyer_trgm`, kế hoạch Q2 dùng `ix_orders_status_created`. Planner tự chọn, không ép bằng `enable_seqscan = off`.
  - `test_migration_0008_up_down`;
  - `test_bench_measures_before_and_after`.
- **Máy đo:** Intel Core i5-12500H, RAM 15,6 GB, Windows 11, PostgreSQL 18.6 (x86_64-windows), cấu hình mặc định.

## Kết quả chính thức — `ticketnhip_large` (100 000 đơn, 255 908 vé; 2026-11-08)

- Dữ liệu: `seed_large --scale 1.0 --seed 42`, xem `du-lieu-lon.md`.
- Lệnh đo:
  ```bash
  cd backend
  .venv/Scripts/python.exe scripts/explain_bench.py --database-url postgresql+psycopg://ticketnhip:ticketnhip@localhost:5432/ticketnhip_large --runs 5
  ```
- Kích thước: bảng `orders` 15 MB; `ix_orders_buyer_trgm` 17 MB; `ix_orders_status_created` 5 MB.
- Kế hoạch đầy đủ: `database/docs/plans/q1_order_search_{before,after}.json`, `q2_revenue_report_{before,after}.json`.

| Truy vấn | Đợt | Trung vị (ms) | Min | Max | Node chính trên `orders` | Shared hit | Shared read |
|---|---|---|---|---|---|---|---|
| Q1 tìm đơn | trước | 59,771 | 59,082 | 139,721 | Seq Scan | 2 036 | 0 |
| Q1 tìm đơn | **sau** | **0,380** | 0,329 | 0,490 | Bitmap Index Scan (`ix_orders_buyer_trgm`) → Bitmap Heap Scan | 59 | 0 |
| Q2 doanh thu 7 ngày | trước | 7,540 | 7,339 | 8,393 | Bitmap Index Scan (`ix_orders_event_created`, đọc hết chỉ mục) → Bitmap Heap Scan | 2 834 | 0 |
| Q2 doanh thu 7 ngày | **sau** | **4,040** | 3,692 | 4,211 | Index Only Scan (`ix_orders_status_created`) | 42 | 0 |

Max 139,7 ms ở đợt trước của Q1 là lần chạy đầu tiên, ngay sau `VACUUM`, khi bộ nhớ đệm còn nguội. Vì vậy bảng dùng trung vị.

### Lần chạy thử trước đó (CSDL test, cùng dữ liệu, 2026-11-08)

Kết quả cùng chiều: Q1 82,8 → 0,52 ms; Q2 17,4 → 5,9 ms. Kế hoạch lưu ở `database/docs/plans/thu-csdl-test/`.

## Nhận xét

- **Q1:** nhanh hơn khoảng **157 lần** (59,8 → 0,38 ms); số block đọc giảm từ 2 036 xuống 59.
  - Trước khi có chỉ mục, mỗi lần tìm phải tính `lower(…)` cho cả 100 000 dòng.
  - Sau khi có chỉ mục, chỉ còn đọc vài danh sách trigram rồi kiểm lại khoảng 28 dòng ứng viên.
  - **Giới hạn:** từ khoá dưới 3 ký tự không tạo được trigram nên vẫn quét bảng. Từ khoá rất phổ biến (ví dụ `gmail`) khớp phần lớn bảng, nên planner chọn Seq Scan, và đó là lựa chọn đúng.
- **Q2:** nhanh hơn khoảng **1,9 lần** (7,5 → 4,0 ms); số block đọc giảm **67 lần** (2 834 → 42) nhờ Index Only Scan, không phải vào bảng.
  - Thời gian còn lại chủ yếu dành cho gom nhóm theo ngày.
  - Mức lợi tăng theo độ dài lịch sử: dữ liệu càng nhiều năm thì khoảng 7 ngày càng nhỏ so với cả bảng.
  - Với khoảng rất dài (ví dụ cả năm), planner có thể quay về quét bảng. Điều này hợp lý.
- **Chi phí:**
  - Hai chỉ mục chiếm khoảng 22 MB, lớn hơn chính bảng `orders`. Riêng chỉ mục trigram là 17 MB.
  - Mỗi lần ghi đơn phải cập nhật thêm hai chỉ mục.
  - GIN dùng *pending list* (`fastupdate`) để giảm chi phí ghi, nhưng phải được `VACUUM` gộp lại thì planner mới ước lượng đúng.
  - Ví dụ: ngay sau khi chèn 20 000 đơn mà chưa `VACUUM`, planner chọn Seq Scan (42 ms thay vì 1,4 ms). Vì vậy công cụ đo và test đều chạy `VACUUM ANALYZE` trước khi đo; trên máy chủ thật, autovacuum làm việc này.

## Chợ vé bán lại — truy vấn duyệt tin (migration 0016, 2026-11-11)

- **Truy vấn:** `GET /api/events/{slug}/resale` (`services/resale.py::event_listings`) — tin `status = 'listed'` của một sự kiện, suất chưa diễn, còn ít nhất một vé `listed` (`EXISTS` trên `resale_listing_tickets`), sắp theo giá.
- **Chỉ mục:** `ix_resale_listings_browse (event_id, show_id, status, price)`; kiểm tra vé dùng khoá chính `resale_listing_tickets (listing_id, …)`; mỗi vé chỉ nằm trong một tin đang mở nhờ `uq_resale_ticket_listed` (UNIQUE một phần).
- **Đo trên CSDL dev** (8 tin bán lại demo): planner chọn **Seq Scan** — đúng, vì cả bảng nằm trong 1 block; thực thi **0,20 ms** (9 block, toàn shared hit).
- **Kiểm tra chỉ mục dùng được** (`SET enable_seqscan = off`, chỉ để xác nhận): `Index Scan using ix_resale_listings_browse`, `Index Cond: event_id = … AND status = 'listed'`, 0,29 ms. Khi bảng lớn (hàng nghìn tin / nhiều sự kiện) planner sẽ tự chuyển sang chỉ mục này.
- **Chưa đo trên `ticketnhip_large`:** CSDL lớn chưa nâng lên 0016 và chưa có tin bán lại mẫu.
