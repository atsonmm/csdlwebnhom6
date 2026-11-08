# Bảng điều khiển Ban tổ chức — giai đoạn 2 · Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm thật 5 mục còn thiếu của `/ban-to-chuc` (Hoá đơn & đơn hàng, Báo cáo doanh thu, Soát vé, Sửa/Huỷ sự kiện, Rút tiền), cho BTC chọn sơ đồ khu/ghế có sẵn, làm thật trang Admin, và đồng bộ 3 bên Khán giả – Ban tổ chức – Admin — mỗi tính năng gồm API FastAPI + giao diện BTC + task Admin + phần khán giả bị ảnh hưởng.

**Architecture:** Một nguồn số liệu kho chung (`backend/app/services/stock.py`) và một quy tắc trạng thái bán chung (`manage.phase_of` + `ShowOut.closed`) cho cả khán giả, BTC, Admin. API mới của BTC trong router mới `backend/app/routers/organizer.py` (phần admin rút tiền trong `manage.py`), mỗi tính năng một file service. Giao diện BTC: mỗi mục một component trong `frontend/src/pages/Organizer/components/`, `OrganizerDashboard.jsx` chỉ chuyển `view`. Thứ tự (cập nhật 2026-11-08 theo `docs/Thong_bao_Project_cuoi_ky_2026.md`): **S (nền tảng đồng bộ) → A → B → C → D → E → G (hạng mục CSDL bắt buộc của học phần) → F (sơ đồ cho BTC, làm cuối)**; mỗi tính năng làm trọn API + pytest + Postman rồi giao diện + Vitest, task Admin của tính năng đó đứng cuối (A3, B3, C3, D4, E2, F3). D và E không còn phụ thuộc F: phần "sửa sự kiện theo sơ đồ" chuyển sang Task F4, nút "Gỡ sự kiện" của Admin đặt ở danh sách sự kiện của BTC (OrganizersView) và F3 cắm thêm vào ngăn xem trước. Route Admin mới nằm trong `backend/app/routers/admin.py` (tạo ở A3); component Admin trong `frontend/src/pages/Admin/components/`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 18, pytest · React 19, Vite, Tailwind v4, Vitest, Testing Library · `qr-scanner@1.4.2` (chỉ cho Soát vé).

**Spec:** `docs/specs/2026-11-07-organizer-dashboard-phase-2-design.md`

## Global Constraints
- **Cấu trúc thư mục (tái cấu trúc 2026-11-08, sau D3):** frontend nằm trong `frontend/` (chạy `cd frontend && npm test`); route API mới: khai báo ở `backend/app/routers/<nhóm>.py` (chỉ đường dẫn + `Depends`), xử lý ở `backend/app/controllers/<nhóm>_controller.py` (tham số, commit/rollback), nghiệp vụ ở `services/`, body request ở `schemas/`; cấu hình ở `app/config/` (`settings`, `database`, `rules`), `app/middlewares/` (`auth`, `errors`), `app/utils/` (`timefmt`, `validators`, `textnorm`, `security`). Component riêng của trang Ban tổ chức / Admin ở `frontend/src/pages/{Organizer,Admin}/components/`; minh chứng CSDL ở `database/docs/`.
- Lỗi API luôn là `{"error": "<câu tiếng Việt>"}` qua `HTTPException(status, "...")` (xem `backend/app/middlewares/errors.py`); 400 dữ liệu sai, 404 không thấy / không thuộc BTC này, 409 xung đột trạng thái.
- Ban tổ chức chỉ thấy/sửa dữ liệu của sự kiện có `events.organizer_id = user.id`; dữ liệu của BTC khác trả **404** (không lộ là có tồn tại).
- Mã sự kiện trên URL: chỉ chữ số ASCII, 1–10 ký tự, ≤ 2 147 483 647, nếu không → 404 (như `manage.organizer_event`).
- Ngày giờ trả về theo giờ VN bằng `iso_vn()` của `app.utils.timefmt`; tham số ngày dạng `YYYY-MM-DD` hiểu theo ngày VN.
- Tiền là số nguyên VND. Phí sàn `manage.FEE_RATE = 5`, làm tròn `(revenue * 5 + 50) // 100`, tính **theo từng sự kiện** rồi cộng lại (khớp ngăn kéo sự kiện). Dùng chung một hàm `manage.fee_of(revenue: int) -> int` (tách ra ở Task S1, ngăn kéo sự kiện, báo cáo, số dư, Admin dùng lại).
- "Doanh thu" = tổng `orders.total` của đơn `status = 'paid'` (BTC chịu giảm giá), gom theo **ngày mua** (`created_at`). Đơn hoàn biến mất khỏi ngày mua gốc; không ghi số âm vào ngày hoàn.
- Sự kiện của BTC có đúng 1 suất, nhưng mọi truy vấn mới viết theo `show_id`, không giả định chỉ có 1 suất.
- Mọi con số sức chứa / đã bán / còn lại (khán giả, BTC, Admin, kiểm tra khi sửa) đi qua `stock.tier_stats` (Task S1); không tự cộng `ticket_tiers.capacity` hay `order_items.qty` để ra "đã bán". Sự kiện `seats` không có dòng `tier_stock`.
- Giới hạn vé chỉ khai báo ở `backend/app/config/rules.py` (`MAX_PER_ORDER = 10`, `TIER_MAX_PER_ORDER = 10`); frontend đọc `event.maxPerOrder` từ API.
- Phase sự kiện: `pending | rejected | cancelled | upcoming-sale | on-sale | closed | ended`. Chỉ `pending | rejected | upcoming-sale | on-sale` sửa/huỷ được (cả BTC lẫn Admin).
- **Dùng chung, không viết hai lần:** Admin gọi lại service của BTC với `organizer_id=None` (= toàn sàn) thay vì viết truy vấn riêng; giao diện Admin dùng lại component của BTC / khán giả (`OrdersView`, `ReportsView`, `CancelEventDialog`, `MapPricing`, các component trang sự kiện) qua prop `scope="admin"` hoặc `readOnly`.
- Nhãn trạng thái đơn và phase sự kiện chỉ khai báo ở `frontend/src/utils/status.js` (Task S2) cho cả 3 giao diện.
- Phí sàn chỉ tính trên doanh thu sự kiện **của BTC** (`organizer_id IS NOT NULL`); sự kiện do sàn tự bán không có phí.
- Không `git commit` (người dùng yêu cầu bỏ qua — giữ nguyên sau khi đọc thông báo học phần); mỗi task kết thúc bằng bước **Checkpoint** chạy test.
- **Kiểm thử đồng thời dùng 2 kết nối CSDL thật** (học phần: "gọi lần lượt hai lần không được tính"): helper `tests/concurrency.py` → `race(engine, fn_a, fn_b, hold=0.3)` chạy 2 luồng, mỗi luồng một `Session(engine)` (kết nối riêng), cùng xuất phát qua `threading.Barrier`; bên giành được khoá dòng giữ khoá thêm `hold` giây (móc `_after_lock` trong service, mặc định không làm gì) để chứng minh bên kia **thực sự bị chặn** (đo thời gian chờ ≥ `hold − 0.05` s) rồi mới nhận 409. Kết quả trả về `[(status|result, elapsed), …]`.
- **Kiểm thử rollback**: mỗi nghiệp vụ ghi ≥ 2 bảng (huỷ sự kiện + hoàn tiền, tạo yêu cầu rút tiền, duyệt rút tiền) có một test chèn lỗi giữa chừng (monkeypatch một bước ghi sau để ném lỗi) rồi đọc lại bằng **kết nối khác**: không bảng nào bị đổi.
- Python venv: `backend/.venv/Scripts/python.exe`. Test backend chạy trong `backend/`: `.venv/Scripts/python.exe -m pytest <file> -v`. Test frontend chạy ở gốc: `npx vitest run <file>`.
- Chuỗi tiếng Việt truyền qua file, không qua tham số dòng lệnh (Windows làm hỏng dấu). Thư mục "Tài liệu" là NFD — vào dự án bằng `cd /c/Users/khact/OneDrive/Ta*/WeB/ticketnhip`.
- Không tự khởi động lại dev server và không tự chạy `alembic upgrade` trên CSDL dev; cần thì hỏi người dùng.
- Mỗi endpoint mới phải có request trong `backend/postman/ticketnhip.postman_collection.json`, URL bắt đầu bằng `{{baseUrl}}/`.
- Fixture frontend chụp từ API thật bằng `frontend/scripts/capture-fixtures.mjs` (thêm tên mới vào script); test React mock `@/lib/api` bằng `fakeApi` (xem `frontend/src/pages/Organizer/OrganizerDashboard.test.jsx`).

## Review Focus
1. **Soát vé cùng một mã ở hai cổng:** chỉ một lần nhận `checked-in`, lần sau nhận `already` với giờ soát đầu — Task C1 `test_checkin_ok_then_already_keeps_first_time`.
2. **Hai yêu cầu rút tiền chạy chồng lấn trên 2 kết nối, mỗi cái bằng toàn bộ số dư:** đúng một cái 201, cái kia bị chặn ở khoá rồi 409; tổng `pending + paid` không bao giờ vượt thực nhận của các sự kiện đã diễn — khoá `organizers` `FOR UPDATE` — Task E1 `test_two_requests_each_full_balance_second_409` (tuần tự) + `test_concurrent_requests_two_connections` (song song).
3. **Giảm số lượng vé xuống dưới số đã bán** (tính cả `presold`) khi sửa sự kiện đã duyệt → 400, kho không đổi; với sự kiện `seats`, "đã bán" là số ghế trong `seat_holds` chứ không phải `tier_stock` — Task S1 `test_seats_counted_from_seat_holds`, Task D2 `test_limited_capacity_below_sold_400_stock_unchanged`.
4. **Sự kiện đã huỷ:** biến mất khỏi `/api/events`, không đặt được vé, vé của nó soát → 409 — Task D1 `test_cancelled_hidden_and_not_bookable`, `test_checkin_after_cancel_409`.
5. **Ô tìm kiếm đơn có ký tự đặc biệt** (`%`, `_`, `'`, `\`, chuỗi 500 ký tự): không lỗi 500, `%`/`_` không khớp mọi đơn — escape LIKE, cắt `q` còn 100 ký tự — Task A1 `test_search_special_chars_no_500`.
6. **Admin và BTC huỷ cùng một sự kiện cùng lúc trên 2 kết nối:** chỉ một bên thành công, bên kia bị chặn rồi 409, đơn không bị hoàn hai lần — khoá dòng sự kiện `FOR UPDATE` trong `cancel_event` dùng chung — Task D1 `test_concurrent_cancel_two_connections`, Task D4 `test_admin_org_cancel_concurrent_single_refund`.
8. **Lỗi giữa chừng khi huỷ sự kiện / rút tiền:** không bảng nào bị ghi dở — Task D1 `test_cancel_rollback_on_midway_error`, Task E1 `test_request_rollback_on_midway_error`, Task E2 `test_decide_rollback_on_midway_error`.
9. **Truy vấn trên dữ liệu lớn:** chỉ mục G2 phải được planner dùng thật (`Index Scan`/`Bitmap Index Scan` trong EXPLAIN sau khi tạo) — Task G2 `test_plans_use_new_indexes`.
7. **Admin duyệt hồ sơ đã quá giờ diễn** (BTC gửi lâu, Admin duyệt muộn): 409, sự kiện không lên trang chủ — Task F3 `test_approve_after_show_start_409`.

---

## Tính năng S — Nền tảng đồng bộ Khán giả ↔ Ban tổ chức

> **Đã xong (2026-11-08)** — chi tiết và các ruling trong `.superpowers/sdd/2026-11-07-organizer-dashboard-phase-2/progress.md`.

### Task S1: Kho chung, trạng thái bán chung, giới hạn mỗi đơn (backend)

**Files:**
- Create: `backend/app/services/stock.py`, `backend/app/config/rules.py`
- Modify: `backend/app/services/catalog.py` (`tier_remaining` gọi `tier_stats`; `ShowOut` thêm `closed`; `EventDetail` thêm `maxPerOrder`, `soldOut`), `backend/app/schemas/catalog.py`, `backend/app/services/booking.py` và `manage.py` (import hằng số từ `app.config.rules`; `event_summaries` lấy `capacity`/`sold` từ `tier_stats`; `phase_of` thêm `closed`)
- Test: `backend/tests/test_stock.py`, cập nhật `test_api_event_detail.py`, `test_api_organizer_events.py`, `test_api_dashboard.py`

**Interfaces:**
- Produces:
  - `stock.TierStat` (dataclass: `capacity: int, presold: int, sold: int, remaining: int`).
  - `stock.tier_stats(db, events: list[Event], show_id: str | None = None) -> dict[tuple[int, str], TierStat]` — khoá `(event_id, tier_id)`, chỉ hạng `active`; `show_id=None` → cộng mọi suất `active`. list/zones: từ `tier_stock` (thiếu dòng → `capacity = ticket_tiers.capacity`, 0 đã bán); seats: `capacity` = số ghế của nhóm trong `map_seats`, `presold` = `seat_holds` có `order_id IS NULL`, `sold` = `seat_holds` có `order_id`. `remaining = max(0, capacity − presold − sold)`. Truy vấn gộp theo lô, không N+1.
  - `manage.fee_of(revenue: int) -> int` = `(revenue * FEE_RATE + 50) // 100` (thay biểu thức trong `organizer_event_detail`).
  - `manage.phase_of(e, last_show_start, now)` trả thêm `"cancelled"` (từ D1) và `"closed"`: đã duyệt, `last_show_start <= now` nhưng chưa sang ngày VN hôm sau.
  - `event_summaries[*]`: `capacity` = Σ `capacity`, `sold` = Σ (`presold + sold`) qua `tier_stats` (đổi định nghĩa cũ); `revenue` giữ nguyên.
  - `GET /api/events/{slug}`: `shows[*].closed` (`starts_at <= now`), `maxPerOrder` (= `rules.MAX_PER_ORDER`), `soldOut` (mọi suất chưa đóng đều hết vé; không còn suất mở → `true`).
- [x] **Step 1: Test thất bại:** `test_list_and_zones_use_tier_stock_with_presold`; `test_seats_counted_from_seat_holds` (ghế bán sẵn + ghế của đơn); `test_missing_stock_row_defaults_to_capacity`; `test_aggregate_over_shows`; `test_phase_closed_after_start_same_day`; `test_detail_closed_show_and_sold_out_across_shows` (suất 1 hết, suất 2 còn → `soldOut == false`); `test_summary_sold_matches_availability` (BTC "đã bán" = sức chứa − "còn lại" của `/availability`); `test_admin_overview_totals_paid_only` (`/api/admin/overview`: `totals.tickets` / `orders` chỉ đơn `paid`; `totals.fee` = Σ `fee_of` theo sự kiện của BTC; `totals.platformRevenue` = doanh thu sự kiện `organizer_id IS NULL`, `totals.orgRevenue` = phần của BTC; `revenue` = tổng hai phần).
- Admin: `manage.overview` sửa theo test trên (thêm `fee`, `orgRevenue`, `platformRevenue`); `orders[*].status` giữ nguyên giá trị CSDL.
- [x] **Step 2–4:** FAIL → cài đặt → PASS. Chạy lại toàn bộ test đặt vé (`test_api_orders_*`, `test_api_availability.py`) — không đổi hành vi.
- [x] **Checkpoint:** `pytest -q`.

### Task S2: Khán giả dùng trạng thái bán chung (frontend)

**Files:**
- Modify: `frontend/src/components/booking/BookingParts.jsx` (`ShowPicker`: suất `closed` bị vô hiệu, nhãn "Đã diễn"), `frontend/src/pages/Event/EventPage.jsx` + `frontend/src/components/event/EventHero.jsx` (dùng `event.soldOut` thay vì xét `remaining` của suất đầu; chọn sẵn suất mở đầu tiên), `frontend/src/pages/Booking/BookingPage.jsx` (`event.maxPerOrder ?? MAX_PER_ORDER`; suất trên URL đã đóng → chuyển sang suất mở đầu tiên), `frontend/src/utils/dashboard.js` (STATUS `closed` = `{label: 'Đang diễn', tone: 'ink'}`; bộ lọc "Đang bán" không gồm `closed`, "Đã diễn" gồm `closed` và `ended`), `frontend/src/constants/rules.js` (ghi chú: chỉ là giá trị dự phòng)
- Create: `frontend/src/utils/status.js` — `ORDER_STATUS = { paid: {label: 'Đã trả', tone: 'forest'}, refunded: {label: 'Đã hoàn', tone: 'tomato'}, cancelled: {label: 'Đã huỷ', tone: 'muted'} }`, `orderStatus(s)` (khoá lạ → `{label: s, tone: 'muted'}`, không bao giờ rơi về "Đã trả"); chuyển `STATUS` phase từ `dashboard.js` sang đây và re-export để import cũ không vỡ.
- Modify (Admin): `frontend/src/pages/Admin/AdminDashboard.jsx` dùng `orderStatus`, StatCard phí sàn dùng `totals.fee` (bỏ `revenue * 0.05`), thêm dòng "sàn tự bán: {platformRevenue}".
- Test: `frontend/src/pages/Event/EventPage.test.jsx`, `frontend/src/pages/Booking/BookingPage.test.jsx`, `frontend/src/utils/dashboard.test.js`, `frontend/src/utils/status.test.js`, `frontend/src/pages/Admin/AdminDashboard.test.jsx` (tạo mới: đơn `refunded` hiện "Đã hoàn"; phí sàn lấy từ `totals.fee`); chụp lại fixture `event-*`, `org-me`, thêm `admin-overview`

**Interfaces:** Consumes S1 (`closed`, `soldOut`, `maxPerOrder`, phase `closed`).
- [x] **Step 1: Test thất bại:** sự kiện 2 suất, suất đầu hết vé → nút "Mua vé ngay" vẫn bật; suất `closed` không bấm được; `maxPerOrder: 4` → bộ đếm dừng ở 4; dashboard: phase `closed` hiện con dấu "Đang diễn" và nằm trong bộ lọc "Đã diễn".
- [x] **Step 2–4:** FAIL → cài đặt → PASS.
- [x] **Checkpoint:** `npm test`.

---

## Tính năng A — Hoá đơn & đơn hàng

> **Đã xong (2026-11-08)** — chi tiết và các ruling trong `.superpowers/sdd/2026-11-07-organizer-dashboard-phase-2/progress.md`.

### Task A1: API `GET /api/organizer/orders`

**Files:**
- Create: `backend/app/routers/organizer.py`, `backend/app/services/org_orders.py`
- Modify: `backend/app/main.py` (thêm `app.include_router(organizer.router, prefix="/api")` sau `manage.router`), Postman collection
- Test: `backend/tests/test_api_org_orders.py`

**Interfaces:**
- Produces (dùng ở mọi task backend sau):
  - `app.routers.organizer.parse_event_id(raw: str, message: str) -> int` — kiểm định dạng như Global Constraints, sai → `not_found(message)`.
  - `app.services.org_orders.own_event(db, organizer_id: int, event_id: int) -> Event` — không thuộc BTC → 404 `manage.EVENT_NOT_FOUND`.
  - `app.services.org_orders.parse_day(raw: str | None, field: str) -> date | None` — `YYYY-MM-DD` hoặc rỗng; sai → 400 `"Ngày {field} không hợp lệ"`.
  - `app.services.org_orders.list_orders(db, organizer_id: int | None, *, q: str, event_id: int | None, status: str, day_from: date | None, day_to: date | None, page: int, page_size: int) -> dict`
- Hợp đồng: query `q` (cắt còn 100 ký tự), `eventId`, `status` ∈ `all|paid|refunded|cancelled` (mặc định `all`, khác → 400 `"Trạng thái đơn không hợp lệ"`), `from`, `to` (`from > to` → 400 `"Khoảng ngày không hợp lệ"`), `page` ≥ 1 (mặc định 1), `pageSize` 1–100 (mặc định 20). Trả:
  ```json
  {"orders": [{"id","createdAt","eventId","eventTitle","showId","startsAt","buyerName","buyerEmail","buyerPhone",
               "items","tickets","checkedIn","subtotal","discount","total","method","status","refundedAt"}],
   "page": 1, "pageSize": 20, "total": 37,
   "summary": {"paidOrders": 30, "paidRevenue": 12500000, "tickets": 61}}
  ```
  `refundedAt` = `iso_vn(orders.refunded_at)` — cột này do Task D1 thêm; ở A1 trả `null` (đọc bằng `getattr(o, "refunded_at", None)` cho tới khi D1 thêm cột, D1 đổi thành truy cập trực tiếp). `items` dạng `"Vé thường ×2, VIP ×1"` (như `manage._recent_orders`); `summary` tính trên toàn bộ kết quả lọc, không chỉ trang hiện tại; sắp `created_at DESC, id DESC`. `q` khớp mã đơn (bắt đầu bằng, không phân biệt hoa thường) hoặc chứa trong tên / email / SĐT người mua (`ILIKE`, đã escape `%`, `_`, `\`).

- [x] **Step 1: Viết test thất bại** trong `test_api_org_orders.py` (fixture `c`, `logged_organizer`, `api_db`; helper `make_org_event`, `insert_order`, `make_customer`):
  - `test_lists_only_own_orders_newest_first` — 2 đơn của BTC + 1 đơn của BTC khác → `total == 2`, mới trước.
  - `test_filter_status_event_and_date_range` — `status=refunded` chỉ ra đơn hoàn; `eventId` của BTC khác → `total == 0`; `from=to=<ngày đơn>` ra đúng 1.
  - `test_search_by_order_id_name_email_phone` — mỗi kiểu khớp đúng 1 đơn; `q="tn"` khớp mã đơn bắt đầu `TN`.
  - `test_search_special_chars_no_500` — `q` ∈ `["%", "_", "'", "\\", "a" * 500]` → 200; `%` và `_` không khớp đơn nào.
  - `test_pagination_and_summary` — 3 đơn, `pageSize=2&page=2` → 1 đơn, `total == 3`, `summary.paidRevenue` = tổng cả 3.
  - `test_bad_params_400` — `status=x`, `from=2026-13-01`, `from > to`, `pageSize=0` → 400 có `error`.
  - `test_requires_organizer` — khách thường → 403, chưa đăng nhập → 401.
- [x] **Step 2: Chạy, xác nhận FAIL** — `.venv/Scripts/python.exe -m pytest tests/test_api_org_orders.py -v` → 404 (chưa có route).
- [x] **Step 3: Cài đặt** `org_orders.py` + router. Lọc ngày: `created_at >= day_from 00:00 VN` và `< (day_to + 1 ngày) 00:00 VN`. `tickets` / `checkedIn` đếm từ `tickets` bằng một truy vấn GROUP BY `order_id` cho cả trang (không N+1).
- [x] **Step 4: Chạy lại** → PASS.
- [x] **Step 5: Postman** — thư mục "Ban tổ chức — đơn hàng": `GET {{baseUrl}}/api/organizer/orders?q=&status=all&page=1&pageSize=20`. `pytest tests/test_postman_collection.py` → PASS.
- [x] **Checkpoint:** `.venv/Scripts/python.exe -m pytest -q` → toàn bộ PASS.

### Task A2: Trang "Hoá đơn & đơn hàng"

**Files:**
- Create: `frontend/src/pages/Organizer/components/OrdersView.jsx`, `frontend/src/hooks/useOrgOrders.js`, `frontend/src/pages/Organizer/components/OrdersView.test.jsx`, `frontend/src/test/fixtures/org-orders.json`
- Modify: `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (`onNav('orders')` → `setView('orders')`; `active` và tiêu đề theo `view`), `frontend/scripts/capture-fixtures.mjs` (`save('org-orders', await org('/organizer/orders?pageSize=5'))`)

**Interfaces:**
- Consumes: hợp đồng A1.
- Produces: `useOrgOrders(params: {q, eventId, status, from, to, page}) -> {data, error, loading, reload}` — gọi `api('/organizer/orders?' + URLSearchParams)` bỏ khoá rỗng, bỏ kết quả cũ khi params đổi. Mẫu view dùng lại ở B2/C2: `export default function XView({ events })` nhận `events` từ `useOrganizerData`.

- [x] **Step 1: Test thất bại** `OrdersView.test.jsx` (fixture `org-orders`):
  - mỗi đơn một dòng (mã đơn, người mua, tổng tiền định dạng `money()`), con dấu `Đã trả` / `Đã hoàn` / `Đã huỷ`;
  - gõ ô "Tìm mã đơn, tên, email, SĐT" → sau 300 ms gọi API có `q=`; đổi bộ lọc sự kiện / trạng thái / ngày → gọi API đúng tham số và `page=1`;
  - "Trang sau" gửi `page=2`, bị vô hiệu khi `page * pageSize >= total`;
  - rỗng → "Không có đơn nào khớp bộ lọc".
- [x] **Step 2: Chạy** `npx vitest run frontend/src/pages/Organizer/components/OrdersView.test.jsx` → FAIL.
- [x] **Step 3: Cài đặt** OrdersView: hàng bộ lọc (ô tìm debounce 300 ms, select sự kiện từ `events`, `Tabs` trạng thái, 2 ô `type="date"`), 3 `StatCard` từ `summary`, bảng đơn (màn hẹp: thẻ xếp dọc), phân trang. Dùng `Panel`, `Stamp`, `StatCard` (`components/dashboard/widgets.jsx`), `money` (`utils/format.js`).
- [x] **Step 4: Chụp fixture** (cần server đang chạy, nếu không thì hỏi người dùng) rồi chạy test → PASS.
- [x] **Step 5: Cập nhật `OrganizerDashboard.test.jsx`** — bấm "Hoá đơn & đơn hàng" hiện OrdersView, không còn toast "sẽ có ở bước tiếp theo".
- [x] **Checkpoint:** `npm test` → PASS.

### Task A3: Admin — Sổ đơn toàn sàn

**Files:**
- Create: `backend/app/routers/admin.py` (đăng ký trong `main.py`; mọi route `require_role("admin")`), `frontend/src/pages/Admin/components/AdminOrders.jsx`
- Modify: `backend/app/services/org_orders.py` (`organizer_id=None` → không lọc theo BTC; tham số mới `filter_organizer: int | None`; mỗi dòng thêm `orgName`), `frontend/src/pages/Organizer/components/OrdersView.jsx` (prop `scope: 'organizer' | 'admin'` chọn endpoint; admin có thêm select "Ban tổ chức" và cột BTC), `frontend/src/pages/Admin/AdminDashboard.jsx` (mục "Sổ đơn hàng" render `AdminOrders` thay cho bảng 10 đơn + tìm phía trình duyệt; bỏ nút giả "Gửi lại vé qua email"; ô tìm trên đầu trang chỉ còn lọc hồ sơ chờ duyệt), Postman
- Test: `backend/tests/test_api_admin_orders.py`, `frontend/src/pages/Admin/components/AdminOrders.test.jsx`

**Interfaces:**
- Consumes: `list_orders` (A1), `OrdersView` (A2).
- Produces: `GET /api/admin/orders` — cùng tham số và cùng JSON với `/organizer/orders`, thêm `organizerId` (lọc) và `orgName` trên mỗi đơn (`null` = sự kiện sàn tự bán). `admin.py` là router chung cho mọi route Admin mới ở các task sau.
- [x] **Step 1: Test thất bại:** `test_admin_sees_all_orgs_and_platform_orders`; `test_filter_by_organizer`; `test_same_filters_as_organizer` (cùng tham số → cùng `orders` khi lọc theo 1 BTC như BTC đó tự xem); `test_requires_admin`; UI: `AdminOrders` gọi `/admin/orders`, có select BTC, đơn `refunded` hiện "Đã hoàn".
- [x] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `GET {{baseUrl}}/api/admin/orders`.
- [x] **Checkpoint:** `pytest -q` và `npm test`.

---

## Tính năng B — Báo cáo doanh thu

> **Đã xong (2026-11-08)** — chi tiết và các ruling trong `.superpowers/sdd/2026-11-07-organizer-dashboard-phase-2/progress.md`.

### Task B1: API `GET /api/organizer/reports`

**Files:**
- Create: `backend/app/services/org_reports.py`
- Modify: `backend/app/routers/organizer.py`, Postman
- Test: `backend/tests/test_api_org_reports.py`

**Interfaces:**
- Consumes: `parse_day`, `own_event` (A1).
- Produces: `org_reports.report(db, organizer_id: int, *, day_from: date, day_to: date, event_id: int | None, group_by: str) -> dict`
- Hợp đồng: `from` / `to` mặc định 30 ngày kết thúc hôm nay (VN); khoảng > 366 ngày → 400 `"Khoảng báo cáo tối đa 366 ngày"`; `groupBy` ∈ `day|week|month` (mặc định `day`, khác → 400). Trả:
  ```json
  {"range": {"from": "2026-10-09", "to": "2026-11-07", "groupBy": "day"},
   "totals": {"gross","discount","revenue","fee","net","orders","tickets","refundedOrders","refundedAmount"},
   "series": [{"key": "2026-11-01", "label": "01/11", "revenue", "tickets", "orders"}],
   "byEvent": [{"eventId","title","revenue","tickets","orders","fee","net"}],
   "byTier": [{"eventId","eventTitle","tierId","tierName","price","capacity","sold","revenue"}]}
  ```
  `series` liên tục (bucket không có đơn = 0), tính theo giờ VN: `day` → nhãn `dd/MM`; `week` → khoá là thứ Hai đầu tuần, nhãn `T dd/MM`; `month` → khoá `YYYY-MM`, nhãn `MM/YYYY`. `byEvent` sắp doanh thu giảm dần; `byTier.sold/revenue` chỉ trong khoảng ngày; `byTier.capacity` lấy từ `stock.tier_stats` (S1). Mọi số chỉ từ đơn `paid` có ngày mua trong khoảng; riêng `refundedOrders` / `refundedAmount` đếm đơn `refunded` có **ngày mua** trong khoảng. `totals.fee` = tổng `fee_of()` của từng dòng `byEvent`.
- Consumes thêm: `manage.fee_of` (S1). `report(...)` nhận `organizer_id: int | None` ngay từ đầu (None = toàn sàn, dùng ở B3).

- [x] **Step 1: Test thất bại:** `test_totals_match_orders_in_range` (đơn ngoài khoảng bị loại; `fee`/`net` đúng công thức); `test_series_continuous_day_week_month` (7 ngày → 7 bucket; 2026-10-01..2026-11-30 theo tháng → 2); `test_by_event_and_tier`; `test_refunded_counted_separately`; `test_event_filter_other_org_404`; `test_range_too_long_400`; `test_bad_group_by_400`.
- [x] **Step 2:** chạy → FAIL.
- [x] **Step 3: Cài đặt** — gom bằng `date_trunc(:unit, created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')` trong SQL, lấp bucket trống bằng Python.
- [x] **Step 4:** chạy → PASS. **Step 5:** Postman `GET {{baseUrl}}/api/organizer/reports?groupBy=day`.
- [x] **Checkpoint:** `pytest -q` → PASS.

### Task B2: Trang "Báo cáo doanh thu"

**Files:**
- Create: `frontend/src/pages/Organizer/components/ReportsView.jsx`, `frontend/src/hooks/useOrgReport.js`, `frontend/src/pages/Organizer/components/ReportsView.test.jsx`, `frontend/src/test/fixtures/org-reports.json`
- Modify: `OrganizerDashboard.jsx` (`reports` → view), `frontend/scripts/capture-fixtures.mjs`

**Interfaces:** Consumes hợp đồng B1. Produces `useOrgReport({from, to, eventId, groupBy}) -> {data, error, loading}`.

- [x] **Step 0:** Nạp skill `dataviz` trước khi viết biểu đồ.
- [x] **Step 1: Test thất bại:** nút khoảng nhanh `7 ngày | 30 ngày | 90 ngày | Tuỳ chọn` gửi `from`/`to` đúng; `Toggle` Ngày/Tuần/Tháng gửi `groupBy`; 4 StatCard (Doanh thu, Phí sàn, Thực nhận, Vé bán); bảng theo sự kiện và theo hạng vé đủ dòng fixture; khoảng không có đơn → "Chưa có doanh thu trong khoảng này".
- [x] **Step 2:** chạy → FAIL.
- [x] **Step 3: Cài đặt** — dùng lại `BarChart` của `widgets.jsx` (Toggle Doanh thu / Số vé như sổ cái); bảng hạng vé có `Progress` sold/capacity.
- [x] **Step 4:** chụp fixture, chạy → PASS.
- [x] **Checkpoint:** `npm test`.

### Task B3: Admin — Số liệu thật, bục vinh danh, danh sách Ban tổ chức

**Files:**
- Modify: `backend/app/routers/admin.py`, `backend/app/services/org_reports.py` (toàn sàn: thêm `byOrganizer`), `backend/app/services/manage.py` (`admin_organizers`, `admin_organizer_events`), `frontend/src/pages/Admin/AdminDashboard.jsx` (biểu đồ "Doanh thu & số vé" và "Bục vinh danh" lấy từ API — xoá `SampleTag`; mục menu "Ban tổ chức" mở `OrganizersView`; bỏ "Hàng chờ ảo" + khối chân sidebar hàng chờ và "Cấu hình hệ thống"), `frontend/src/pages/Organizer/components/ReportsView.jsx` (prop `scope`)
- Create: `frontend/src/pages/Admin/components/OrganizersView.jsx`, `frontend/src/pages/Admin/components/OrganizersView.test.jsx`
- Delete: phần `admin` trong `frontend/src/constants/dashboards.js` (xoá file nếu không còn ai import)
- Test: `backend/tests/test_api_admin_reports.py`

**Interfaces:**
- Consumes: `org_reports.report(organizer_id=None)` (B1), `event_summaries` (S1), `fee_of`.
- Produces:
  - `GET /api/admin/reports` — JSON như B1, thêm `byOrganizer: [{"organizerId","orgName","revenue","fee","net","tickets","orders"}]` (sàn tự bán là một dòng `organizerId: null`, `orgName: "Sàn TicketNhịp"`, `fee: 0`) và `totals.platformRevenue`.
  - `GET /api/admin/organizers` → `{"organizers": [{"userId","code","orgName","email","phone","createdAt","events","live","pending","revenue","fee"}]}` (E2 thêm `available`, `held`, `pendingWithdrawals`).
  - `GET /api/admin/organizers/{id}/events` → `{"events": event_summaries(...)}` của BTC đó.
  - Biểu đồ Admin = `GET /api/admin/reports?groupBy=week` 6 tuần gần nhất; Bục vinh danh = 5 dòng đầu `byEvent`.
- [x] **Step 1: Test thất bại:** `test_admin_report_totals_equal_sum_of_organizers` (Σ `byOrganizer.revenue` == `totals.revenue`; phí chỉ của BTC); `test_admin_report_matches_org_report` (lọc 1 BTC ra cùng số với `/organizer/reports` của BTC đó); `test_organizers_list_counts`; `test_organizer_events_404_unknown`; UI: không còn chữ "DỮ LIỆU MẪU" ở trang Admin; bấm một BTC → danh sách sự kiện của BTC.
- [x] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman 3 request.
- [x] **Checkpoint:** `pytest -q` và `npm test`.

---

## Tính năng C — Soát vé tại cổng

> **Đã xong (2026-11-08)** — chi tiết và các ruling trong `.superpowers/sdd/2026-11-07-organizer-dashboard-phase-2/progress.md`.

### Task C1: API `POST /api/organizer/checkin`

**Files:**
- Create: `backend/app/services/checkin.py`
- Modify: `backend/app/routers/organizer.py`, Postman
- Test: `backend/tests/test_api_checkin.py`

**Interfaces:**
- Produces: `checkin.normalize_code(raw: Any) -> str | None` — bỏ khoảng trắng, viết hoa, `"K7QF29XM"` → `"K7QF-29XM"`; không khớp `^[A-Z0-9]{4}-[A-Z0-9]{4}$` → `None` (định dạng từ `booking.new_ticket_code`). `checkin.check_in(db, organizer_id: int, raw_code: Any) -> dict`.
- Hợp đồng: body `{"code": "..."}`. Sai định dạng → 400 `"Mã vé không hợp lệ"`; không có / thuộc BTC khác → 404 `"Không tìm thấy vé"`; đơn không `paid` → 409 `"Vé thuộc đơn đã hoàn tiền hoặc đã huỷ"`. Thành công 200:
  ```json
  {"result": "checked-in" | "already",
   "ticket": {"code","orderId","eventId","eventTitle","showId","startsAt","tierName","seat","buyerName","checkedInAt"},
   "showToday": true,
   "progress": {"checkedIn": 41, "total": 120}}
  ```
  `seat` = nhãn ghế `map_seats.label` (giống `booking.orders_json`, để cổng soát và vé của khán giả hiện cùng một chữ), `null` nếu không bán theo ghế. `already` = đã soát trước đó, `checkedInAt` là lần soát ĐẦU. Ghi bằng `UPDATE tickets SET checked_in_at = now() WHERE code = :c AND checked_in_at IS NULL RETURNING ...` — không đọc rồi mới ghi. `showToday` = ngày suất (VN) == hôm nay (VN); giao diện chỉ cảnh báo, không chặn. `progress` đếm vé thuộc đơn `paid` cùng suất.

- [x] **Step 1: Test thất bại:** `test_normalize_code` (tham số hoá: chữ thường, thiếu gạch, có khoảng trắng, 7 ký tự → None); `test_checkin_ok_then_already_keeps_first_time`; `test_other_org_ticket_404`; `test_refunded_order_409`; `test_bad_code_400`; `test_progress_counts`; `test_show_today_flag` (suất hôm nay vs 30 ngày sau); `test_seat_label_matches_customer_ticket` (sự kiện `seats`: `ticket.seat` == `seat` trong `GET /api/orders` của khách).
- [x] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `POST {{baseUrl}}/api/organizer/checkin`.
- [x] **Checkpoint:** `pytest -q`.

### Task C2: Trang "Soát vé tại cổng"

**Files:**
- Create: `frontend/src/pages/Organizer/components/GateView.jsx`, `frontend/src/pages/Organizer/components/QrScanner.jsx`, `frontend/src/pages/Organizer/components/GateView.test.jsx`
- Modify: `OrganizerDashboard.jsx` (`gate` → view), `package.json` (`npm i qr-scanner@1.4.2`); phía khán giả: `frontend/src/context/OrdersProvider.jsx` (thêm `reload()`; `MyTicketsPage` gọi `reload` khi mở trang và khi tab trình duyệt được focus lại), `frontend/src/components/booking/ETicket.jsx` ("Đã check-in lúc HH:mm dd/MM" thay cho "Đã check-in")
- Test thêm: `frontend/src/pages/MyTickets/MyTicketsPage.test.jsx` (tạo mới) — vé có `checkedInAt` hiện giờ soát; mở trang gọi lại `/orders`.

**Interfaces:** Consumes hợp đồng C1. Produces `QrScanner({ onCode: (text: string) => void, paused: boolean })` — bọc `qr-scanner`; không có camera hoặc bị từ chối quyền → "Không mở được camera — hãy nhập mã".

- [x] **Step 1: Test thất bại** (`vi.mock` QrScanner): nhập mã + Enter → POST `/organizer/checkin` `{code}`; `checked-in` → thẻ xanh "HỢP LỆ" + hạng vé + ghế; `already` → thẻ vàng "ĐÃ SOÁT LÚC HH:mm"; lỗi 404/409 → thẻ đỏ với câu lỗi; `showToday=false` → cảnh báo "Vé không phải suất hôm nay"; danh sách 10 lần soát gần nhất trong phiên; ô nhập tự focus lại sau mỗi lần soát; trong lúc chờ API bỏ qua mã quét trùng.
- [x] **Step 2–4:** FAIL → cài đặt (nút "Bật camera" bật/tắt `QrScanner`; `Progress` từ `progress`) → PASS.
- [x] **Step 5: Thử tay** (cần server — hỏi người dùng): soát một mã lấy từ `/ve-cua-toi`.
- [x] **Checkpoint:** `npm test`.

### Task C3: Admin — Tra cứu mã vé (chỉ xem)

**Files:**
- Modify: `backend/app/routers/admin.py`, `backend/app/services/checkin.py` (`lookup(db, raw_code) -> dict`, dùng chung truy vấn với `check_in` nhưng **không ghi**), `frontend/src/pages/Admin/AdminDashboard.jsx` (ô "Tra mã vé" trong mục Sổ đơn hàng), Postman
- Create: `frontend/src/pages/Admin/components/TicketLookup.jsx`
- Test: `backend/tests/test_api_admin_tickets.py`, `frontend/src/pages/Admin/components/TicketLookup.test.jsx`

**Interfaces:**
- Consumes: `checkin.normalize_code` (C1).
- Produces: `GET /api/admin/tickets/{code}` → `{"ticket": {...như C1}, "order": {"id","status","total","createdAt","buyerName","buyerEmail"}, "event": {"id","title","slug","status","orgName"}}`; sai định dạng → 400, không có → 404 `"Không tìm thấy vé"`. Không đổi `checked_in_at`.
- [x] **Step 1: Test thất bại:** `test_lookup_any_org_ticket`; `test_lookup_does_not_check_in` (`checked_in_at` vẫn `NULL`); `test_lookup_refunded_shows_status`; `test_bad_code_400_unknown_404`; `test_requires_admin`; UI: nhập mã → hiện đơn, trạng thái "Chưa soát" / "Đã soát lúc …" / "Đơn đã hoàn", link sang dòng đơn trong Sổ đơn.
- [x] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `GET {{baseUrl}}/api/admin/tickets/K7QF-29XM`.
- [x] **Checkpoint:** `pytest -q` và `npm test`.

---

## Tính năng D — Sửa & Huỷ sự kiện

### Task D1: Migration 0006 + `DELETE /api/organizer/events/{id}`

**Files:**
- Create: `backend/alembic/versions/0006_event_cancel.py`, `backend/app/services/org_events.py`
- Modify: `backend/app/models/catalog.py` (`ck_events_status` thêm `'cancelled'`; cột `cancel_reason: Mapped[str | None]` (Text), `cancelled_at: Mapped[datetime | None]` (timestamptz), `cancelled_by: Mapped[str | None]` (varchar(10), CHECK `IN ('organizer','admin')`, dùng ở D4)), `backend/app/models/sales.py` (`Order.refunded_at: Mapped[datetime | None]` timestamptz), `backend/app/services/org_orders.py` (đọc `o.refunded_at` trực tiếp), `backend/app/services/booking.py` (`orders_json` thêm `eventStatus` (`events.status`), `cancelReason`, `refundedAt` — để "Vé của tôi" biết đơn bị hoàn), `database/schema.sql` (chạy `backend/scripts/export_schema.sh`), `backend/app/services/manage.py` (`phase_of` trả `"cancelled"`; `event_summaries` thêm `cancelReason`), `backend/app/routers/organizer.py`, Postman, `frontend/src/utils/dashboard.js` (STATUS `cancelled` = `{label: 'Đã huỷ', tone: 'muted'}`; bộ lọc `{ id: 'da-huy', label: 'Đã huỷ', phases: ['cancelled'] }`)
- Create: `backend/tests/concurrency.py` (helper `race`, xem Global Constraints)
- Test: `backend/tests/test_api_org_cancel.py`, `backend/tests/test_cancel_concurrency.py`, `backend/tests/test_migrations.py` (thêm 0006), `frontend/src/utils/dashboard.test.js`

**Interfaces:**
- Produces: `org_events.cancel_event(db, organizer_id: int, event_id: int, reason: Any) -> dict`
- Hợp đồng: body `{"reason": "..."}`. Khoá dòng sự kiện `FOR UPDATE` (sau khi khoá gọi móc `_after_lock()` — chỉ test dùng để giữ khoá). Toàn bộ huỷ + hoàn tiền nằm trong **một transaction** (router commit một lần; lỗi bất kỳ → rollback). `phase ∈ {closed, ended}` → 409 `"Sự kiện đã diễn ra, không thể huỷ"`; đã huỷ → 409 `"Sự kiện đã được huỷ trước đó"`. Không có đơn nào (mọi trạng thái) → xoá hẳn (xoá `home_slots`, cascade suất/hạng/kho), trả `{"deleted": true}`. Có đơn → `reason` 5–300 ký tự (thiếu → 400 `"Vui lòng nhập lý do huỷ (5–300 ký tự)"`), `status='cancelled'`, `cancel_reason`, `cancelled_at = now`, `cancelled_by = 'organizer'`, mọi đơn `paid` → `refunded` với `refunded_at = now`; trả `{"deleted": false, "refundedOrders": n, "refundedAmount": sum, "event": <summary>}`.

- [ ] **Step 1: Test thất bại:** `test_delete_without_orders_removes_event`; `test_cancel_with_orders_refunds_all` (kể cả `refunded_at` được đặt và `/organizer/orders` trả `refundedAt`); `test_cancel_requires_reason`; `test_cancelled_hidden_and_not_bookable` (`/api/events` không có, `/api/events/{slug}` → 404, POST `/api/orders` bị từ chối); `test_cancel_ended_409`; `test_cancel_twice_409`; `test_other_org_404`; `test_checkin_after_cancel_409` (dùng C1); `test_phase_cancelled_in_summary`; `test_customer_orders_show_refund` (`GET /api/orders` của khách: `status == 'refunded'`, `eventStatus == 'cancelled'`, `cancelReason`, `refundedAt`); migration nâng/hạ 0006 được.
  - **Rollback** `test_cancel_rollback_on_midway_error`: monkeypatch bước hoàn đơn (`org_events._refund_paid_orders`) ném lỗi sau khi đã đổi `events.status` → API 500; đọc lại bằng kết nối khác: sự kiện vẫn `approved`, `cancel_reason`/`cancelled_at` NULL, mọi đơn vẫn `paid`, `refunded_at` NULL.
  - **Đồng thời (2 kết nối)** `test_concurrent_cancel_two_connections`: `race()` hai lần `cancel_event` cùng sự kiện có đơn → đúng 1 thành công + 1 `HTTPException(409)`; bên thua chờ ≥ `hold` giây (bị chặn ở `FOR UPDATE`, không phải gọi lần lượt); mỗi đơn chỉ hoàn 1 lần (`refunded_at` một giá trị), `refundedOrders` của bên thắng = số đơn `paid` ban đầu.
  - **Migration trên CSDL có dữ liệu** `test_0006_upgrade_on_populated_db`: hạ test DB về 0005, nạp catalog + đơn demo, nâng lên 0006 → số dòng `events`/`orders` không đổi, mọi sự kiện cũ giữ `status`, `cancelled_*`/`refunded_at` NULL; hạ lại 0005 khi chưa có sự kiện `cancelled` → OK; có sự kiện `cancelled` → downgrade dừng với thông báo rõ (không làm mất dữ liệu âm thầm). Ghi biên bản chạy trên CSDL dev (đếm dòng trước/sau) vào `database/docs/migration-0006.md`.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. Kiểm `/api/admin/overview` không vỡ khi có sự kiện `cancelled`.
- [ ] **Step 5:** Postman `DELETE {{baseUrl}}/organizer/events/{{eventId}}`. Hỏi người dùng trước khi `alembic upgrade head` trên CSDL dev (đây cũng là minh chứng "migration trên CSDL đã có dữ liệu" của học phần).
- [ ] **Checkpoint:** `pytest -q` và `npx vitest run frontend/src/utils/dashboard.test.js`.

### Task D2: `PATCH /api/organizer/events/{id}` + dữ liệu form trong chi tiết

**Files:**
- Modify: `backend/app/services/org_events.py`, `backend/app/services/manage.py` (tách phần kiểm tra của `create_org_event` thành `validate_event_form` dùng chung; `organizer_event_detail` thêm `form` và `editable`), `backend/app/routers/organizer.py`, Postman
- Test: `backend/tests/test_api_org_edit.py`

**Interfaces:**
- Produces: `manage.validate_event_form(db, body: OrgEventIn) -> dict` (khoá: `title, category, city, venue, address, day, start, end, show_start, sale_start, description_paras, tiers`); `org_events.update_event(db, organizer_id: int, event_id: int, body: OrgEventIn) -> Event`.
- `OrgEventIn.tiers[*]` nhận thêm `id` (tuỳ chọn) để chỉ hạng cũ.
- `GET /organizer/events/{id}` thêm:
  ```json
  "form": {"title","category","city","venue","address","date","startTime","endTime","description","saleStart",
           "tiers": [{"id","name","price","quantity","perks","sold"}]},
  "editable": {"mode": "full" | "limited" | "none", "saleStart": true}
  ```
  `form` thêm `layout`, `mapId`, `prices` (`{groupId: price}`, `null` với `list`) — chỉ đọc ở D2; sửa theo sơ đồ làm ở Task F4.
  `mode`: `pending`/`rejected` → `full`; phase `upcoming-sale`/`on-sale` → `limited`; còn lại (`closed`, `ended`, `cancelled`) → `none`. `editable.saleStart` = `mode == 'full'` hoặc (`limited` và chưa mở bán). `sold` = `presold + sold` từ `stock.tier_stats` (S1) — đúng cho cả sự kiện `seats`.
- Quy tắc PATCH (khoá sự kiện + dòng `tier_stock` `FOR UPDATE`):
  - `full`: thay toàn bộ trường của form `list`; đổi ngày/giờ → thay `Show` bằng id mới và tạo lại kho; hạng vé thay hết (chưa thể có đơn). `rejected` → `status='pending'`, `reject_reason=None`, `reviewed_at=None`. Slug giữ nguyên. (Đổi `layout`/`mapId`/`prices` → Task F4; ở D2 gửi `layout` khác `list` → 400 `"Kiểu bán vé không hợp lệ"`.)
  - PATCH khoá dòng sự kiện `FOR UPDATE` trước khi đọc số đã bán → sửa và huỷ cùng lúc không chồng nhau.
  - `limited`: trường khoá (`title, category, city, venue, date, startTime, endTime`) khác giá trị cũ → 409 `"Sự kiện đã duyệt không thể đổi {tên trường}"`. `saleStart` khác cũ khi đã mở bán → 409 `"Đã mở bán, không đổi được giờ mở bán"`; giờ mới phải sau hiện tại. Hạng cũ: `quantity < sold` → 400 `"Loại vé “{name}”: không thể ít hơn {sold} vé đã bán"`; đổi `price` khi `sold > 0` → 409 `"Loại vé “{name}” đã có người mua, không đổi được giá"`. Hạng cũ bị bỏ khỏi danh sách: `sold == 0` và không có `order_items` → xoá; ngược lại → 409. Hạng mới → id `ve-{max+1}`, tạo `TierStock`. Cập nhật `ticket_tiers.capacity` và `tier_stock.capacity` cùng lúc.
  - `none` → 409 `"Sự kiện này không còn sửa được"`.
  - Trả `{"event": <summary>}`.

- [ ] **Step 1: Test thất bại:** `test_detail_has_form_and_mode`; `test_full_edit_pending_changes_everything`; `test_full_edit_rejected_back_to_pending`; `test_limited_edit_description_address_ok`; `test_limited_locked_field_409` (tham số hoá 7 trường); `test_limited_capacity_below_sold_400_stock_unchanged` (đơn thật + `presold`); `test_limited_price_change_sold_409`; `test_limited_add_tier_creates_stock`; `test_limited_remove_unsold_tier_ok_sold_tier_409`; `test_sale_start_after_open_409`; `test_ended_or_cancelled_409` (cả `closed`); `test_edit_visible_to_customer` (sau PATCH, `GET /api/events/{slug}` và `/availability` phản ánh giá / sức chứa mới). Chạy lại `test_api_organizer_events.py` để chắc tạo sự kiện vẫn đúng sau khi tách `validate_event_form`.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `PATCH {{baseUrl}}/organizer/events/{{eventId}}`.
- [ ] **Checkpoint:** `pytest -q`.

### Task D3: Nút Sửa / Huỷ trên ngăn kéo sự kiện

**Files:**
- Modify: `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (`CreateEventForm` nhận `initial`, `mode`, `eventId`: có `eventId` → PATCH, nút "Lưu thay đổi"; `mode='limited'` → khoá các ô khoá, hạng có `sold > 0` khoá giá và không xoá được, ô số lượng `min={sold}`; `DrawerDetail` thêm "Sửa sự kiện" (ẩn khi `mode='none'`) và "Huỷ sự kiện"), `frontend/src/hooks/useEventDetail.js` (xoá cache sau khi sửa/huỷ)
  phía khán giả: `frontend/src/components/booking/ETicket.jsx` + `frontend/src/pages/MyTickets/MyTicketsPage.jsx` (đơn `refunded`: con dấu "Sự kiện đã huỷ · Đã hoàn {total} ₫", lý do huỷ, ẩn QR và mã check-in, không link tới trang sự kiện; thêm tab "Đã huỷ" gom các đơn `refunded`/`cancelled`, hai tab cũ chỉ lấy đơn `paid`)
- Create: `frontend/src/pages/Organizer/components/CancelEventDialog.jsx`
- Test: `frontend/src/pages/Organizer/OrganizerDashboard.test.jsx`, `frontend/src/pages/MyTickets/MyTicketsPage.test.jsx`; chụp lại `frontend/src/test/fixtures/org-event-detail.json` để có `form` / `editable`

**Interfaces:** Consumes D1, D2. Produces `CancelEventDialog({ event, detail, onDone })` — hiện số đơn / số tiền sẽ hoàn (`detail.money.orders`, `detail.money.revenue`), ô lý do (bắt buộc khi có đơn), phải gõ đúng tên sự kiện mới bật nút "Huỷ sự kiện".

- [ ] **Step 1: Test thất bại:** "Sửa sự kiện" ở sự kiện on-sale → form điền sẵn, ô "Tên sự kiện" bị khoá, lưu gửi PATCH đúng body; sự kiện chờ duyệt → mọi ô sửa được; "Huỷ sự kiện" → dialog, nút vô hiệu tới khi gõ đúng tên; xác nhận gửi DELETE `{reason}`, toast "Đã huỷ sự kiện và hoàn tiền N đơn", danh sách tải lại; lỗi 409 hiện trong form; "Vé của tôi": đơn `refunded` nằm ở tab "Đã huỷ", không có QR, hiện lý do huỷ.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS.
- [ ] **Checkpoint:** `npm test`.

### Task D4: Admin — Gỡ / huỷ sự kiện vi phạm

**Files:**
- Modify: `backend/app/services/org_events.py` (`cancel_event(db, organizer_id: int | None, event_id, reason, by: str)` — `organizer_id=None` + `by='admin'` bỏ kiểm tra chủ sở hữu; Admin **luôn** phải có lý do kể cả khi chưa có đơn, và luôn huỷ mềm (không xoá hẳn) để còn dấu vết), `backend/app/routers/admin.py`, `backend/app/services/manage.py` + `booking.orders_json` (trả `cancelledBy`), `frontend/src/pages/Admin/components/OrganizersView.jsx` (nút "Gỡ sự kiện" trên mỗi dòng sự kiện qua prop `renderEventActions` có sẵn, dùng lại `CancelEventDialog` của D3 với `scope="admin"`; F3 cắm thêm nút này vào ngăn xem trước), `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (sự kiện `cancelledBy == 'admin'`: con dấu "Sàn đã gỡ" + lý do), `frontend/src/components/booking/ETicket.jsx` ("Sàn đã gỡ sự kiện" thay cho "Sự kiện đã huỷ" khi `cancelledBy == 'admin'`), Postman
- Test: `backend/tests/test_api_admin_cancel.py`, `backend/tests/test_cancel_concurrency.py`, `frontend/src/pages/Admin/components/OrganizersView.test.jsx`, `frontend/src/pages/MyTickets/MyTicketsPage.test.jsx`

**Interfaces:**
- Consumes: D1 (`cancel_event`, migration 0006 — cột `events.cancelled_by` thêm luôn trong 0006), D3 (`CancelEventDialog`).
- Produces: `POST /api/admin/events/{id}/cancel` `{reason}` (5–300 ký tự, bắt buộc) → như D1 nhưng `deleted` luôn `false`; quy tắc phase giống BTC (`closed`/`ended`/`cancelled` → 409). `event_summaries[*]` và `orders_json` thêm `cancelledBy`.
- [ ] **Step 1: Test thất bại:** `test_admin_cancel_refunds_and_keeps_event`; `test_admin_cancel_requires_reason_even_without_orders`; `test_admin_then_org_cancel_409_single_refund` (tuần tự); **`test_admin_org_cancel_concurrent_single_refund`** (`race()` Admin `cancel_event(None, …, by='admin')` vs BTC `cancel_event(org_id, …)` trên 2 kết nối → 1 thắng, 1 bị chặn rồi 409, `cancelled_by` là của bên thắng, mỗi đơn hoàn 1 lần); `test_org_sees_cancelled_by_admin`; `test_customer_sees_cancelled_by_admin`; UI: "Gỡ sự kiện" trong danh sách sự kiện của một BTC (OrganizersView) gửi đúng endpoint; vé của khách hiện "Sàn đã gỡ sự kiện".
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `POST {{baseUrl}}/admin/events/{{eventId}}/cancel`.
- [ ] **Checkpoint:** `pytest -q` và `npm test`.

---

## Tính năng E — Rút tiền về ngân hàng

### Task E1: Migration 0007 + API rút tiền của Ban tổ chức

**Files:**
- Create: `backend/alembic/versions/0007_withdrawals.py`, `backend/app/models/payouts.py` (đăng ký trong `models/__init__.py`), `backend/app/services/withdrawals.py`
- Modify: `backend/app/routers/organizer.py`, `database/schema.sql`, Postman
- Test: `backend/tests/test_api_withdrawals.py`, `backend/tests/test_withdrawal_concurrency.py`, `backend/tests/test_migrations.py`

**Interfaces:**
- Bảng `withdrawals`: `id serial PK`, `organizer_id int FK organizers.user_id ON DELETE CASCADE`, `amount int CHECK (amount > 0)`, `bank_name text`, `account_no varchar(20)`, `account_name text`, `status varchar(10) CHECK IN ('pending','paid','rejected') DEFAULT 'pending'`, `note text NULL`, `created_at timestamptz DEFAULT now()`, `processed_at timestamptz NULL`, `processed_by int FK users.id NULL`; index `(organizer_id, created_at)`; chú thích bảng tiếng Việt như các bảng khác.
- Produces: `withdrawals.balance(db, organizer_id: int) -> dict` → `{"settledNet","held","pending","paid","available"}`:
  - `settledNet` = Σ thực nhận (`revenue − fee_of(revenue)`, theo từng sự kiện) của các sự kiện **đã diễn** (`manage.phase_of(...) == 'ended'`);
  - `held` = Σ thực nhận của các sự kiện chưa diễn và chưa huỷ (đang tạm giữ, chưa rút được);
  - `available = settledNet − pending − paid`, không bao giờ âm (sự kiện đã diễn thì không huỷ được).
  Tái dùng cách tính `last_show_start` của `event_summaries` (truy vấn gộp, không N+1). `withdrawals.request(db, organizer_id: int, body) -> Withdrawal`; `withdrawals.to_json(w, org_name: str | None = None) -> dict` → `{"id","amount","bankName","accountNo","accountName","status","note","createdAt","processedAt"}` (+ `orgName` khi có).
- Hợp đồng:
  - `GET /organizer/withdrawals` → `{"balance": {...}, "withdrawals": [...mới trước]}`.
  - `POST /organizer/withdrawals` body `{amount, bankName, accountNo, accountName}` → 201 `{"withdrawal", "balance"}`. Kiểm: `amount` nguyên ≥ 50 000 (400 `"Số tiền rút tối thiểu 50.000 ₫"`), ≤ `available` (409 `"Số dư khả dụng không đủ"`); `bankName` 2–60 (400 `"Vui lòng nhập tên ngân hàng"`); `accountNo` chỉ chữ số, 6–20 (400 `"Số tài khoản chỉ gồm 6–20 chữ số"`); `accountName` 2–60 (400 `"Vui lòng nhập tên chủ tài khoản"`). Trước khi tính số dư: `SELECT ... FROM organizers WHERE user_id = :id FOR UPDATE` (rồi gọi móc `_after_lock()` cho test). Ghi `withdrawals` trong cùng transaction với khoá; lỗi → rollback.

- [ ] **Step 1: Test thất bại:** `test_balance_settled_vs_held` (1 sự kiện đã diễn + 1 đang bán: tiền rơi đúng ô, phí tính theo từng sự kiện); `test_held_money_not_withdrawable` (chỉ có sự kiện đang bán → `available == 0`, POST → 409); `test_request_reduces_available`; `test_request_over_balance_409`; `test_two_requests_each_full_balance_second_409`; `test_validation_400` (tham số hoá 4 trường); `test_rejected_returns_money_paid_does_not` (đặt status trực tiếp trong DB); `test_cancel_only_reduces_held` (dùng D1: huỷ sự kiện đang bán → `held` giảm, `available` không đổi); `test_only_own_withdrawals`; migration nâng/hạ 0007 (nâng trên CSDL đã có dữ liệu: bảng mới rỗng, bảng cũ không đổi số dòng).
  - **Đồng thời (2 kết nối)** `test_concurrent_requests_two_connections`: số dư khả dụng X; `race()` hai `withdrawals.request(amount=X)` → đúng 1 tạo được, bên kia chờ ≥ `hold` giây ở `FOR UPDATE` rồi 409 `"Số dư khả dụng không đủ"`; trong CSDL đúng 1 dòng `pending`, `available == 0`. Thêm ca `amount = X/2` cả hai → cả hai thành công, `available == 0` (khoá không chặn sai).
  - **Rollback** `test_request_rollback_on_midway_error`: monkeypatch bước sau khi INSERT `withdrawals` (vd. `withdrawals.to_json`) ném lỗi → API 500; kết nối khác đọc lại: không có dòng `withdrawals` mới, số dư như cũ.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman GET/POST `{{baseUrl}}/organizer/withdrawals`; hỏi người dùng trước khi `alembic upgrade head` trên CSDL dev.
- [ ] **Checkpoint:** `pytest -q`.

### Task E2: API duyệt rút tiền của Admin

**Files:**
- Modify: `backend/app/routers/admin.py` (router Admin tạo ở A3), `backend/app/services/withdrawals.py`, `backend/app/services/manage.py` (`overview` thêm `pendingWithdrawals: int`; `admin_organizers` (B3) thêm `available`, `held`, `pendingWithdrawals` lấy từ `withdrawals.balance` — truy vấn gộp, không gọi lặp từng BTC), Postman
- Test: `backend/tests/test_api_admin_withdrawals.py`

**Interfaces:**
- Produces: `withdrawals.admin_list(db, status: str) -> list[dict]` (kèm `orgName`); `withdrawals.decide(db, admin: User, withdrawal_id: int, decision: Any, note: Any) -> dict`.
- Hợp đồng: `GET /admin/withdrawals?status=pending|paid|rejected|all` (mặc định `pending`) → `{"withdrawals": [...]}`. `POST /admin/withdrawals/{id}/decide` `{decision: "paid"|"rejected", note}` → `{"withdrawal"}`; `rejected` cần `note` 3–300 ký tự; cập nhật có điều kiện `WHERE status = 'pending'`, không còn pending → 409 `"Yêu cầu này đã được xử lý"`; id sai định dạng / không có → 404 `"Không tìm thấy yêu cầu rút tiền"`.

- [ ] **Step 1: Test thất bại:** `test_admin_lists_pending_with_org_name`; `test_mark_paid_sets_processed`; `test_reject_requires_note`; `test_decide_twice_409`; `test_not_admin_403`; `test_overview_counts_pending`; `test_admin_organizers_balance_matches_org_view` (`available`/`held` của một BTC trong `/admin/organizers` == `/organizer/withdrawals` của BTC đó).
  - **Đồng thời (2 kết nối)** `test_two_admins_decide_concurrently`: `race()` Admin A `paid` vs Admin B `rejected` cùng một yêu cầu → đúng 1 thành công, bên kia 409 `"Yêu cầu này đã được xử lý"`; trạng thái cuối khớp bên thắng, `processed_by` là người thắng.
  - **Rollback** `test_decide_rollback_on_midway_error`: lỗi sau UPDATE → yêu cầu vẫn `pending`, `processed_at` NULL.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman 2 request admin (`{{baseUrl}}/admin/withdrawals…`).
- [ ] **Checkpoint:** `pytest -q`.

### Task E3: Giao diện rút tiền (BTC) + duyệt rút tiền (Admin)

**Files:**
- Create: `frontend/src/pages/Organizer/components/WithdrawDialog.jsx`, `frontend/src/hooks/useWithdrawals.js`, `frontend/src/pages/Organizer/components/WithdrawDialog.test.jsx`, fixture `org-withdrawals.json`, `admin-withdrawals.json`
- Modify: `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (khối "Số dư khả dụng" lấy `balance.available` từ API, thêm dòng "Đang tạm giữ: {held} ₫ — rút được sau khi sự kiện diễn xong", bỏ state `withdrawn` và phép tính tay; nút "Rút về ngân hàng" mở dialog, vô hiệu khi `available < 50000`), `frontend/src/pages/Admin/AdminDashboard.jsx` (mục "Tài chính & rút tiền": danh sách yêu cầu thật kèm số dư khả dụng hiện tại của BTC đó để Admin đối chiếu, nút "Đã chuyển" / "Từ chối" (bắt nhập lý do); giấy nhớ thứ 3 trên bàn làm việc đổi thành "yêu cầu rút tiền chờ xử lý"), `frontend/src/pages/Admin/components/OrganizersView.jsx` (cột Khả dụng / Tạm giữ / Chờ rút), `frontend/scripts/capture-fixtures.mjs`
- Test: `frontend/src/pages/Organizer/OrganizerDashboard.test.jsx`, `frontend/src/pages/Admin/AdminDashboard.test.jsx` (tạo mới)

**Interfaces:** Consumes E1, E2. Produces `useWithdrawals() -> {data, error, reload}`; `WithdrawDialog({ balance, onDone })`.

- [ ] **Step 1: Test thất bại:** sidebar hiện `available` và dòng "Đang tạm giữ" của fixture; dialog điền sẵn số tiền = `available`, chặn < 50.000 và > `available` ngay trên giao diện; gửi POST đúng body, toast "Đã gửi yêu cầu rút … ₫", số dư tải lại; lịch sử có con dấu Chờ xử lý / Đã chuyển / Từ chối (kèm lý do); Admin: "Đã chuyển" gửi `decide` `paid`, "Từ chối" mở ô lý do.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS.
- [ ] **Checkpoint:** `npm test` và `pytest -q`.

---

## Tính năng G — Hạng mục CSDL bắt buộc của học phần

Căn cứ: `docs/Thong_bao_Project_cuoi_ky_2026.md` mục III.2 (quy mô dữ liệu), III.3 (truy vấn, view), III.5 (chỉ mục, hiệu năng). Minh chứng đặt trong `database/docs/` và dẫn từ README.

### Task G1: Script sinh dữ liệu lớn + thống kê số dòng

**Files:**
- Create: `backend/app/seed_large.py` (`python -m app.seed_large --scale 1.0 [--seed 42] [--database-url …]`), `backend/scripts/row_counts.sql`, `database/docs/du-lieu-lon.md`
- Test: `backend/tests/test_seed_large.py`

**Interfaces:**
- Produces: `seed_large.generate(db, *, scale: float, seed: int, days: int = 365) -> dict[str, int]` (số dòng đã thêm theo bảng); `seed_large.row_counts(db) -> dict[str, int]`.
- Quy mô ở `scale=1.0` (mô phỏng 12 tháng, mọi dữ liệu sinh ra đi qua đúng ràng buộc CSDL, không chèn dòng vô nghĩa):
  | Bảng | Số dòng | Ghi chú |
  |---|---|---|
  | `users` (khách) | ≥ 12 000 | tên/email/SĐT giả lập, mật khẩu băm một lần dùng chung |
  | `organizers` + `events` | ~ 60 BTC, ≥ 400 sự kiện (list) | đủ phase: pending, rejected, upcoming-sale, on-sale, ended, cancelled |
  | `orders` | ≥ 100 000 | ngày mua phân bố theo mùa/cuối tuần trong 365 ngày, ~4% `refunded`, có mã giảm giá |
  | `order_items` | ≥ 120 000 | 1–3 hạng/đơn |
  | `tickets` | ≥ 200 000 | mỗi vé một mã duy nhất; ~70% vé của sự kiện đã diễn có `checked_in_at` |
  | `withdrawals` | ~ 1 000 | chỉ trên tiền của sự kiện đã diễn, đúng quy tắc số dư |
  `tier_stock.sold` khớp tổng vé đã bán (đơn `paid` + `refunded` — vé không quay lại kho).
- Sinh bằng SQL theo lô (`INSERT … SELECT … FROM generate_series`) + `COPY` khi cần, trong **một transaction**; chạy lại được (xoá dữ liệu do chính script tạo — đánh dấu email `@lon.ticketnhip.vn`, mã đơn tiền tố `TL`). Không chạm dữ liệu catalog/demo.
- Bộ dữ liệu lớn chạy trên CSDL riêng `ticketnhip_large` (cùng schema bằng `alembic upgrade head`); bộ demo giữ nguyên ở `ticketnhip`.

- [ ] **Step 1: Test thất bại** (chạy `scale=0.01` trên CSDL test): `test_counts_scale_linearly`; `test_constraints_hold` (không vi phạm FK/CHECK — chèn thành công là đủ; thêm kiểm tra `orders.total = subtotal − discount`); `test_stock_matches_sold_tickets`; `test_withdrawals_never_exceed_settled_net` (dùng `withdrawals.balance` của E1); `test_rerun_is_idempotent` (chạy 2 lần → cùng số dòng); `test_demo_data_untouched`.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS.
- [ ] **Step 5:** Hỏi người dùng rồi tạo `ticketnhip_large`, chạy `scale=1.0`, ghi thời gian chạy + kết quả `scripts/row_counts.sql` vào `database/docs/du-lieu-lon.md` (bảng: tên – vai trò – số dòng demo – số dòng lớn – cách sinh – truy vấn sử dụng).
- [ ] **Checkpoint:** `pytest -q`.

### Task G2: Hai chỉ mục + đo EXPLAIN (ANALYZE, BUFFERS) trước/sau

**Files:**
- Create: `backend/alembic/versions/0008_perf_indexes.py`, `backend/perf/q1_order_search.sql`, `backend/perf/q2_revenue_report.sql`, `backend/scripts/explain_bench.py`, `database/docs/hieu-nang.md`
- Test: `backend/tests/test_perf_indexes.py`

**Interfaces:**
- Chỉ mục (ngoài PK/UNIQUE), mỗi cái phục vụ một truy vấn thật đã có:
  1. `CREATE EXTENSION IF NOT EXISTS pg_trgm` + `ix_orders_buyer_trgm` — GIN `gin_trgm_ops` trên `lower(buyer_name || ' ' || buyer_email || ' ' || buyer_phone)` → ô tìm của sổ đơn (A1/A3, `ILIKE '%…%'`); sửa `org_orders._conditions` để so khớp đúng biểu thức này.
  2. `ix_orders_status_created` — B-tree `(status, created_at) INCLUDE (event_id, total)` → báo cáo doanh thu theo khoảng ngày (B1/B3) và `v_daily_revenue`.
- `explain_bench.py --database-url … --runs 5`: với mỗi truy vấn trong `backend/perf/*.sql` (kèm tham số cố định ghi trong file), chạy `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` N lần **trước** (đã `DROP INDEX`) và **sau** khi tạo chỉ mục, cùng CSDL `ticketnhip_large`, `VACUUM ANALYZE` trước mỗi đợt; xuất bảng trung vị/min/max thời gian, loại node, shared hit/read, và lưu kế hoạch đầy đủ vào `database/docs/plans/`.
- [ ] **Step 1: Test thất bại:** `test_migration_0008_up_down`; `test_plans_use_new_indexes` (CSDL test + `scale=0.05`, `SET enable_seqscan = off` không dùng — chỉ `ANALYZE`; kế hoạch q1 có `Bitmap Index Scan on ix_orders_buyer_trgm`, q2 có `ix_orders_status_created`); `test_search_results_unchanged` (cùng kết quả A1 trước/sau đổi biểu thức tìm).
- [ ] **Step 2–4:** FAIL → cài đặt → PASS.
- [ ] **Step 5:** Hỏi người dùng rồi chạy `explain_bench.py` trên `ticketnhip_large`; viết `database/docs/hieu-nang.md`: SQL, tham số, quy mô dữ liệu, máy đo (CPU/RAM/PostgreSQL 18), kế hoạch trước/sau, thời gian, nhận xét trung thực (kể cả khi chỉ mục không giúp).
- [ ] **Checkpoint:** `pytest -q`.

### Task G3: 8 truy vấn nghiệp vụ nâng cao (CTE, hàm cửa sổ, EXISTS, phân trang) phục vụ API

**Files:**
- Create: `backend/sql/queries/*.sql` (mỗi truy vấn một file, đầu file chú thích: mục đích – đầu vào – API/màn hình dùng – người phụ trách), `backend/app/services/sql_queries.py` (nạp file `.sql`, chạy bằng `text()` với tham số bind — không ghép chuỗi), `database/docs/truy-van.md` (SQL + kết quả mẫu trên bộ demo)
- Modify: các service dùng truy vấn tương ứng (thay truy vấn ORM cùng chức năng — kết quả API không đổi), `backend/app/routers/organizer.py` / `admin.py` (2 endpoint mới bên dưới), Postman
- Test: `backend/tests/test_sql_queries.py`

**Interfaces — 8 truy vấn** (mỗi cái khác kỹ thuật/mục đích, không chỉ đổi tham số):
  | # | File | Kỹ thuật chính | Dùng ở |
  |---|---|---|---|
  | Q1 | `order_ledger.sql` | JOIN 5 bảng + lọc động + `LIMIT/OFFSET` phân trang + đếm tổng | `/organizer/orders`, `/admin/orders` |
  | Q2 | `revenue_series.sql` | CTE `generate_series` lấp bucket trống + `LEFT JOIN` + `date_trunc` theo giờ VN | `/organizer/reports` `series` |
  | Q3 | `revenue_running.sql` | Hàm cửa sổ `SUM(...) OVER (ORDER BY bucket)` (doanh thu luỹ kế) + `LAG` (so với kỳ trước, %) | thêm `series[*].cumulative`, `changePct` |
  | Q4 | `event_ranking.sql` | CTE tổng theo sự kiện + `RANK() OVER (ORDER BY revenue DESC)` + `PERCENT_RANK` | Bục vinh danh Admin, `byEvent[*].rank` |
  | Q5 | `tier_sell_through.sql` | CTE kho (`tier_stock` ∪ đếm `seat_holds`) + JOIN đã bán theo khoảng + tỉ lệ lấp đầy | `byTier` |
  | Q6 | `top_customers.sql` | Tổng chi theo khách + `DENSE_RANK() OVER (PARTITION BY organizer_id ORDER BY spent DESC)` lấy top 10 mỗi BTC | **mới** `GET /organizer/top-customers?from&to` + bảng trong ReportsView |
  | Q7 | `events_without_sales.sql` | `NOT EXISTS` (sự kiện đang bán chưa có đơn `paid` trong N ngày) + truy vấn con tương quan lần bán gần nhất | **mới** `GET /admin/events/stale?days=7` + giấy nhắc trên bàn làm việc Admin |
  | Q8 | `withdrawal_balance.sql` | CTE thực nhận theo sự kiện đã diễn (phí theo từng sự kiện) − `SUM(...) FILTER (WHERE status IN ('pending','paid'))` | `withdrawals.balance` (E1), `/admin/organizers` (E2) |
  View: giữ `v_daily_revenue` (đang dùng ở biểu đồ sổ cái); Q2 đọc từ view khi `groupBy=day`.
- [ ] **Step 1: Test thất bại:** mỗi truy vấn một test so kết quả với cách tính độc lập bằng Python trên dữ liệu nhỏ dựng trong test (`test_q1_…` → `test_q8_…`); `test_queries_are_parameterized` (mọi file chỉ dùng `:param`, không có `{`/`%s`); `test_api_shapes_unchanged` (chạy lại toàn bộ test A1/B1/B3/E1/E2).
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman 2 request mới; `database/docs/truy-van.md` có SQL, mục đích, đầu vào, kết quả mẫu (chạy trên bộ demo) và người phụ trách (để trống cho nhóm điền).
- [ ] **Step 6:** UI: ReportsView thêm cột "Luỹ kế" + "so với kỳ trước" và bảng "Khách mua nhiều nhất"; Admin thêm giấy nhắc "sự kiện đang bán chưa có đơn 7 ngày"; Vitest.
- [ ] **Checkpoint:** `pytest -q` và `npm test`.

---

## Tính năng F — Ban tổ chức bán theo sơ đồ khu / ghế (làm cuối cùng)

> Đưa xuống cuối theo quyết định 2026-11-08: không nằm trong yêu cầu bắt buộc của học phần. Sau D: CreateEventForm/PATCH đã có, F1–F3 bổ sung sơ đồ, F4 làm phần sửa theo sơ đồ đã tách khỏi D2/D3.

### Task F1: API sơ đồ + tạo sự kiện theo sơ đồ

**Files:**
- Create: `backend/app/services/org_maps.py`
- Modify: `backend/app/services/manage.py` (`OrgEventIn` thêm `layout`, `mapId`, `prices`; `create_org_event` sinh hạng vé theo sơ đồ), `backend/app/routers/organizer.py`, Postman
- Test: `backend/tests/test_api_org_maps.py`

**Interfaces:**
- Produces:
  - `GET /api/organizer/venue-maps` → `{"maps": [{"id","kind","name","capacity","groups": [{"id","label","color","capacity","maxPerOrder","perks"}]}]}` — `groups[*].capacity` = Σ sức chứa khu của nhóm (zones) hoặc số ghế của nhóm (seats); sắp theo `sort_order`.
  - `org_maps.tiers_for_map(db, map_id: str, prices: dict[str, int]) -> tuple[str, list[dict]]` → `(layout, tiers)` theo đúng quy ước catalog: **zones** — mỗi khu một hạng `{id: zone.id, name: zone.label, price: prices[zone.group_id], capacity: zone.capacity, group_id: zone.group_id, max_per_order: group.max_per_order or TIER_MAX_PER_ORDER, perks: group.perks, sort_order: zone.sort_order}` + dòng `tier_stock`; **seats** — mỗi nhóm một hạng `{id: group.id, name: group.label, price, capacity: số ghế, group_id: group.id, ...}`, **không** tạo `tier_stock`. Đối chiếu với một sự kiện catalog cùng loại trong `seed/catalog.json` trước khi chốt `group_id` cho seats.
- Hợp đồng tạo: `layout` ∈ `list|zones|seats` (mặc định `list`, khác → 400 `"Kiểu bán vé không hợp lệ"`). `list` → như cũ dùng `tiers`. `zones|seats` → `mapId` phải tồn tại và `kind == layout` (400 `"Sơ đồ không hợp lệ"`); `prices` phải có giá cho **mọi** nhóm, mỗi giá 10 000–100 000 000 (400 `"Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"`); `tiers` bị bỏ qua. `events.map_id` = `mapId`.
- [ ] **Step 1: Test thất bại:** `test_list_venue_maps_with_group_capacity`; `test_create_zones_event_tiers_and_stock`; `test_create_seats_event_no_tier_stock`; `test_missing_or_bad_price_400`; `test_map_kind_mismatch_400`; `test_created_map_event_bookable_after_approve` (duyệt → khách đặt vé/ghế qua `POST /api/orders` thành công, `/availability` giảm đúng); `test_list_layout_unchanged` (chạy lại `test_api_organizer_events.py`).
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `GET {{baseUrl}}/organizer/venue-maps` + ví dụ tạo sự kiện `zones`.
- [ ] **Checkpoint:** `pytest -q`.

### Task F2: Form tạo sự kiện chọn sơ đồ + xem trước bằng đúng component của khán giả

**Files:**
- Create: `frontend/src/pages/Organizer/components/MapPricing.jsx`, `frontend/src/pages/Organizer/components/MapPricing.test.jsx`, fixture `org-venue-maps.json`
- Modify: `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (`CreateEventForm`: bộ chọn "Loại vé / Sơ đồ khu / Sơ đồ ghế"; `list` → khối "Loại vé" như cũ; sơ đồ → `MapPricing`), `frontend/src/components/booking/TicketPickers.jsx` (cho `ZoneMapArea` / `SeatMapArea` nhận `readOnly` để dùng làm bản xem trước), `frontend/scripts/capture-fixtures.mjs`

**Interfaces:**
- Consumes F1; `useMap(mapId)` có sẵn; `ZoneMapArea` / `SeatMapArea` của khán giả.
- Produces: `MapPricing({ maps, layout, mapId, prices, onChange })` — chọn sơ đồ cùng loại, mỗi nhóm một ô giá kèm màu + sức chứa, tổng sức chứa; bên cạnh là **bản xem trước dùng chính `ZoneMapArea`/`SeatMapArea`** (dựng `tiers` giả từ giá đang nhập, `remaining = capacity`) để BTC thấy đúng thứ khán giả sẽ thấy. Gửi `{layout, mapId, prices}`.
- [ ] **Step 1: Test thất bại:** chọn "Sơ đồ ghế" chỉ liệt kê sơ đồ `seats`; thiếu giá một nhóm → nút gửi báo "Nhập giá cho nhóm …"; gửi POST đúng `{layout, mapId, prices}` và không có `tiers`; bản xem trước hiện nhãn nhóm với giá vừa nhập.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Kiểm `BookingPage.test.jsx` vẫn PASS sau khi thêm `readOnly`.
- [ ] **Checkpoint:** `npm test`.

### Task F3: Admin — Xem trước hồ sơ trước khi duyệt + chặn duyệt quá hạn

**Files:**
- Modify: `backend/app/services/catalog.py` (tách `build_event_detail(db, ev: Event) -> EventDetail` khỏi `get_event_detail`, bản công khai vẫn lọc `public_events_query`), `backend/app/services/manage.py` (`review`: duyệt khi suất đầu đã bắt đầu → 409 `"Đã qua giờ diễn, không thể duyệt"`), `backend/app/routers/admin.py`, `frontend/src/pages/Admin/AdminDashboard.jsx` (`PendingCard` thêm nút "Xem hồ sơ"), Postman
- Create: `frontend/src/pages/Admin/components/EventPreview.jsx`, `frontend/src/pages/Admin/components/EventPreview.test.jsx`
- Test: `backend/tests/test_api_admin_preview.py`

**Interfaces:**
- Consumes: `build_event_detail`; component khán giả `EventHero`, `EventSections` (giới thiệu, bảng giá), `ZoneMapArea` / `SeatMapArea` với `readOnly` (F2); `reviveEvent` (`utils/eventFormat.js`); `CancelEventDialog` (D3) cho nút "Gỡ sự kiện" (D4) trong `actions`.
- Produces: `GET /api/admin/events/{id}` → `{"event": <cùng JSON với GET /api/events/{slug}>, "summary": <event_summaries>, "organizer": {"orgName","code","email","phone"}}` cho sự kiện **bất kỳ trạng thái** (kể cả `pending`, `rejected`, `cancelled`); `related` rỗng. `EventPreview({ eventId, onClose, actions })` — ngăn kéo toàn màn hình hiện đúng trang khán giả sẽ thấy (nút mua bị vô hiệu, dải "XEM TRƯỚC — CHƯA CÔNG KHAI"), `actions` là chỗ cắm nút Duyệt / Trả lại / Gỡ sự kiện.
- [ ] **Step 1: Test thất bại:** `test_preview_pending_event_same_shape_as_public` (khoá JSON trùng với `/api/events/{slug}` của một sự kiện đã duyệt); `test_preview_map_event_has_map_and_tiers`; `test_public_still_404_for_pending`; `test_approve_after_show_start_409`; `test_requires_admin`; UI: bấm "Xem hồ sơ" → hiện tên, giới thiệu, bảng giá / sơ đồ; duyệt ngay trong ngăn kéo được.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS. **Step 5:** Postman `GET {{baseUrl}}/admin/events/{{eventId}}`.
- [ ] **Checkpoint:** `pytest -q` và `npm test`.

### Task F4: Sửa sự kiện theo sơ đồ (tách từ D2/D3)

**Files:**
- Modify: `backend/app/services/org_events.py` (`update_event` nhận `layout`/`mapId`/`prices`), `frontend/src/pages/Organizer/components/MapPricing.jsx` (chế độ sửa), `frontend/src/pages/Organizer/OrganizerDashboard.jsx` (`CreateEventForm` sửa sự kiện sơ đồ), Postman
- Test: `backend/tests/test_api_org_edit.py`, `frontend/src/pages/Organizer/components/MapPricing.test.jsx`

**Interfaces:** Consumes D2 (`update_event`, `editable`), F1 (`tiers_for_map`), F2 (`MapPricing`).
- `full`: đổi cả `layout` / `mapId` / `prices` → sinh lại hạng vé bằng `org_maps.tiers_for_map` (kho `tier_stock` với zones, không có kho với seats).
- `limited` với sự kiện theo sơ đồ: `layout`, `mapId` bị khoá (409 như trường khoá); chỉ đổi `prices` của nhóm chưa bán vé nào (nhóm đã bán → 409 `"Nhóm “{label}” đã có người mua, không đổi được giá"`); không thêm/bỏ hạng, không đổi sức chứa.
- UI: `MapPricing` ở chế độ sửa — khoá chọn sơ đồ khi `limited`, khoá ô giá của nhóm đã bán.
- [ ] **Step 1: Test thất bại:** `test_limited_map_event_price_rules` (zones: đổi giá nhóm chưa bán OK, nhóm đã bán 409, đổi `mapId` 409); `test_full_edit_switch_list_to_seats`; UI: sự kiện `zones` đang bán → ô giá nhóm đã bán bị khoá.
- [ ] **Step 2–4:** FAIL → cài đặt → PASS.
- [ ] **Checkpoint:** `pytest -q` và `npm test`.

---

## Task Z: Kết thúc
- [ ] Chụp lại toàn bộ fixture (cần server — hỏi người dùng); `npm test` + `pytest -q` → PASS, ghi lại số test.
- [ ] Thử tay luồng đồng bộ hai phía: BTC tạo sự kiện sơ đồ ghế → Admin duyệt → khách đặt ghế → BTC thấy đơn + "đã bán" khớp "còn lại" của khách → soát vé → khách thấy "Đã check-in" → (sự kiện khác) BTC huỷ → khách thấy "Đã huỷ · Đã hoàn".
- [ ] Thử tay luồng Admin: xem trước hồ sơ sơ đồ ghế → duyệt → tìm đơn của khách trong Sổ đơn toàn sàn → tra mã vé → gỡ một sự kiện → BTC và khách đều thấy "Sàn đã gỡ" → duyệt một yêu cầu rút tiền; số trên Admin khớp số trên trang BTC.
- [ ] `grep -rn "DỮ LIỆU MẪU\|sẽ có ở bước tiếp theo" src` → không còn kết quả.
- [ ] Cập nhật bảng API trong `backend/README.md` (17 endpoint của plan gốc + 2 endpoint của G3); `pytest tests/test_postman_collection.py` → PASS.
- [ ] `database/docs/` đủ: `du-lieu-lon.md` (G1), `hieu-nang.md` + `plans/` (G2), `truy-van.md` (G3), `migration-0006.md` (D1), và bảng minh chứng transaction/đồng thời (liệt kê các test `race()`/rollback của D1, D4, E1, E2 kèm lệnh chạy và kết quả).
- [ ] `npm run build` → không lỗi.
- [ ] Thử tay cả 5 mục trên trình duyệt bằng tài khoản demo (cần server — hỏi người dùng).
