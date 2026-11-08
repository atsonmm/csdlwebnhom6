# TicketNhịp — Backend (FastAPI + PostgreSQL)

Server API cho giao diện React. Chạy song song với server Node cũ (`../server/`) cho tới khi chuyển xong.

## 1. Tạo CSDL (một lần)

Cần PostgreSQL 18 (kèm pgAdmin 4). Chạy bằng tài khoản `postgres`:

```bash
"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -h localhost -f ../database/create_db.sql
```

Hoặc mở pgAdmin → Query Tool → dán nội dung `database/create_db.sql` → Execute.
Kết quả: role `ticketnhip` (mật khẩu `ticketnhip`, chỉ dùng khi phát triển), CSDL `ticketnhip` và `ticketnhip_test` (UTF8).

## 2. Môi trường Python

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env        # sửa nếu cần
```

## 3. Lược đồ & dữ liệu

```bash
.venv/Scripts/alembic.exe upgrade head      # tạo/cập nhật bảng
.venv/Scripts/python.exe -m app.seed        # nạp danh mục sự kiện (chạy lại nhiều lần vẫn an toàn)
.venv/Scripts/python.exe -m app.seed --reset   # XOÁ SẠCH mọi dữ liệu rồi nạp lại
```

Danh mục lấy từ `seed/catalog.json`. File này được xuất một lần từ dữ liệu JS cũ:

```bash
cd ..   # gốc dự án ticketnhip/
TZ=Asia/Ho_Chi_Minh node backend/seed/export_catalog.mjs
```

Tài khoản quản trị khi phát triển: `admin@ticketnhip.vn` / `admin123456` (đặt `ADMIN_EMAIL`, `ADMIN_PASSWORD` trong `.env` để đổi).

## 4. Chạy server

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- Tài liệu API tự sinh: http://localhost:8000/docs
- Kiểm tra: http://localhost:8000/api/health → `{"ok": true, "postgres": "18.x"}`

## 5. Test

```bash
.venv/Scripts/python.exe -m pytest
```

Test chạy trên CSDL `ticketnhip_test` (không đụng dữ liệu dev).

## 6. Postman

Import `postman/ticketnhip.postman_collection.json` vào Postman (File → Import). Biến `baseUrl` mặc định là `http://localhost:8000/api`.

## 7. Lược đồ, VIEW & ERD (cho báo cáo)

- 19 bảng + 2 VIEW, mọi bảng có chú thích tiếng Việt (`COMMENT ON`).
- `v_event_sales`: số vé đã bán & doanh thu theo sự kiện / suất / hạng vé.
- `v_daily_revenue`: doanh thu (tiền khách trả) & số vé theo ngày giờ Việt Nam, theo Ban tổ chức.
- Xuất lược đồ ra `database/schema.sql`: `bash scripts/export_schema.sh`
- Xem ERD: pgAdmin → Servers → PostgreSQL 18 → Databases → chuột phải `ticketnhip` → **ERD For Database**.

## 8. API danh mục (giai đoạn 2)

Chỉ trả sự kiện đã duyệt và đang bán (`active`), suất và hạng vé đang bán. Lỗi luôn có dạng `{"error": "..."}`.

| Phương thức | Đường dẫn | Trả về |
|---|---|---|
| GET | `/api/categories` | Thể loại theo thứ tự hiển thị |
| GET | `/api/coupons/{code}` | Mã giảm giá (không phân biệt hoa thường) hoặc 404 |
| GET | `/api/events?q=&category=&city=&organizer=&sort=start\|reviewed&limit=` | Thẻ sự kiện; `q` tìm không dấu |
| GET | `/api/events/{slug}` | Chi tiết: suất, hạng vé (kèm vé còn của suất đầu), ban tổ chức, sự kiện liên quan |
| GET | `/api/events/{slug}/availability?show=` | Vé còn lại theo suất; sự kiện theo ghế có thêm `unavailableSeats` |
| GET | `/api/home` | 9 khu trang chủ, mỗi thẻ có `meta` trang trí |
| GET | `/api/maps/{id}` | Sơ đồ khu / ghế (cùng dạng object JS cũ) |

Thời gian luôn theo giờ Việt Nam, ví dụ `2026-11-15T19:00:00+07:00`.

Tệp đối chiếu dữ liệu JS cũ (dùng trong test): `tests/fixtures/legacy_events.json`, `legacy_maps.json`. Sinh lại bằng
`TZ=Asia/Ho_Chi_Minh node backend/seed/dump_legacy_events.mjs` và `dump_legacy_maps.mjs` (chạy từ gốc dự án).

## 9. API tài khoản (giai đoạn 3)

Phiên đăng nhập bằng cookie httpOnly `tn_session` (30 ngày; CSDL chỉ lưu SHA-256 của token). Request ghi dữ liệu phải gửi `Content-Type: application/json` (nếu không: 415).

| Phương thức | Đường dẫn | Thân (JSON) | Trả về |
|---|---|---|---|
| GET | `/api/auth/me` | | `{"user": {...} hoặc null}` |
| POST | `/api/auth/register` | `name`, `identifier` (email hoặc SĐT), `password` | 201 `{"user"}` + đăng nhập luôn |
| POST | `/api/auth/login` | `identifier`, `password` | `{"user"}`; sai 5 lần → khoá 15 phút (429) |
| POST | `/api/auth/logout` | `{}` | `{"ok": true}` |
| POST | `/api/auth/forgot` | `identifier` | `{"ok": true}` (khi `ENV=dev` và tài khoản tồn tại: thêm `devResetUrl`) |
| POST | `/api/auth/reset` | `token`, `password` | `{"user"}`; liên kết dùng 1 lần, hạn 15 phút, đăng xuất mọi thiết bị khác |

Postman: chạy thư mục "2 · Tài khoản" theo thứ tự (Postman tự giữ cookie; "Quên mật khẩu" tự lưu `resetToken` cho bước sau).

## 10. API đặt vé (giai đoạn 4)

| Phương thức | Đường dẫn | Thân (JSON) | Trả về |
|---|---|---|---|
| GET | `/api/orders` | | `{"orders": [...]}` — đơn của chính mình, mới nhất trước (cần đăng nhập) |
| POST | `/api/orders` | theo loại vé / khu: `slug`, `showId`, `items: [{tierId, qty}]`; theo ghế: `slug`, `showId`, `seats: ["G-D5", ...]`; cùng `buyer {name, email, phone}`, `method` (`qr`/`wallet`/`card`), `coupon` | 201 `{"order"}`; mỗi vé một mã check-in `XXXX-XXXX` |

Giá, tổng tiền, giảm giá **do máy chủ tính** (bỏ qua số client gửi). Tối đa 10 vé mỗi đơn. Không bán suất đã diễn ra hoặc sự kiện chưa mở bán.

**Chống bán trùng khi nhiều người mua cùng lúc** — cả đơn nằm trong MỘT transaction:
- Theo loại vé / khu: `UPDATE tier_stock SET sold = sold + :qty WHERE … AND presold + sold + :qty <= capacity RETURNING …` — câu lệnh nguyên tử, không có dòng trả về = hết vé → huỷ cả đơn (409). Khoá theo thứ tự mã hạng vé để hai đơn mua chéo hạng không deadlock. CHECK `presold + sold <= capacity` là lớp chặn cuối.
- Theo ghế: `INSERT INTO seat_holds … ON CONFLICT DO NOTHING RETURNING seat_id` — ghế không được trả về = vừa có người giữ → huỷ cả đơn (409 kèm tên ghế). Khoá chính `(event_id, show_id, seat_id)` là lớp chặn cuối.
- Test chứng minh: 20 người mua cùng lúc 5 vé cuối → đúng 5 đơn thành công; 10 người giành 1 ghế → đúng 1 người được.

**Đơn mẫu cho buổi bảo vệ / dashboard:** `.venv/Scripts/python.exe -m app.seed --demo` — khoảng 30–50 đơn rải 7 ngày gần nhất, tạo qua chính logic đặt vé; chạy lại thì thay đơn demo cũ (trả lại kho). Khách demo: `khach1..5@demo.ticketnhip.vn` / `demo123456`.

## 11. API Ban tổ chức & Quản trị (giai đoạn 5)

| Phương thức | Đường dẫn | Ai gọi | Trả về |
|---|---|---|---|
| POST | `/api/organizer/register` | người đã đăng nhập | 201 `{"user"}` (vai trò → organizer; gọi lại = cập nhật hồ sơ) |
| GET | `/api/organizer/me` | Ban tổ chức | `{organizer, events, recentOrders}` — chỉ sự kiện & đơn của chính mình; số vé / doanh thu chỉ tính đơn đã thanh toán |
| POST | `/api/organizer/events` | Ban tổ chức | 201 `{"event"}` — chờ duyệt; tạo luôn suất diễn, hạng vé `ve-N`, dòng kho |
| GET | `/api/admin/overview` | Quản trị | `{pending, orders, totals}` |
| POST | `/api/admin/events/{id}/review` | Quản trị | `{"ok", "slug", "status"}`; `decision`: `approve` / `reject` (+ `reason`) |

Sự kiện chờ duyệt / bị trả lại không xuất hiện ở API danh mục và không đặt vé được. Duyệt là một câu `UPDATE … WHERE status = 'pending'`
nên hai quản trị viên bấm cùng lúc thì chỉ một người thành công (người kia: 409 "Hồ sơ này đã được xử lý").

Tài khoản quản trị khi phát triển: `admin@ticketnhip.vn` / `admin123456`. Postman: chạy thư mục "4 · Ban tổ chức & Quản trị" theo thứ tự (cần chạy "2 · Tài khoản" trước để có tài khoản Postman).

## 12. Dashboard Ban tổ chức (giai đoạn 7)

| Phương thức | Đường dẫn | Trả về |
|---|---|---|
| GET | `/api/organizer/stats?days=7` | `{"days": [{date, label, revenue, tickets}]}` — đủ N ngày (1–31) kết thúc hôm nay, theo ngày giờ Việt Nam (VIEW `v_daily_revenue`) |
| GET | `/api/organizer/events/{id}` | Ngăn kéo: `tiers` (đã bán / doanh thu từng hạng), `money` (gross − discount = revenue; phí 5%; thực nhận), `timeline`, 5 đơn gần đây — chỉ sự kiện của chính mình |

- Tạo sự kiện nhận thêm `saleStart` (`"YYYY-MM-DDTHH:mm"`, giờ VN, phải trước giờ diễn; bỏ trống = mở bán khi được duyệt).
- `/api/organizer/me` → mỗi sự kiện có `phase`: `pending` · `rejected` · `upcoming-sale` (chưa tới giờ mở bán) · `on-sale` · `ended`.
- Doanh thu = tiền khách thực trả (Ban tổ chức chịu mã giảm giá); chỉ tính đơn đã thanh toán.
- Dữ liệu test giao diện cho dashboard: `.venv/Scripts/python.exe scripts/capture_dashboard_fixtures.py` (chạy trong tiến trình trên CSDL test, không cần bật server).

## 13. Vận hành Ban tổ chức & Quản trị (giai đoạn 2 — plan `docs/plans/2026-11-07-organizer-dashboard-phase-2.md`)

Hợp đồng chi tiết từng API (request, response, mã lỗi, trạng thái giao diện) ở `docs/FRONTEND_FEATURES_GUIDE.md`. Lỗi luôn có dạng `{"error": "<câu tiếng Việt>"}`.

| Phương thức | Đường dẫn | Ai gọi | Tóm tắt |
|---|---|---|---|
| GET | `/api/organizer/orders?q=&eventId=&status=&from=&to=&page=&pageSize=` | Ban tổ chức | Sổ đơn: tìm (mã đơn tiền tố; tên / email / SĐT chứa), lọc, phân trang, `summary` (Q1) |
| GET | `/api/organizer/reports?from=&to=&eventId=&groupBy=day\|week\|month` | Ban tổ chức | Báo cáo: `totals`, `series` (+ `cumulative`, `changePct`), `byEvent` (+ `rank`), `byTier` (+ `revenueShare`, `fillRate`) (Q2–Q5) |
| GET | `/api/organizer/top-customers?from=&to=` | Ban tổ chức | Top 10 hạng khách chi nhiều nhất (DENSE_RANK, Q6) |
| POST | `/api/organizer/checkin` | Ban tổ chức | Soát vé `{code}` → `checked-in` / `already` (giữ giờ soát đầu) |
| GET | `/api/organizer/venue-maps` | Ban tổ chức | Sơ đồ khu / ghế có sẵn + sức chứa từng nhóm |
| POST | `/api/organizer/events` | Ban tổ chức | (mở rộng) `layout: list\|zones\|seats`, `mapId`, `prices {nhóm: giá}` |
| PATCH | `/api/organizer/events/{id}` | Ban tổ chức | Sửa: `full` (chưa duyệt) / `limited` (đã duyệt, chưa diễn) / `none` |
| DELETE | `/api/organizer/events/{id}` | Ban tổ chức | Huỷ: chưa có đơn → xoá hẳn; có đơn → `cancelled` + hoàn mọi đơn (`{reason}` 5–300 ký tự) |
| GET | `/api/organizer/withdrawals` | Ban tổ chức | Số dư `{settledNet, held, pending, paid, available}` + lịch sử yêu cầu rút |
| POST | `/api/organizer/withdrawals` | Ban tổ chức | 201 — yêu cầu rút `{amount ≥ 50 000, bankName, accountNo, accountName}` ≤ `available` |
| GET | `/api/admin/orders` | Quản trị | Sổ đơn toàn sàn (thêm `organizerId`, mỗi đơn có `orgName`) |
| GET | `/api/admin/organizers` | Quản trị | Ban tổ chức + số sự kiện, doanh thu, phí, `available`, `held`, `pendingWithdrawals` |
| GET | `/api/admin/organizers/{id}/events` | Quản trị | Sự kiện của một Ban tổ chức (mọi trạng thái) |
| GET | `/api/admin/reports` | Quản trị | Báo cáo toàn sàn (+ `byOrganizer`, `totals.platformRevenue`) |
| GET | `/api/admin/tickets/{code}` | Quản trị | Tra mã vé (chỉ xem) |
| GET | `/api/admin/events/{id}` | Quản trị | Xem trước hồ sơ ở mọi trạng thái (cùng JSON trang sự kiện) |
| GET | `/api/admin/events/stale?days=7` | Quản trị | Sự kiện đang bán chưa có đơn N ngày (NOT EXISTS, Q7) |
| POST | `/api/admin/events/{id}/cancel` | Quản trị | Gỡ sự kiện vi phạm: luôn huỷ mềm + hoàn tiền, `{reason}` bắt buộc |
| POST | `/api/admin/events/{id}/review` | Quản trị | (mở rộng) duyệt khi đã qua giờ diễn → 409 |
| GET | `/api/admin/withdrawals?status=pending\|paid\|rejected\|all` | Quản trị | Yêu cầu rút tiền + `orgName`, `orgAvailable` |
| POST | `/api/admin/withdrawals/{id}/decide` | Quản trị | `{decision: paid\|rejected, note}` (từ chối cần lý do 3–300 ký tự) |

### Migration của giai đoạn 2

| Bản | Nội dung | Minh chứng |
|---|---|---|
| 0006 | huỷ sự kiện (`events.cancel_*`, `orders.refunded_at`) | `database/docs/migration-0006.md` |
| 0007 | bảng `withdrawals` (+ CHECK: số tiền > 0, chờ ⇔ chưa xử lý, từ chối ⇒ có lý do) | `tests/test_migrations.py::test_0007_upgrade_on_populated_db` |
| 0008 | chỉ mục `ix_orders_buyer_trgm` (GIN pg_trgm) + `ix_orders_status_created` | `database/docs/hieu-nang.md` |

Nâng CSDL dev: `.venv/Scripts/python.exe -m alembic upgrade head` (cần trước khi dùng các API rút tiền).

### Dữ liệu lớn, hiệu năng, truy vấn

- `python -m app.seed_large --scale 1.0 --database-url …/ticketnhip_large` → `database/docs/du-lieu-lon.md`
- `python scripts/explain_bench.py --database-url …/ticketnhip_large --runs 5` → `database/docs/hieu-nang.md`
- 8 truy vấn SQL thuần ở `sql/queries/*.sql` (chạy qua `app/services/sql_queries.py`) → `database/docs/truy-van.md`
- Minh chứng transaction / đồng thời → `database/docs/giao-dich-dong-thoi.md`
- Sao lưu / khôi phục: `scripts/backup_restore.py backup|restore|verify` → `database/docs/sao-luu-khoi-phuc.md`
